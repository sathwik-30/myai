"""Runtime loader for a promoted local decoder checkpoint.

Training checkpoints are never used automatically. A checkpoint must be copied
to models/production/medha-small.pt before this runtime exposes it.
"""
from pathlib import Path
import torch

from backend.model.architecture.decoder import MedhaDecoderLM
from backend.model.tokenizer.persistent import PersistentTokenizer
from backend.model.config import ModelConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_CHECKPOINT = PROJECT_ROOT / "models/production/medha-small.pt"

class LocalDecoderRuntime:
    def __init__(self, checkpoint: str | Path = PRODUCTION_CHECKPOINT):
        self.checkpoint_path = Path(checkpoint)
        self.model = None
        self.tokenizer = None
        self.error = None
        self._load()

    @property
    def available(self):
        return self.model is not None and self.tokenizer is not None

    def _load(self):
        if not self.checkpoint_path.is_file():
            self.error = "No promoted production decoder checkpoint."
            return
        try:
            payload = torch.load(self.checkpoint_path, map_location="cpu", weights_only=False)
            config = ModelConfig(**payload["config"])
            tokenizer = PersistentTokenizer()
            tokenizer.load()
            if len(tokenizer.tokenizer.vocab) > config.vocab_size:
                raise RuntimeError("Tokenizer vocabulary is larger than checkpoint vocabulary.")
            model = MedhaDecoderLM(config)
            model.load_state_dict(payload["state_dict"])
            model.eval()
            self.model = model
            self.tokenizer = tokenizer
        except Exception as exc:
            self.model = None
            self.tokenizer = None
            self.error = str(exc)

    @torch.no_grad()
    def generate(self, prompt: str, max_new_tokens: int = 96, temperature: float = 0.8, top_k: int = 20):
        if not self.available:
            raise RuntimeError(self.error or "Local decoder is unavailable.")
        if not str(prompt or "").strip():
            return ""
        ids = self.tokenizer.encode(prompt)
        ids = ids[-self.model.config.max_length:]
        generated = list(ids)

        for _ in range(max(1, min(int(max_new_tokens), 256))):
            context = torch.tensor([generated[-self.model.config.max_length:]], dtype=torch.long)
            logits = self.model(context)[0, -1]
            temperature = max(0.1, float(temperature))
            logits = logits / temperature
            k = max(1, min(int(top_k), logits.numel()))
            values, indices = torch.topk(logits, k)
            probs = torch.softmax(values, dim=-1)
            next_id = int(indices[torch.multinomial(probs, 1)].item())
            generated.append(next_id)
            if next_id == self.tokenizer.tokenizer.vocab.token_to_id.get("<EOS>"):
                break

        new_ids = generated[len(ids):]
        return self.tokenizer.decode(new_ids).strip()

_runtime = None

def get_decoder_runtime():
    global _runtime
    if _runtime is None:
        _runtime = LocalDecoderRuntime()
    return _runtime
