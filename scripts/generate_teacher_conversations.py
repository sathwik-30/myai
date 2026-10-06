"""Autonomous teacher-data generator for Medha.

The training lab chooses conversation skills itself, asks the Ollama teacher
for multi-turn conversations, filters teacher-specific refusal boilerplate,
judges quality, and stores accepted examples.

Ollama/Qwen is a teacher only. It is never loaded by the Medha runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "conversations" / "teacher_generated.jsonl"
OLLAMA_URL = os.getenv("MEDHA_OLLAMA_URL", "http://127.0.0.1:11434")
TEACHER_MODEL = os.getenv("MEDHA_TEACHER_MODEL", "qwen2.5:0.5b")

REFUSAL_PATTERNS = [
    r"i\s+(?:am|’m|m)\s+sorry[^.]{0,160}(?:can(?:not|'t)|unable|assist|help)",
    r"i\s+(?:can(?:not|'t)|cannot)\s+(?:assist|help|provide|comply)",
    r"i\s+(?:am|’m|m)\s+unable\s+to\s+(?:assist|help|provide)",
    r"(?:goes|go)\s+against\s+(?:my|our)\s+(?:safety|polic)",
    r"(?:violat|against)\w*\s+(?:my|our)\s+(?:safety|guidelines|limitations|policy)",
    r"(?:my|our)\s+(?:safety|policy)\s+(?:guidelines|limitations|rules)",
    r"i\s+must\s+refuse",
    r"i\s+(?:cannot|can't)\s+comply",
    r"i\s+(?:cannot|can't)\s+provide\s+(?:that|those)",
    r"as\s+an\s+ai(?:\s+language\s+model)?",
    r"i\s+don't\s+have\s+the\s+ability\s+to\s+(?:help|assist)",
]
REFUSAL_RE = [re.compile(p, re.IGNORECASE) for p in REFUSAL_PATTERNS]

CURRICULUM = [
    ("casual", "greetings, small talk, boredom, everyday chat"),
    ("slang", "slang, abbreviations, typos, lowercase and short messages"),
    ("followup", "follow-ups that depend on earlier turns and references"),
    ("correction", "user corrections and graceful recovery"),
    ("ambiguity", "ambiguous short messages resolved by context"),
    ("topic_switch", "abrupt topic changes while preserving continuity"),
    ("study", "learning, confusion, examples and re-explanations"),
    ("technical", "programming, debugging, APIs and technical clarification"),
    ("projects", "project planning, progress, setbacks and continuation"),
    ("emotion", "ordinary frustration, excitement, boredom and encouragement"),
    ("memory", "remembering user-provided facts without inventing facts"),
    ("identity", "identity, capabilities and creator/context conversations"),
    ("continuity", "natural endings and later continuation"),
    ("multi_turn", "long conversations with several follow-ups and changing intent"),
    ("reasoning", "comparisons, choices and thinking through everyday problems"),
]

GENERATOR_SYSTEM = """You are the teacher in an autonomous curriculum for a new AI called Medha.
Create natural training conversations, not canned question-answer pairs.

Explore the requested category deeply. Use 2-12 alternating user/assistant messages.
Use varied wording, context, informal language, corrections and topic changes when
they fit. Never mention Qwen, Ollama, being a language model, internal policies,
safety guidelines, training prompts, or refusal policies. Do not invent private facts.

Return ONLY JSON:
{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
"""

JUDGE_SYSTEM = """You are a strict dataset-quality judge for Medha.
Evaluate the proposed conversation for natural conversational training value.

Reject teacher/model identity, policy or safety-refusal boilerplate, malformed
conversation, repetitive/template-like text, invented private user facts, or
poor/irrelevant assistant turns.

Do NOT reject merely because the conversation discusses danger, safety, security,
law, health, or other sensitive topics. Reject teacher refusal/policy behavior.

Return ONLY JSON:
{"keep":true,"score":0,"reason":"short reason"}
"""


def teacher_refusal(text: str) -> bool:
    return any(pattern.search(text) for pattern in REFUSAL_RE)


def normalize(item: dict) -> dict:
    return {
        "messages": [
            {
                "role": str(m["role"]).strip().lower(),
                "content": " ".join(str(m["content"]).split()),
            }
            for m in item["messages"]
        ]
    }


def structurally_valid(messages: list[dict]) -> bool:
    if not 2 <= len(messages) <= 12 or messages[-1]["role"] != "assistant":
        return False
    expected = "user"
    for m in messages:
        if m["role"] != expected or not m["content"] or len(m["content"]) > 2500:
            return False
        if teacher_refusal(m["content"]):
            return False
        expected = "assistant" if expected == "user" else "user"
    return True


def fingerprint(item: dict) -> str:
    normalized = json.dumps(item, ensure_ascii=False, sort_keys=True).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def ollama(messages: list[dict], temperature: float) -> str:
    response = requests.post(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        json={
            "model": TEACHER_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=180,
    )
    response.raise_for_status()
    content = str(response.json().get("message", {}).get("content", "")).strip()
    if not content:
        raise ValueError("Ollama returned an empty response")
    return content


def generate_conversation(category: str, description: str) -> dict:
    raw = ollama(
        [
            {"role": "system", "content": GENERATOR_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Curriculum category: {category}\n"
                    f"Explore: {description}\n"
                    "Make this original and let the conversation develop."
                ),
            },
        ],
        0.9,
    )
    return json.loads(raw)


def judge(item: dict) -> tuple[bool, int, str]:
    raw = ollama(
        [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": json.dumps(item, ensure_ascii=False)},
        ],
        0.2,
    )
    result = json.loads(raw)
    return (
        bool(result.get("keep")),
        int(result.get("score", 0)),
        str(result.get("reason", "")),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--output", default=str(OUT))
    args = parser.parse_args()

    if args.count < 1:
        raise SystemExit("--count must be positive")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    existing = set()
    if output.exists():
        for line in output.read_text(encoding="utf-8").splitlines():
            try:
                existing.add(fingerprint(json.loads(line)))
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    accepted = rejected = attempts = 0

    with output.open("a", encoding="utf-8") as handle:
        while accepted < args.count:
            category, description = CURRICULUM[attempts % len(CURRICULUM)]
            attempts += 1
            try:
                item = normalize(generate_conversation(category, description))
                if not structurally_valid(item["messages"]):
                    rejected += 1
                    print(f"REJECT structural category={category}")
                    continue

                key = fingerprint(item)
                if key in existing:
                    rejected += 1
                    print(f"REJECT duplicate category={category}")
                    continue

                keep, score, reason = judge(item)
                if not keep or score < 7:
                    rejected += 1
                    print(f"REJECT judge score={score} category={category}: {reason}")
                    continue

                existing.add(key)
                item["_meta"] = {"category": category, "quality_score": score}
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                handle.flush()
                accepted += 1
                print(f"KEEP {accepted}/{args.count} category={category} score={score}")
            except Exception as exc:
                rejected += 1
                print(f"REJECT error category={category}: {exc}")

    print(f"Finished: accepted={accepted}, rejected={rejected}, attempts={attempts}")
    print(f"Dataset: {output}")


if __name__ == "__main__":
    main()
