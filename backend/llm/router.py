"""Model routing boundary for Medha.

Medha uses its own promoted local decoder for generative responses.
No Ollama or hosted/cloud model is part of the runtime.
"""
from typing import Any, Dict, List

from backend.model.runtime import get_decoder_runtime


class ModelRouter:
    """Expose the local Medha decoder as the only generative provider."""

    @property
    def provider_name(self) -> str:
        try:
            return "local-decoder" if get_decoder_runtime().available else "none"
        except Exception:
            return "none"

    def available(self) -> bool:
        return self.provider_name == "local-decoder"

    def generate(
        self,
        messages: List[Dict[str, str]],
        instructions: str = "",
        model: str | None = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        runtime = get_decoder_runtime()
        if not runtime.available:
            raise RuntimeError(
                "Medha's local decoder is unavailable. "
                "Promote a valid local decoder checkpoint before generating responses."
            )

        context = []
        for item in messages:
            content = str(item.get("content", "")).strip()
            if content:
                context.append(f"{item.get('role', 'user')}: {content}")
        prompt = (
            instructions.strip()
            + "\n\n"
            + "\n".join(context)
            + "\nMedha:"
        ).strip()

        text = runtime.generate(
            prompt,
            max_new_tokens=128,
            temperature=temperature,
            top_k=24,
        ).strip()
        if not text:
            raise RuntimeError("Medha local decoder returned an empty response.")
        return {
            "text": text,
            "model": model or "medha-small",
            "provider": self.provider_name,
        }


router = ModelRouter()
