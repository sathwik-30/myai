from pathlib import Path
from typing import Dict, List

RESOURCE_ROOT = Path(__file__).resolve().parent / "resources"
SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown"}


def load_resources() -> List[Dict[str, str]]:
    RESOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    resources = []

    for path in sorted(RESOURCE_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        if text.strip():
            resources.append({
                "name": path.name,
                "path": str(path.relative_to(RESOURCE_ROOT)),
                "text": text.strip(),
            })

    return resources


def search_resources(query: str, limit: int = 3) -> List[Dict[str, str]]:
    resources = load_resources()
    if not resources:
        return []

    query_words = {word.lower() for word in query.split() if len(word) > 2}
    scored = []

    for item in resources:
        words = {word.lower() for word in item["text"].split() if len(word) > 2}
        overlap = len(query_words & words)
        if overlap:
            scored.append((overlap / max(len(query_words), 1), item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for score, item in scored[:limit] if score >= 0.20]
