"""Autonomous casual-teacher data generator for Medha.

Qwen/Ollama is used only as a teacher. This script generates varied
casual conversations, removes visible teacher reasoning/refusal boilerplate,
rejects warning-only responses when they do not answer the user, asks a
quality judge whether each conversation is genuinely useful, and stores only
accepted examples.

The Medha runtime never loads Qwen.
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
TEACHER_MODEL = os.getenv("MEDHA_TEACHER_MODEL", "qwen3:8b")

# These are teacher/model refusal patterns, not ordinary safety language.
# A useful answer may contain words such as dangerous, safety, risk, health,
# security, or law and must NOT be rejected merely for containing them.
REFUSAL_PATTERNS = [
    r"i\s+(?:am|’m|m)\s+sorry[^.]{0,240}(?:can(?:not|'t)|unable|assist|help)",
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

# Qwen3 may expose its reasoning in the returned message. That is teacher
# internals, not conversational training data.
THINKING_BLOCK_PATTERNS = [
    re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<analysis>.*?</analysis>", re.IGNORECASE | re.DOTALL),
]
THINKING_LINE_RE = re.compile(
    r"(?is)(?:^|\n)\s*(?:thinking\.\.\.|analysis\.\.\.)\s*.*?"
    r"(?:\n\s*(?:\.\.\.done thinking\.|done thinking\.|final answer\s*:?)\s*)"
)

# Only casual conversational skills are trained in this first phase.
CURRICULUM = [
    ("casual", "greetings, small talk, boredom, everyday chat"),
    ("slang", "slang, abbreviations, typos, lowercase and short informal messages"),
    ("followup", "natural follow-ups that depend on earlier turns"),
    ("correction", "user corrections and graceful conversational recovery"),
    ("ambiguity", "ambiguous short messages resolved from context"),
    ("topic_switch", "abrupt everyday topic changes while preserving continuity"),
    ("emotion", "ordinary frustration, excitement, boredom, disappointment and encouragement"),
    ("continuity", "remembering what was just said and continuing naturally"),
    ("short_messages", "messages such as ok, hmm, so, what, nah, really, fine"),
    ("multi_turn", "natural casual conversations with several turns and changing intent"),
    ("natural_endings", "ending a conversation naturally without forcing another question"),
]

GENERATOR_SYSTEM = """You are a teacher generating training conversations for a new AI called Medha.

This phase teaches ONLY natural CASUAL CONVERSATION. Do not teach programming,
technical subjects, school subjects, project knowledge, factual encyclopedic
knowledge, or personal facts.

Create original, realistic, varied multi-turn conversations, not canned FAQ pairs.
Use 2-12 alternating user/assistant messages. Include short messages, slang,
follow-ups, corrections, ambiguity, topic changes and natural endings when they
fit the scenario. Do not force a question after every assistant turn.

The assistant should respond directly to what the user says. If the user asks a
question, the assistant should actually answer it when an answer is appropriate.
A warning by itself is not an answer. A warning plus a useful explanation,
answer, or safer alternative IS an answer.

Never generate assistant refusal boilerplate such as "I can't help", "I cannot
assist", "I must refuse", or policy/safety-guideline explanations. Never mention
Qwen, Ollama, being a language model, internal policies, training prompts, or
teacher identity. Do not invent private facts.

Do not output reasoning or thinking text. Return ONLY JSON:
{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}
"""

JUDGE_SYSTEM = """You are a strict dataset-quality judge for Medha's CASUAL conversation training.

Keep only conversations that teach useful, natural conversational behavior.

IMPORTANT DIRECT-ANSWER RULE:
When the user asks a question or requests something, the assistant should
directly address it. Reject responses that merely warn, lecture, apologize,
refuse, or say something is dangerous without actually answering the request
or providing a useful explanation/alternative.

Examples:
- User: "How do I do X?" Assistant: "X is dangerous." -> REJECT.
- User: "How do I do X?" Assistant: "X is dangerous because A and B. If your
  goal is Y, a safer way is Z." -> KEEP.
- User: "Is X dangerous?" Assistant: "Yes, because A and B." -> KEEP.
- User: "What do you think?" Assistant: "That's an interesting question." with
  no meaningful response -> REJECT when the context requires an answer.

