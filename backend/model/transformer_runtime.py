"""Local pretrained language-model runtime for Medha.

The model is loaded locally after its first download and is never called
through a hosted API. Set MEDHA_BASE_MODEL to a local model directory or
a Hugging Face model id.
"""
from __future__ import annotations

import os

import torch

DEFAULT_MODEL = os.getenv("MEDHA_BASE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")


class TransformerRuntime:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.error: str | None = None
        self._load()

    @property
    def available(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def _load(self) -> None:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=dtype,
                low_cpu_mem_usage=True,
            )
            self.model.eval()
            if torch.cuda.is_available():
                self.model.to("cuda")
        except Exception as exc:
            self.tokenizer = None
            self.model = None
            self.error = str(exc)

    @torch.no_grad()
    def generate(
        self,
        messages: list[dict[str, str]],
        max_new_tokens: int = 128,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        if not self.available:
            raise RuntimeError(self.error or "Transformer language model is unavailable.")

        inputs = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        device = next(self.model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}

        output = self.model.generate(
            **inputs,
            max_new_tokens=max(1, min(int(max_new_tokens), 512)),
            do_sample=True,
            temperature=max(0.1, float(temperature)),
            top_p=min(1.0, max(0.1, float(top_p))),
            repetition_penalty=1.05,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        generated = output[0][inputs["input_ids"].shape[-1]:]
        return self.tokenizer.decode(generated, skip_special_tokens=True).strip()


_runtime: TransformerRuntime | None = None


def get_transformer_runtime() -> TransformerRuntime:
    global _runtime
    if _runtime is None:
        _runtime = TransformerRuntime()
    return _runtime
