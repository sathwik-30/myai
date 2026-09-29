from pathlib import Path


def checkpoint_exists(path: str = "models/checkpoints/medha-small.pt") -> bool:
    return Path(path).is_file()


def summarize_checkpoint(path: str = "models/checkpoints/medha-small.pt") -> dict:
    file = Path(path)
    return {"path": str(file), "exists": file.is_file(), "size_bytes": file.stat().st_size if file.is_file() else 0}
