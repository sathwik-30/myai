import os
from typing import Any, Dict, List

import requests

from backend.llm.provider import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI Responses API adapter, disabled unless MEDHA_OPENAI_API_KEY exists."""

    name = "openai"

    def __init__(self):
        self.api_key = os.getenv("MEDHA_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.default_model = os.getenv("MEDHA_CLOUD_MODEL", "gpt-5.6-sol")
        self.timeout = float(os.getenv("MEDHA_LLM_TIMEOUT", "60"))

    def available(self) -> bool:
        return bool(self.api_key)

    def generate(
        self,
        messages: List[Dict[str, str]],
        instructions: str = "",
        model: str | None = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        if not self.available():
            raise RuntimeError("OpenAI provider is not configured")

        input_items = [
            {
                "role": item["role"],
                "content": item["message"],
            }
            for item in messages
            if item.get("role") in {"user", "assistant", "system"} and item.get("message")
        ]

        payload = {
            "model": model or self.default_model,
            "input": input_items,
        }
        if instructions:
            payload["instructions"] = instructions

        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        output_text = data.get("output_text")
        if not output_text:
            parts = []
            for item in data.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") in {"output_text", "text"} and content.get("text"):
                        parts.append(content["text"])
            output_text = "\n".join(parts).strip()

        if not output_text:
            raise RuntimeError("The model returned no text output")

        return {
            "answer": output_text.strip(),
            "source": "llm:openai",
            "model": payload["model"],
            "response_id": data.get("id"),
            "usage": data.get("usage", {}),
        }
