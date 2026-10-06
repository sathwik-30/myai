"""Model routing boundary for Medha.

Preference order:
1. Promoted Medha local decoder.
2. Optional Ollama model running on the same machine.

No hosted/cloud model is required.
"""
from typing import Any, Dict, List

from backend.brain.local_nlu import get_language_engine


class ModelRouter:
    def __init__(self):
        self._ollama = None

    @property
    def provider_name(self) -> str:
        try:
            ollama = self._get_ollama()
            if ollama.available():
                return "ollama"
        except Exception:
            pass

        try:
            from backend.model.runtime import get_decoder_runtime
            if get_decoder_runtime().available:
                return "local-decoder"
        except Exception:
            pass

        return "none"

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
        # The conversational response layer owns decoder generation. This
        # boundary is only the provider fallback and must report reality.
        ollama = self._get_ollama()
        if ollama.available():
            return ollama.generate(
                messages,
                instructions=instructions,
                model=model,
                temperature=temperature,
            )
        raise RuntimeError(
            "No local conversational provider is available. "
            "Promote a Medha decoder checkpoint or start Ollama with a local model."
        )


router = ModelRouter()
