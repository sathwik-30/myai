"""Train Medha's local decoder with deterministic train/validation evaluation."""
from dataclasses import asdict
from pathlib import Path
import random
import torch
import torch.nn.functional as F
from backend.model.architecture.decoder import MedhaDecoderLM
from backend.model.config import SMALL_CONFIG
from backend.model.tokenizer.persistent import PersistentTokenizer
from backend.training.dataset import load_texts, make_causal_examples

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def _loss(model, examples):
    model.eval()
    total, count = 0.0, 0
    with torch.no_grad():
        for input_ids, targets in examples:
            x = torch.tensor([input_ids], dtype=torch.long)
            y = torch.tensor([targets], dtype=torch.long)
            logits = model(x)
            total += float(F.cross_entropy(
                logits.reshape(-1, logits.size(-1)), y.reshape(-1)
            ).item())
            count += 1
    model.train()
    return total / max(1, count)

def train(steps: int = 500, data_root: str | None = None, checkpoint_dir: str | None = None):
    data_path = Path(data_root) if data_root is not None else PROJECT_ROOT / "data"
    checkpoint_path = Path(checkpoint_dir) if checkpoint_dir is not None else PROJECT_ROOT / "models/checkpoints"
    texts = load_texts(data_path)
    if not texts:
        raise ValueError("No curated local training text found.")

    tokenizer = PersistentTokenizer()
    tokenizer.train_texts(texts)
    tokenizer.save()

    token_ids = []
    for text in texts:
        token_ids.extend(tokenizer.encode(text))

    config = SMALL_CONFIG
    vocab_size = max(config.vocab_size, len(tokenizer.tokenizer.vocab))
    config = type(config)(**{**asdict(config), "vocab_size": vocab_size})
    examples = make_causal_examples(token_ids, config.max_length, stride=max(1, config.max_length // 2))
    if len(examples) < 2:
        raise ValueError("Training corpus is too small for a train/validation split.")

    split = max(1, int(len(examples) * 0.9))
    train_examples = examples[:split]
    val_examples = examples[split:] or examples[-1:]

    torch.manual_seed(42)
    random.seed(42)
    model = MedhaDecoderLM(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
    model.train()

    steps = max(1, int(steps))
    for step in range(steps):
        input_ids, targets = train_examples[step % len(train_examples)]
        x = torch.tensor([input_ids], dtype=torch.long)
        y = torch.tensor([targets], dtype=torch.long)
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), y.reshape(-1))
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

    train_loss = _loss(model, train_examples)
    validation_loss = _loss(model, val_examples)

    output = checkpoint_path
    output.mkdir(parents=True, exist_ok=True)
    checkpoint = output / "medha-small.pt"
    torch.save({
        "config": asdict(config),
        "state_dict": model.state_dict(),
        "training": {
            "steps": steps,
            "train_examples": len(train_examples),
            "validation_examples": len(val_examples),
            "train_loss": train_loss,
            "validation_loss": validation_loss,
        },
    }, checkpoint)

    return {
        "checkpoint": str(checkpoint),
        "steps": steps,
        "train_loss": train_loss,
        "validation_loss": validation_loss,
        "examples": len(examples),
    }

if __name__ == "__main__":
    print(train())
