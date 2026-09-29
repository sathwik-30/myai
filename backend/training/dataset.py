from pathlib import Path


def load_texts(root: str | Path = "data") -> list[str]:
    """Load local training text without sending data to an external provider."""
    root = Path(root)
    texts = []
    for path in root.rglob("*"):
        if path.suffix.lower() in {".txt", ".md", ".jsonl"} and path.is_file():
            try:
                content = path.read_text(encoding="utf-8").strip()
            except UnicodeDecodeError:
                continue
            if content:
                texts.append(content)
    return texts


def make_causal_examples(token_ids: list[int], block_size: int) -> list[tuple[list[int], list[int]]]:
    examples = []
    for start in range(0, max(0, len(token_ids) - block_size), block_size):
        chunk = token_ids[start:start + block_size + 1]
        if len(chunk) == block_size + 1:
            examples.append((chunk[:-1], chunk[1:]))
    return examples
