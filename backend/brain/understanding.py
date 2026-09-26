from typing import Any, Dict, List
from backend.memory.semantic_memory import search

class LanguageUnderstanding:
    """
    Meaning-based understanding for Medha.

    No hand-written phrase matching is used here. A sentence is
    represented by a language embedding and compared with learned
    memories, allowing different wording to reach the same answer.
    """
    def understand(self, message: str, context: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        matches = search(message, top_k=5, min_score=0.45)
        return {"message": message, "matches": matches, "context": context or []}

    def best_memory_answer(self, message: str, context: List[Dict[str, Any]] | None = None) -> str | None:
        matches = self.understand(message, context)["matches"]
        return matches[0].get("answer") if matches else None
