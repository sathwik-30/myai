from typing import Any, Dict


def evaluate_memory(
    message: str,
    answer: str = "",
    source: str = "conversation",
) -> Dict[str, Any]:
    """
    Decide whether an interaction belongs in reusable memory.

    Ordinary conversation is already preserved in chat history and must not be
    copied into temporary or permanent memory automatically. Knowledge fetched
    from external sources is stored by SearchManager at the point of retrieval.
    """
    text = " ".join(str(message or "").lower().split())
    if not text:
        return {
            "save": False,
            "importance": 1,
            "memory_type": "temporary",
            "reason": "empty_message",
        }

    if source in {"web", "wikipedia", "local_resource"}:
        return {
            "save": False,
            "importance": 4,
            "memory_type": "knowledge",
            "reason": "knowledge_already_handled_by_search_layer",
        }

    return {
        "save": False,
        "importance": 1,
        "memory_type": "temporary",
        "reason": "chat_history_is_the_source_of_truth_for_conversation",
    }
