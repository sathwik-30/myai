import os
from typing import Any, Dict, List

from backend.llm.openai_provider import OpenAIProvider


class ModelRouter:
    """
    Central model router.

    Policy:
    - explicit MEDHA_MODEL_PROVIDER wins
    - otherwise use configured cloud model
    - if no model provider is configured, return unavailable rather than fake AI
    """

    def __init__(self):
        self.provider_name = os.getenv("MEDHA_MODEL_PROVIDER", "openai").strip().lower()
        self.openai = OpenAIProvider()

    def _provider(self):
        if self.provider_name == "openai":
            return self.openai
        return None

    def available(self) -> bool:
        provider = self._provider()
        return bool(provider and provider.available())

    def generate(
        self,
        messages: List[Dict[str, str]],
        instructions: str = "",
        model: str | None = None,
    ) -> Dict[str, Any]:
        provider = self._provider()
        if provider is None:
            raise RuntimeError(f"Unknown model provider: {self.provider_name}")
        if not provider.available():
            raise RuntimeError("No configured LLM provider is available")
        return provider.generate(messages, instructions=instructions, model=model)


router = ModelRouter()
