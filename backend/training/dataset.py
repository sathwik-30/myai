from pathlib import Path
import hashlib

ALLOWED_SUFFIXES = {".txt", ".md"}
EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", "node_modules", "models", "data/nlu"}

def _is_training_file(path: Path, root: Path) -> bool:
    if path.suffix.lower() not in ALLOWED_SUFFIXES or not path.is_file():
        return False
    relative = path.relative_to(root).as_posix().lower()
    return not any(relative == part or relative.startswith(part + "/") for part in EXCLUDED_PARTS)

def load_texts(root: str | Path = "data") -> list[str]:
    """Load curated text while excluding generated/runtime artifacts."""
    root = Path(root).resolve()
    texts, seen = [], set()
    if not root.exists():
        return []
    for path in sorted(root.rglob("*")):
        if not _is_training_file(path, root):
            continue
        try:
            content = path.read_text(encoding="utf-8").strip()
        except (UnicodeDecodeError, OSError):
            continue
        if not content:
            continue
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        texts.append(content)
    return texts

def make_causal_examples(token_ids: list[int], block_size: int, stride: int | None = None) -> list[tuple[list[int], list[int]]]:
    if block_size < 1:
        raise ValueError("block_size must be positive")
    if len(token_ids) < block_size + 1:
        return []
    stride = block_size if stride is None else int(stride)
    if stride < 1:
        raise ValueError("stride must be positive")
    examples = []
    for start in range(0, len(token_ids) - block_size, stride):
        chunk = token_ids[start:start + block_size + 1]
        if len(chunk) == block_size + 1:
            examples.append((chunk[:-1], chunk[1:]))
    return examples
