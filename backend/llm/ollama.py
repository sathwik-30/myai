import os
from typing import Any, Dict, List

import requests

from backend.llm.provider import LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.base_url = os.getenv("MEDHA_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("MEDHA_OLLAMA_MODEL", "llama3.2:3b")
        self.timeout = float(os.getenv("MEDHA_OLLAMA_TIMEOUT", "30"))

    def available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.ok
        except requests.RequestException:
            return False

    def generate(
        self,
        messages: List[Dict[str, str]],
        instructions: str = "",
        model: str | None = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        system = instructions.strip()
        payload_messages = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(
            {"role": str(item.get("role", "user")), "content": str(item.get("content", ""))}
            for item in messages
            if item.get("content")
        )

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": model or self.model,
                "messages": payload_messages,
                "stream": False,
                "options": {"temperature": max(0.0, min(float(temperature), 1.5))},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        message = data.get("message") or {}
        content = str(message.get("content", "")).strip()
        if not content:
            raise RuntimeError("Ollama returned an empty response.")
        return {"text": content, "model": model or self.model, "provider": self.name}


provider = OllamaProvider()
