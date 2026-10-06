"""Generate Medha training conversations from an Ollama teacher.

Ollama/Qwen is a teacher only. Its output is filtered before it can enter
Medha's training data. Ollama is never imported by the Medha runtime.

Requires Ollama running locally, for example:
    ollama serve
    ollama pull qwen2.5:0.5b

Run:
    python scripts/generate_teacher_conversations.py --count 500

Environment:
    MEDHA_TEACHER_MODEL      Ollama model name
    MEDHA_OLLAMA_URL         Ollama API base URL
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "conversations" / "teacher_generated.jsonl"
OLLAMA_URL = os.getenv("MEDHA_OLLAMA_URL", "http://127.0.0.1:11434")
TEACHER_MODEL = os.getenv("MEDHA_TEACHER_MODEL", "qwen2.5:0.5b")

# These identify teacher refusal/policy boilerplate, not ordinary discussion
# of danger or safety. The semantic checks below add another layer.
REFUSAL_PATTERNS = [
    r"i\s+(?:am|’m|m)\s+sorry[^.]{0,120}(?:can(?:not|'t)|unable|assist|help)",
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

SYSTEM_PROMPT = """You are a teacher helping create training data for a new personal AI
called Medha. Produce natural, varied, multi-turn conversations.

Teach useful communication: casual conversation, slang, typos, follow-ups,
corrections, topic changes, explanations, uncertainty, natural endings,
technical discussion, project discussion, and context tracking.

Do not write about being Qwen, being a language model, your policies, or your
safety rules. Do not produce refusal boilerplate. The dataset will be filtered
again before training.

Return ONLY valid JSON with this shape:
{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
Use 2 to 8 alternating user/assistant messages.
"""

CATEGORIES = [
    "greeting and casual conversation",
    "slang, abbreviations, typos and short messages",
    "follow-up questions using previous context",
    "user corrects the assistant",
    "topic change during a conversation",
    "project and study conversation",
    "technical conversation with clarification",
    "user is excited, bored, frustrated, or having a bad day",
    "natural conversation ending and continuation later",
    "identity and personal-memory conversation without inventing facts",
]


def teacher_refusal(text: str) -> bool:
    return any(pattern.search(text) for pattern in REFUSAL_RE)


def valid_messages(messages) -> bool:
    if not isinstance(messages, list) or not 2 <= len(messages) <= 8:
        return False
    expected = "user"
    for item in messages:
        if not isinstance(item, dict):
            return False
        role = str(item.get("role", "")).strip().lower()
        content = str(item.get("content", "")).strip()
        if role != expected or not content:
            return False
        if len(content) > 2000:
            return False
        if teacher_refusal(content):
            return False
        expected = "assistant" if expected == "user" else "user"
    return messages[-1]["role"] == "assistant"


def normalize(item):
    messages = []
    for message in item["messages"]:
        messages.append({
            "role": message["role"].strip().lower(),
            "content": " ".join(message["content"].split()),
        })
    return {"messages": messages}


def fingerprint(item) -> str:
    return json.dumps(item, ensure_ascii=False, sort_keys=True).lower()


def generate_one(category: str) -> dict:
    prompt = (
        f"Create one original conversation in the category: {category}. "
        "Make the wording different from common textbook examples."
    )
    response = requests.post(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        json={
            "model": TEACHER_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.9},
        },
        timeout=180,
    )
    response.raise_for_status()
    body = response.json()
    content = str(body.get("message", {}).get("content", "")).strip()
    if not content:
        raise ValueError("Teacher returned an empty response.")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("Teacher did not return valid JSON.") from exc


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
            except json.JSONDecodeError:
                pass

    accepted = 0
    rejected = 0
    attempts = 0

    with output.open("a", encoding="utf-8") as handle:
        while accepted < args.count:
            attempts += 1
            category = CATEGORIES[accepted % len(CATEGORIES)]
            try:
                item = normalize(generate_one(category))
                if not valid_messages(item["messages"]):
                    rejected += 1
                    continue
                key = fingerprint(item)
                if key in existing:
                    rejected += 1
                    continue
                existing.add(key)
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                handle.flush()
                accepted += 1
                print(f"accepted={accepted}/{args.count} rejected={rejected} category={category}")
            except Exception as exc:
                rejected += 1
                print(f"rejected={rejected}: {exc}")

    print(f"Finished: accepted={accepted}, rejected={rejected}, attempts={attempts}")
    print(f"Dataset: {output}")


if __name__ == "__main__":
    main()
