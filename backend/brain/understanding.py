from typing import Any, Dict, List

from backend.memory.layers import search_all


class LanguageUnderstanding:
    """
    Local language understanding for Medha.

    The reusable memory layer is the single source of truth for learned
    information. Legacy semantic_memory storage is intentionally not queried.
    """

    def understand(
        self,
        message: str,
        context: List[Dict[str, Any]] | None = None,
        user_id: int | None = None,
    ) -> Dict[str, Any]:
        matches = search_all(user_id, message, top_k=5)
        return {
            "message": message,
            "matches": matches,
            "context": context or [],
        }

    def best_memory_answer(
        self,
        message: str,
        context: List[Dict[str, Any]] | None = None,
        user_id: int | None = None,
    ) -> str | None:
        matches = self.understand(message, context, user_id)["matches"]
        if not matches:
            return None

        # Weak semantic matches should never hijack an ordinary question.
        # A learned answer must be strongly related to the current message.
        best = matches[0]
        if float(best.get("score", 0.0)) < 0.60:
            return None

        return best.get("answer")
