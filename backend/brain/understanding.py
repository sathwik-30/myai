from typing import Any, Dict, List

from backend.memory.semantic_memory import search


class LanguageUnderstanding:
    """
    Local, dependency-light language understanding for Medha.

    It uses character n-gram TF-IDF similarity over learned memories.
    This gives Medha paraphrase tolerance without Ollama, a remote LLM,
    or a model download at runtime.
    """

    def understand(
        self,
        message: str,
        context: List[Dict[str, Any]] | None = None,
        user_id: int | None = None,
    ) -> Dict[str, Any]:
        matches = search(message, top_k=5, min_score=0.30, user_id=user_id)
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
        return matches[0].get("answer") if matches else None
