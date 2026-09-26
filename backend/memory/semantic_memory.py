import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FILE_PATH = os.path.join(DATA_DIR, "semantic_memory.json")

DEFAULT_MEMORIES = [
    ("Hi", "Hi Sathwik. I'm here. How are you?", "casual"),
    ("Hello", "Hello Sathwik. What are we working on?", "casual"),
    ("Hey Medha", "Hey Sathwik. I'm here.", "casual"),
    ("Good morning", "Good morning, Sathwik. What are we working on?", "casual"),
    ("How are you?", "I'm functioning normally and ready to talk with you.", "casual"),
    ("What are you doing?", "I'm here, processing what you need and ready to help.", "casual"),
    ("Thanks", "You're welcome.", "casual"),
    ("Thank you", "You're welcome.", "casual"),
    ("Who are you?", "I'm Medha, your personal AI assistant.", "identity"),
    ("What is your name?", "My name is Medha.", "identity"),
    ("What can you do?", "I can learn from our conversations, retrieve what I've learned, answer questions from stored knowledge, and use connected tools when available.", "capability"),
]

_STOP_WORDS = {
    "a", "an", "the", "is", "am", "are", "was", "were", "be", "been",
    "to", "of", "for", "in", "on", "at", "with", "and", "or", "but",
    "i", "me", "my", "you", "your", "we", "our", "it", "this", "that",
    "can", "could", "would", "should", "do", "does", "did", "please",
}

def _normalize(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = [word for word in text.split() if word not in _STOP_WORDS]
    return " ".join(words)

def _load() -> List[Dict[str, Any]]:
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(FILE_PATH):
        items = [
            {
                "text": text,
                "answer": answer,
                "memory_type": memory_type,
                "source": "built_in_memory",
                "metadata": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            for text, answer, memory_type in DEFAULT_MEMORIES
        ]
        _save(items)
        return items

    try:
        with open(FILE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []

def _save(items: List[Dict[str, Any]]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_file = FILE_PATH + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(items, file, indent=2, ensure_ascii=False)
    os.replace(temp_file, FILE_PATH)

def remember(
    text: str,
    answer: str,
    memory_type: str = "conversation",
    source: str = "memory",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    if not text or not answer:
        return

    items = _load()
    normalized = _normalize(text)

    # Update an existing memory instead of creating an identical duplicate.
    for item in items:
        if _normalize(item.get("text", "")) == normalized and normalized:
            item.update({
                "answer": answer,
                "memory_type": memory_type,
                "source": source,
                "metadata": metadata or item.get("metadata", {}),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            _save(items)
            return

    items.append({
        "text": text,
        "answer": answer,
        "memory_type": memory_type,
        "source": source,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    _save(items)

def search(
    text: str,
    top_k: int = 3,
    min_score: float = 0.30,
) -> List[Dict[str, Any]]:
    if not str(text or "").strip():
        return []

    items = _load()
    if not items:
        return []

    documents = [_normalize(item.get("text", "")) for item in items]
    query = _normalize(text)

    if not query:
        return []

    try:
        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            min_df=1,
            sublinear_tf=True,
        )
        matrix = vectorizer.fit_transform(documents + [query])
        query_vector = matrix[-1]
        memory_matrix = matrix[:-1]
        scores = cosine_similarity(query_vector, memory_matrix)[0]
    except ValueError:
        return []

    ranked = sorted(
        zip(items, scores),
        key=lambda pair: float(pair[1]),
        reverse=True,
    )

    results = []
    for item, score in ranked[:top_k]:
        score = float(score)
        if score < min_score:
            continue
        result = dict(item)
        result["score"] = round(score, 4)
        results.append(result)

    return results

def count() -> int:
    return len(_load())

def recent(limit: int = 10) -> List[Dict[str, Any]]:
    items = _load()
    return list(reversed(items[-max(1, limit):]))
