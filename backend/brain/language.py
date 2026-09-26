import re
from typing import Literal

Language = Literal["english", "telugu", "mixed"]

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")
LATIN_RE = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> Language:
    value = str(text or "")
    telugu = len(TELUGU_RE.findall(value))
    latin = len(LATIN_RE.findall(value))

    if telugu and latin:
        return "mixed"
    if telugu:
        return "telugu"
    return "english"
