import json
import os
import re
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FILE_PATH = os.path.join(DATA_DIR, "learned_knowledge.json")


def _normalize(text):
    return re.sub(
        r"\s+",
        " ",
        text.lower().strip()
    )


def _load():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(FILE_PATH):
        return []

    try:
        with open(FILE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

    except (json.JSONDecodeError, OSError):
        pass

    return []


def _save(data):
    os.makedirs(DATA_DIR, exist_ok=True)

    temp_file = FILE_PATH + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    os.replace(temp_file, FILE_PATH)


def search_memory(question):
    question_words = set(
        _normalize(question).split()
    )

    if not question_words:
        return None

    memories = _load()

    best_match = None
    best_score = 0

    for item in memories:
        stored_words = set(
            _normalize(
                item.get("question", "")
            ).split()
        )

        if not stored_words:
            continue

        common = question_words.intersection(stored_words)

        score = len(common) / max(
            len(question_words),
            1
        )

        if score > best_score:
            best_score = score
            best_match = item

    # Require reasonable similarity.
    if best_match and best_score >= 0.5:
        return best_match

    return None


def save_knowledge(question, answer, source):
    memories = _load()

    normalized_question = _normalize(question)

    for item in memories:
        if _normalize(
            item.get("question", "")
        ) == normalized_question:

            item["answer"] = answer
            item["source"] = source
            item["updated_at"] = datetime.utcnow().isoformat()

            _save(memories)
            return

    memories.append({
        "question": question,
        "answer": answer,
        "source": source,
        "created_at": datetime.utcnow().isoformat()
    })

    _save(memories)