from pathlib import Path
from typing import Dict, List

# Temporary resources are files supplied for a current exam/project/task.
RESOURCE_ROOT = Path(__file__).resolve().parents[1] / "memory" / "temporary" / "resources"
SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown"}
IGNORED_FILENAMES = {"README.md"}


def load_resources() -> List[Dict[str, str]]:
    RESOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    resources = []
    ignored = {name.lower() for name in IGNORED_FILENAMES}

    for path in sorted(RESOURCE_ROOT.rglob("*")):
        if (
            not path.is_file()
            or path.suffix.lower() not in SUPPORTED_EXTENSIONS
            or path.name.lower() in ignored
        ):
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


def _relevant_excerpt(text: str, query_words: set[str], limit: int = 1800) -> str:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]

    scored = []
    for index, paragraph in enumerate(paragraphs):
        words = {word.lower() for word in paragraph.split() if len(word) > 2}
        overlap = len(query_words & words)
        if overlap:
            scored.append((overlap, -index, paragraph))

    if not scored:
        return text[:limit]

    scored.sort(reverse=True)
    selected = [item[2] for item in scored[:3]]
    return "\n\n".join(selected)[:limit]


def search_resources(query: str, limit: int = 3) -> List[Dict[str, str]]:
    resources = load_resources()
    if not resources:
        return []

    query_words = {word.lower() for word in query.split() if len(word) > 2}
    if not query_words:
        return []

    scored = []
    for item in resources:
        words = {word.lower() for word in item["text"].split() if len(word) > 2}
        overlap = len(query_words & words)
        if overlap:
            scored.append((overlap / max(len(query_words), 1), item))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    results = []
    for score, item in scored[:limit]:
        if score < 0.20:
            continue
        result = dict(item)
        result["text"] = _relevant_excerpt(item["text"], query_words)
        result["score"] = round(score, 4)
        results.append(result)

    return results