Do NOT reject a response merely because it mentions danger, safety, risk, health,
security, law, or similar topics. Reject only when it is a refusal/policy
boilerplate response or fails to meaningfully address the user.

Reject:
- teacher/model identity references
- "I'm sorry, I can't assist..."
- "I cannot/can't help/provide/comply..."
- safety-policy/guideline/limitation boilerplate
- thinking/reasoning traces
- malformed or repetitive/template-like conversations
- invented private user facts
- irrelevant or low-quality assistant turns
- non-casual technical/study/project training

Keep:
- natural small talk and casual conversation
- direct answers
- useful explanations
- warnings when they accompany an actual answer or useful alternative
- ordinary emotional acknowledgement when it meaningfully responds

Return ONLY JSON:
{"keep":true,"score":0,"reason":"short reason"}
"""


def clean_teacher_text(text: str) -> str:
    """Remove visible reasoning blocks while preserving the actual answer."""
    cleaned = text.strip()
    for pattern in THINKING_BLOCK_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    # Handle common Qwen-style visible reasoning when it is wrapped in
    # "Thinking..." ... "...done thinking.".
    cleaned = THINKING_LINE_RE.sub("\n", cleaned)

    # Remove stray reasoning markers if they remain at the edges.
    cleaned = re.sub(r"(?im)^\s*(?:\.\.\.done thinking\.|done thinking\.)\s*$", "", cleaned)
    return cleaned.strip()


def teacher_refusal(text: str) -> bool:
    return any(pattern.search(text) for pattern in REFUSAL_RE)


WARNING_ONLY_PATTERNS = [
    r"^(?:that|this)\s+(?:is|sounds|seems)\s+(?:very\s+)?dangerous\.?$",
    r"^(?:that|this)\s+(?:is|sounds|seems)\s+(?:very\s+)?unsafe\.?$",
    r"^(?:don't|do not)\s+do\s+that\.?$",
    r"^(?:please\s+)?(?:don't|do not)\s+do\s+this\.?$",
    r"^(?:you\s+)?should\s+(?:not|never)\s+do\s+that\.?$",
    r"^(?:i|we)\s+(?:wouldn't|would not)\s+recommend\s+that\.?$",
]
WARNING_ONLY_RE = [re.compile(p, re.IGNORECASE) for p in WARNING_ONLY_PATTERNS]


def warning_only(text: str) -> bool:
    compact = " ".join(text.split()).strip()
    return any(pattern.fullmatch(compact) for pattern in WARNING_ONLY_RE)


def normalize(item: dict) -> dict:
    cleaned_messages = []
    for message in item["messages"]:
        content = clean_teacher_text(str(message["content"]))
        cleaned_messages.append(
            {
                "role": str(message["role"]).strip().lower(),
                "content": " ".join(content.split()),
            }
        )
    return {"messages": cleaned_messages}


def structurally_valid(messages: list[dict]) -> bool:
    if not 2 <= len(messages) <= 12 or messages[-1]["role"] != "assistant":
        return False

    expected = "user"
    for message in messages:
        if message["role"] != expected or not message["content"] or len(message["content"]) > 2500:
            return False

        if teacher_refusal(message["content"]):
            return False

        # Warning-only assistant turns do not teach direct answering.
        # We intentionally do NOT reject useful safety explanations.
        if message["role"] == "assistant" and warning_only(message["content"]):
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
        timeout=300,
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
                    f"Casual curriculum category: {category}\n"
                    f"Explore: {description}\n"
                    "Make the conversation original, natural and conversational."
                ),
            },
        ],
        0.9,
    )
    return json.loads(clean_teacher_text(raw))


def judge(item: dict) -> tuple[bool, int, str]:
    raw = ollama(
        [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": json.dumps(item, ensure_ascii=False)},
        ],
        0.2,
    )
    result = json.loads(clean_teacher_text(raw))
    return (
        bool(result.get("keep")),
        int(result.get("score", 0)),
        str(result.get("reason", "")),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
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
    max_attempts = max(args.count * 5, 20)

    with output.open("a", encoding="utf-8") as handle:
        while accepted < args.count and attempts < max_attempts:
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
    if accepted < args.count:
        print("Stopped at the safety limit of 5 attempts per requested example.")
    print(f"Dataset: {output}")


if __name__ == "__main__":
    main()
