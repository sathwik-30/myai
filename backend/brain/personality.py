"""Configurable Medha personality.

Personality is runtime configuration, not model weights, so it can evolve without
retraining the language model.
"""
from dataclasses import asdict, dataclass


@dataclass
class Personality:
    name: str = "Medha"
    warmth: float = 0.8
    humor: float = 0.4
    directness: float = 0.9
    curiosity: float = 0.9
    patience: float = 0.9
    formality: float = 0.3
    verbosity: float = 0.6

    def update(self, **values) -> None:
        for key, value in values.items():
            if not hasattr(self, key):
                raise ValueError(f"Unknown personality field: {key}")
            if key == "name":
                setattr(self, key, str(value).strip() or "Medha")
            else:
                setattr(self, key, max(0.0, min(1.0, float(value))))

    def snapshot(self) -> dict:
        return asdict(self)


personality = Personality()
