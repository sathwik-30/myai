"""Model routing boundary for Medha.

Preference order:
1. Promoted Medha local decoder.
2. Optional Ollama model running on the same machine.

No hosted/cloud model is required.
"""
from typing import Any, Dict, List

from backend.brain.local_nlu import get_language_engine


class ModelRouter:
    provider_name = "local"

    def __init__(self):
        self._ollama = None

    def _get_ollama(self):
        if self._ollama is None:
            from backend.llm.ollama import provider
            self._ollama = provider
        return self._ollama

    def available(self) -> bool:
        if get_language_engine().available:
            return True
        try:
            return self._get_ollama().available()
        except Exception:
            return False

    def generate(
        self,
        messages: List[Dict[str, str]],
        instructions: str = "",
        model: str | None = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        # The small Medha decoder is intentionally handled by the brain runtime.
        # This router supplies a practical local conversational fallback.
        ollama = self._get_ollama()
        if ollama.available():
            return ollama.generate(
                messages,
                instructions=instructions,
                model=model,
                temperature=temperature,
            )
        raise RuntimeError(
            "No local conversational model is available. Train/promote the "
            "Medha decoder or start Ollama with a local model."
        )


router = ModelRouter()
