"""Intent compatibility layer backed by Medha's trainable local NLU."""
from typing import Literal

from backend.brain.local_nlu import get_language_engine

Intent = Literal[
    "greeting", "status", "identity", "capability", "memory", "personal",
    "desktop", "technical", "knowledge", "research", "thanks", "general",
    "casual", "permanent",
]


def classify(message: str) -> Intent:
    result = get_language_engine().understand(message)
    intent = result.intent

    # Preserve the older conversation engine's categories where they are
    # semantically useful, without phrase-by-phrase if/else matching.
    if intent == "memory":
        return "memory"
    if intent == "personal":
        return "personal"
    if intent == "greeting":
        return "casual"
    if intent in {"status", "identity", "capability", "thanks"}:
        return "casual"
    return intent  # type: ignore[return-value]


def understand(message: str) -> dict:
    result = get_language_engine().understand(message)
    return {
        "intent": result.intent,
        "confidence": result.confidence,
        "entities": result.entities,
    }
