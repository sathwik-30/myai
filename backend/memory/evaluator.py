import re
from typing import Any, Dict

from backend.brain.intent import classify

PERSONAL_PATTERNS = (
    r"\bmy\s+(?:name|project|goal|preference|favorite|favourite|skill|role|college|course|branch)\b",
    r"\bi\s+(?:prefer|like|love|hate|use|work|study|want|need)\b",
    r"\bcall me\b",
)

TEMPORARY_PATTERNS = (
    r"\bright now\b",
    r"\btoday\b",
    r"\btonight\b",
    r"\bfor now\b",
    r"\bcurrently\b",
)

TRIVIAL_PATTERNS = (
    r"^(hi|hello|hey|thanks|thank you|good morning|good night)[!. ]*$",
    r"\bhow are you\b",
)

def evaluate_memory(
    message: str,
    answer: str = "",
    source: str = "conversation",
) -> Dict[str, Any]:
    text = " ".join(str(message or "").lower().split())
    tokens = re.findall(r"[a-z0-9]+", text)

    if not text or any(re.search(pattern, text) for pattern in TRIVIAL_PATTERNS):
        return {"save": False, "importance": 1, "memory_type": "temporary", "reason": "casual_small_talk"}

    if any(re.search(pattern, text) for pattern in TEMPORARY_PATTERNS):
        return {"save": False, "importance": 1, "memory_type": "temporary", "reason": "time_limited_context"}

    if any(re.search(pattern, text) for pattern in PERSONAL_PATTERNS):
        return {"save": True, "importance": 4, "memory_type": "personal", "reason": "future_personal_utility"}

    intent = classify(text)

    if intent == "memory":
        return {"save": True, "importance": 5, "memory_type": "personal", "reason": "explicit_memory_instruction"}

    if source in {"wikipedia", "web"} or intent == "technical":
        return {"save": True, "importance": 3, "memory_type": "knowledge", "reason": "researched_knowledge"}

    if len(tokens) >= 8 and any(word in text for word in (
        "project", "learn", "learning", "build", "building", "goal",
        "prefer", "use", "working", "study", "course",
    )):
        return {"save": True, "importance": 3, "memory_type": "personal", "reason": "likely_future_utility"}

    return {"save": False, "importance": 1, "memory_type": "temporary", "reason": "not_useful_enough"}
