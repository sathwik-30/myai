"""Fine-tune Medha's conversational model.

Teacher/base models are used only during training. The resulting
models/conversational-medha checkpoint is the only learned-model runtime.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import torch
from torch.utils.data import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "conversations"
OUTPUT_DIR = ROOT / "models" / "conversational-medha"
TRAIN_BASE_MODEL = os.getenv("MEDHA_TRAIN_BASE_MODEL", "Qwen/Qwen2.5-0.5B")
MAX_LENGTH = int(os.getenv("MEDHA_TRAIN_MAX_LENGTH", "512"))


def load_conversations() -> list[list[dict[str, str]]]:
    rows: list[list[dict[str, str]]] = []
    for path in sorted(DATA_DIR.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                messages = item.get("messages")
                if not isinstance(messages, list) or not messages:
                    continue
                clean = []
                for message in messages:
                    role = str(message.get("role", "")).strip()
                    content = str(message.get("content", "")).strip()
                    if role in {"user", "assistant", "system"} and content:
                        clean.append({"role": role, "content": content})
                if len(clean) >= 2:
                    rows.append(clean)
    if len(rows) < 10:
        raise RuntimeError(
            f"Need at least 10 valid conversations; found {len(rows)}. "
            "Add more varied examples before training."
        )
    return rows


class ConversationDataset(Dataset):
    def __init__(self, rows, tokenizer, max_length: int):
        self.examples = []
        for messages in rows:
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            encoded = tokenizer(
                text, truncation=True, max_length=max_length, add_special_tokens=False
            )
            ids = encoded["input_ids"]
            if len(ids) >= 2:
                self.examples.append(torch.tensor(ids, dtype=torch.long))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, index):
        ids = self.examples[index]
        return {"input_ids": ids, "labels": ids.clone()}


class ConversationCollator:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token

    def __call__(self, features):
        max_len = max(item["input_ids"].numel() for item in features)
        pad_id = self.tokenizer.pad_token_id
        input_ids, labels, attention = [], [], []
        for item in features:
            ids = item["input_ids"]
            padding = torch.full((max_len - ids.numel(),), pad_id, dtype=torch.long)
            input_ids.append(torch.cat([ids, padding]))
            labels.append(torch.cat([ids, torch.full_like(padding, -100)]))
            attention.append(torch.cat([torch.ones_like(ids), torch.zeros_like(padding)]))
        return {
            "input_ids": torch.stack(input_ids),
            "labels": torch.stack(labels),
            "attention_mask": torch.stack(attention),
        }


def main():
    rows = load_conversations()
    print(f"Loaded {len(rows)} conversations.")
    print(f"Training base model: {TRAIN_BASE_MODEL}")
    print("Teacher/base model is training-only; runtime will load Medha's saved checkpoint.")

    tokenizer = AutoTokenizer.from_pretrained(TRAIN_BASE_MODEL)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        TRAIN_BASE_MODEL,
        dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )

    dataset = ConversationDataset(rows, tokenizer, MAX_LENGTH)
    if len(dataset) < 10:
        raise RuntimeError("Too few tokenized training examples.")

    args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=float(os.getenv("MEDHA_EPOCHS", "3")),
        per_device_train_batch_size=int(os.getenv("MEDHA_BATCH_SIZE", "1")),
        gradient_accumulation_steps=int(os.getenv("MEDHA_GRAD_ACCUM", "8")),
        learning_rate=float(os.getenv("MEDHA_LR", "2e-5")),
        logging_steps=5,
        save_strategy="epoch",
        report_to="none",
        fp16=torch.cuda.is_available(),
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
        data_collator=ConversationCollator(tokenizer),
    )
    trainer.train()
    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))
    print(f"Saved trained Medha brain to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
