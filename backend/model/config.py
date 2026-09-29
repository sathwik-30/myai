"""Configuration for Medha's trainable local decoder model."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int = 4096
    embedding_dim: int = 256
    num_heads: int = 8
    hidden_dim: int = 1024
    num_layers: int = 6
    max_length: int = 512
    dropout: float = 0.1


SMALL_CONFIG = ModelConfig(
    vocab_size=4096,
    embedding_dim=256,
    num_heads=8,
    hidden_dim=1024,
    num_layers=6,
    max_length=512,
)
