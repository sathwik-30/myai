import re
from typing import Any, Dict


def evaluate_memory(
    message: str,
    answer: str = "",
    source: str = "conversation",
) -> Dict[str, Any]:
    """
    Every completed assistant interaction is eligible for long-term memory.

    Memory is not permanent forever: user-scoped entries expire automatically
    after six months without being used. Conversation history remains the
    complete record, while this memory layer is the reusable knowledge store.
    """
    text = " ".join(str(message or "").lower().split())
    if not text:
        return {
            "save": False,
            "importance": 1,
            "memory_type": "temporary",
            "reason": "empty_message",
        }

    if source in {"core_override", "fallback"}:
        return {
            "save": True,
            "importance": 2,
            "memory_type": "conversation",
            "reason": "completed_interaction",
        }

    return {
        "save": True,
        "importance": 3,
        "memory_type": "conversation" if source not in {"web", "wikipedia"} else "knowledge",
        "reason": "store_all_completed_interactions",
    }
