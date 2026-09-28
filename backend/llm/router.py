"""Compatibility boundary for Medha's local brain.

There is intentionally no cloud/local-LLM provider here.  Runtime language
understanding belongs to backend.brain.local_nlu.
"""
from typing import Any, Dict, List

from backend.brain.local_nlu import get_language_engine


class ModelRouter:
    provider_name = "local"

    def available(self) -> bool:
        return get_language_engine().available

    def generate(
        self,
        messages: List[Dict[str, str]],
        instructions: str = "",
        model: str | None = None,
    ) -> Dict[str, Any]:
        raise RuntimeError(
            "Medha is independent: external LLM providers are not used at runtime."
        )


router = ModelRouter()
