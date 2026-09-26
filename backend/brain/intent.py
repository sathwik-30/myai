import re
from typing import Literal

Intent = Literal["casual", "technical", "memory", "general"]

TECHNICAL_TERMS = {
    "api", "algorithm", "array", "backend", "bug", "code", "coding", "compiler",
    "database", "dbms", "docker", "error", "fastapi", "framework", "git", "github",
    "java", "javascript", "linux", "microservice", "model", "network", "npm",
    "python", "react", "sql", "spring", "tensorflow", "technology", "technical",
    "program", "programming", "server", "software", "syntax", "system", "web",
    "machine learning", "artificial intelligence", "ai", "cyber security",
}

MEMORY_CUES = (
    "remember this", "remember that", "don't forget", "do not forget",
    "keep in mind", "save this", "store this", "my preference is",
    "i prefer", "i like", "i dislike", "i use", "i want you to remember",
    "call me", "my name is",
)

CASUAL_STARTS = (
    "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
    "how are you", "what are you doing", "thanks", "thank you",
)

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def classify(message: str) -> Intent:
    text = " ".join(message.lower().strip().split())
    tokens = _tokens(text)

    if any(cue in text for cue in MEMORY_CUES):
        return "memory"

    if any(text == start or text.startswith(start + " ") for start in CASUAL_STARTS):
        return "casual"

    if any(term in text for term in TECHNICAL_TERMS if " " in term) or tokens.intersection(
        {term for term in TECHNICAL_TERMS if " " not in term}
    ):
        return "technical"

    if text.endswith("?") and len(tokens) <= 12:
        return "casual"

    return "general"
