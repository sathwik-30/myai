import os
import re
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OVERRIDE_PATH = os.path.join(BASE_DIR, "core", "OVERRIDE.md")


def _load_lines() -> List[str]:
    try:
        with open(OVERRIDE_PATH, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    except OSError:
        return []


def load_policy() -> Dict[str, Any]:
    rules = _load_lines()
    always = [r[7:].strip() for r in rules if r.startswith("ALWAYS:")]
    never = [r[6:].strip() for r in rules if r.startswith("NEVER:")]
    confirm = [
        r[len("REQUIRE_CONFIRMATION:"):].strip()
        for r in rules
        if r.startswith("REQUIRE_CONFIRMATION:")
    ]
    return {
        "always": always,
        "never": never,
        "require_confirmation": confirm,
        "path": OVERRIDE_PATH,
    }


def blocked_by_override(text: str) -> str | None:
    policy = load_policy()
    candidate = " ".join(str(text or "").lower().split())

    for rule in policy["never"]:
        words = re.findall(r"[a-z0-9]+", rule.lower())
        if words and all(word in candidate for word in words):
            return rule

    return None


def apply_override(response: str, user_message: str) -> Dict[str, Any]:
    blocked_rule = blocked_by_override(user_message)
    if blocked_rule:
        return {
            "allowed": False,
            "response": "I can't do that because it conflicts with a rule in my core override file.",
            "reason": blocked_rule,
        }

    return {
        "allowed": True,
        "response": response,
        "reason": None,
    }
