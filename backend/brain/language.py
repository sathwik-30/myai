import re
from typing import Literal

Language = Literal["english", "telugu", "roman_telugu", "mixed"]

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")
LATIN_RE = re.compile(r"[A-Za-z]")

# Common Roman-Telugu words/patterns. This is intentionally conservative so
# ordinary English text is not accidentally classified as Roman Telugu.
ROMAN_TELUGU_TERMS = {
    "nenu", "naaku", "naku", "naa", "na", "naatho", "naato",
    "nuvvu", "nee", "ni", "neeku", "neeku", "neetho", "neeto",
    "ela", "unnavu", "unnav", "vunnavu", "vunnav", "unnava", "vunnava",
    "bagunnanu", "bagunna", "baga", "baagunnanu", "baagunna",
    "em", "enti", "enduku", "eppudu", "ekkada", "evvaru", "evaru",
    "chesunnav", "chestunnav", "chestunnavu", "chesav", "chesavu",
    "matladutunnav", "matladutunnavu", "maatladutunnav",
    "undhi", "undi", "unnadi", "ledu", "ledhu",
    "avunu", "kaadu", "kadu", "sare", "aithe", "inka",
    "manam", "mana", "maa", "maaku", "memu", "meeru", "mee",
    "cheppu", "cheppandi", "ivvu", "ivvandi", "telusu", "teliyadu",
    "naaku", "naku", "ishtam", "istam", "nachindi", "nachutundi",
    "dhanyavadalu", "thanks", "ra", "raa", "andi",
}

ROMAN_TELUGU_PATTERNS = (
    r"\bnuvvu\s+ela\s+(unn|vunn)",
    r"\bnenu\s+(baga|baaga)\s+(unna|vunna)",
    r"\b(em|enti)\s+(ches|chest)",
    r"\b(ela|enduku|eppudu|ekkada)\s+",
    r"\bnaaku\s+",
    r"\bneeku\s+",
    r"\bmee?ru\s+",
)


def _roman_telugu_score(value: str) -> int:
    text = re.sub(r"[^a-zA-Z\s]", " ", value.lower())
    tokens = set(text.split())
    score = sum(1 for token in tokens if token in ROMAN_TELUGU_TERMS)
    score += sum(2 for pattern in ROMAN_TELUGU_PATTERNS if re.search(pattern, text))
    return score


def detect_language(text: str) -> Language:
    value = str(text or "").strip()
    telugu = len(TELUGU_RE.findall(value))
    latin = len(LATIN_RE.findall(value))

    if telugu and latin:
        return "mixed"
    if telugu:
        return "telugu"

    if latin:
        score = _roman_telugu_score(value)
        if score >= 2:
            return "roman_telugu"

    return "english"
