import json
from pathlib import Path

from backend.model.tokenizer.tokenizer import Tokenizer


class PersistentTokenizer:
    """Persist Medha's vocabulary independently from model checkpoints."""

    def __init__(self, path: str | Path = "models/tokenizer/vocab.json"):
        self.path = Path(path)
        self.tokenizer = Tokenizer()

    def train_texts(self, texts: list[str]) -> None:
        for text in texts:
            self.tokenizer.train(text)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "token_to_id": self.tokenizer.vocab.token_to_id,
            "special_tokens": ["<PAD>", "<UNK>", "<BOS>", "<EOS>"],
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> None:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.tokenizer.vocab.token_to_id = {
            str(k): int(v) for k, v in payload["token_to_id"].items()
        }
        self.tokenizer.vocab.id_to_token = {
            int(v): str(k) for k, v in self.tokenizer.vocab.token_to_id.items()
        }

    def encode(self, text: str) -> list[int]:
        return self.tokenizer.encode(text)

    def decode(self, ids: list[int]) -> str:
        return self.tokenizer.decode(ids)
