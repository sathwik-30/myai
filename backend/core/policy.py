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


def load_override() -> str:
    """Return the complete human-readable core override policy."""
    try:
        with open(OVERRIDE_PATH, "r", encoding="utf-8") as file:
            return file.read().strip()
    except OSError:
        return ""


def load_policy() -> Dict[str, Any]:
    """Load explicit machine-readable rules from the human-readable override.

    The Markdown document is itself a valid policy document. Explicit
    ALWAYS:/NEVER:/REQUIRE_CONFIRMATION: lines are optional extensions used
    when a rule needs machine-enforced matching.
    """
    rules = _load_lines()
    always = [r[len("ALWAYS:"):].strip() for r in rules if r.startswith("ALWAYS:")]
    never = [r[len("NEVER:"):].strip() for r in rules if r.startswith("NEVER:")]
    confirm = [
        r[len("REQUIRE_CONFIRMATION:"):].strip()
        for r in rules
        if r.startswith("REQUIRE_CONFIRMATION:")
    ]
    return {
        "available": bool(rules),
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
    """Apply explicit core policy without turning normal conversation into a gate.

    A readable OVERRIDE.md is considered available even when it contains no
    machine-tagged rules. Only explicit NEVER rules block a request here.
    Capability and authority checks belong to action execution boundaries.
    """
    policy = load_policy()
    if not policy["available"]:
        return {
            "allowed": False,
            "response": "I can't safely process this because my core override policy is unavailable.",
            "reason": "core_override_unavailable",
        }

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
