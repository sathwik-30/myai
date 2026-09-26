import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FILE_PATH = os.path.join(DATA_DIR, "semantic_memory.json")
MODEL_NAME = "all-MiniLM-L6-v2"
_model = None

DEFAULT_MEMORIES = [
    ("Hi", "Hi Sathwik. I'm here. How are you?", "casual"),
    ("Hello", "Hello Sathwik. What are we working on?", "casual"),
    ("Hey Medha", "Hey Sathwik. I'm here.", "casual"),
    ("How are you?", "I'm functioning normally and ready to talk with you.", "casual"),
    ("What are you doing?", "I'm here, processing what you need and ready to help.", "casual"),
    ("Thanks", "You're welcome.", "casual"),
    ("Thank you", "You're welcome.", "casual"),
    ("Who are you?", "I'm Medha, your personal AI assistant.", "identity"),
    ("What is your name?", "My name is Medha.", "identity"),
    ("What can you do?", "I can learn from our conversations, retrieve what I've learned, answer questions from stored knowledge, and use connected tools when available.", "capability"),
]

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def _load() -> List[Dict[str, Any]]:
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(FILE_PATH):
        items = []
        for text, answer, memory_type in DEFAULT_MEMORIES:
            vector = _get_model().encode([text], normalize_embeddings=True)[0].tolist()
            items.append({
                "text": text,
                "answer": answer,
                "memory_type": memory_type,
                "source": "built_in_memory",
                "embedding": vector,
                "metadata": {},
                "created_at": datetime.utcnow().isoformat(),
            })
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

def remember(text: str, answer: str, memory_type: str = "conversation",
             source: str = "memory", metadata: Optional[Dict[str, Any]] = None) -> None:
    if not text or not answer:
        return
    items = _load()
    vector = _get_model().encode([text], normalize_embeddings=True)[0].tolist()
    items.append({
        "text": text,
        "answer": answer,
        "memory_type": memory_type,
        "source": source,
        "embedding": vector,
        "metadata": metadata or {},
        "created_at": datetime.utcnow().isoformat(),
    })
    _save(items)

def search(text: str, top_k: int = 3, min_score: float = 0.45) -> List[Dict[str, Any]]:
    items = _load()
    if not items:
        return []

    query_vector = _get_model().encode([text], normalize_embeddings=True)
    valid_items = [item for item in items if item.get("embedding")]

    if not valid_items:
        return []

    matrix = [item["embedding"] for item in valid_items]
    scores = cosine_similarity(query_vector, matrix)[0]

    ranked = sorted(
        zip(valid_items, scores),
        key=lambda pair: float(pair[1]),
        reverse=True,
    )

    results = []
    for item, score in ranked[:top_k]:
        if float(score) < min_score:
            continue
        result = dict(item)
        result["score"] = float(score)
        results.append(result)

    return results
