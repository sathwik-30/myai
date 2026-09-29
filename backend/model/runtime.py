"""Runtime loader for a promoted local decoder checkpoint.

A training checkpoint is never used automatically. Promotion is an explicit
quality-gated operation, and tokenizer/model vocabulary must match exactly.
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
            vocab_size = len(tokenizer.tokenizer.vocab)
            if vocab_size != config.vocab_size:
                raise RuntimeError(
                    f"Tokenizer/model vocabulary mismatch: tokenizer={vocab_size}, model={config.vocab_size}."
                )
            training = payload.get("training", {})
            validation_loss = training.get("validation_loss")
            if validation_loss is None or not torch.isfinite(torch.tensor(float(validation_loss))):
                raise RuntimeError("Production checkpoint has no finite validation loss.")
            model = MedhaDecoderLM(config)
            model.load_state_dict(payload["state_dict"], strict=True)
            model.eval()
            self.model, self.tokenizer = model, tokenizer
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
        original_ids = self.tokenizer.encode(prompt)
        generated = list(original_ids[-self.model.config.max_length:])
        for _ in range(max(1, min(int(max_new_tokens), 256))):
            context = torch.tensor([generated[-self.model.config.max_length:]], dtype=torch.long)
            logits = self.model(context)[0, -1] / max(0.1, float(temperature))
            k = max(1, min(int(top_k), logits.numel()))
            values, indices = torch.topk(logits, k)
            next_id = int(indices[torch.multinomial(torch.softmax(values, -1), 1)].item())
            generated.append(next_id)
            if next_id == self.tokenizer.tokenizer.vocab.token_to_id.get("<EOS>"):
                break
        new_ids = generated[len(original_ids[-self.model.config.max_length:]):]
        return self.tokenizer.decode(new_ids).strip()

_runtime = None

def get_decoder_runtime():
    global _runtime
    if _runtime is None:
        _runtime = LocalDecoderRuntime()
    return _runtime
