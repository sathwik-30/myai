"""Minimal local training entry point for Medha's decoder model."""
from dataclasses import asdict
from pathlib import Path

import torch
import torch.nn.functional as F

from backend.model.architecture.decoder import MedhaDecoderLM
from backend.model.config import SMALL_CONFIG
from backend.model.tokenizer.persistent import PersistentTokenizer
from backend.training.dataset import load_texts, make_causal_examples

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def train(steps: int = 100, data_root: str | None = None, checkpoint_dir: str | None = None):
    data_path = Path(data_root) if data_root is not None else PROJECT_ROOT / "data"
    checkpoint_path = Path(checkpoint_dir) if checkpoint_dir is not None else PROJECT_ROOT / "models/checkpoints"
    texts = load_texts(data_path)
    if not texts:
        raise ValueError("No local training text found.")

    tokenizer = PersistentTokenizer()
    tokenizer.train_texts(texts)
    tokenizer.save()

    token_ids = []
    for text in texts:
        token_ids.extend(tokenizer.encode(text))

    config = SMALL_CONFIG
    vocab_size = max(config.vocab_size, len(tokenizer.tokenizer.vocab))
    config = type(config)(**{**asdict(config), "vocab_size": vocab_size})
    examples = make_causal_examples(token_ids, config.max_length)
    if not examples:
        raise ValueError("Training corpus is too small for the configured block size.")

    model = MedhaDecoderLM(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)
    model.train()

    for step in range(max(1, steps)):
        input_ids, targets = examples[step % len(examples)]
        x = torch.tensor([input_ids], dtype=torch.long)
        y = torch.tensor([targets], dtype=torch.long)
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), y.reshape(-1))
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

    output = checkpoint_path
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "medha-small.pt"
    torch.save({"config": asdict(config), "state_dict": model.state_dict()}, checkpoint)
    return {"checkpoint": str(checkpoint), "steps": max(1, steps), "loss": float(loss.item())}


if __name__ == "__main__":
    print(train())
