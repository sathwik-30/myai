from abc import ABC, abstractmethod
from typing import Any, Dict, List


class LLMProvider(ABC):
    """Model provider contract. Medha's brain stays independent of any vendor."""

    name = "unknown"

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        instructions: str = "",
        model: str | None = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        raise NotImplementedError
