import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "medha_memory.db")
LEGACY_JSON_PATH = os.path.join(DATA_DIR, "semantic_memory.json")

DEFAULT_MEMORIES = [
    ("Hi", "Hi Sathwik. I'm here. How are you?", "casual"),
    ("Hello", "Hello Sathwik. What are we working on?", "casual"),
    ("Hey Medha", "Hey Sathwik. I'm here.", "casual"),
    ("Good morning", "Good morning, Sathwik. What are we working on?", "casual"),
    ("How are you?", "I'm functioning normally and ready to talk with you.", "casual"),
    ("I am fine, what about you?", "I'm functioning normally too. I'm here and ready to help you, Sathwik.", "casual"),
    ("wt abt u", "I'm functioning normally too. I'm here and ready to help you, Sathwik.", "casual"),
    ("What are you doing?", "I'm here, processing what you need and ready to help.", "casual"),
    ("Thanks", "You're welcome.", "casual"),
    ("Thank you", "You're welcome.", "casual"),
    ("Who are you?", "I'm Medha, your personal AI assistant.", "identity"),
    ("What is your name?", "My name is Medha.", "identity"),
    ("What can you do?", "I can learn useful information, retrieve memories, research technical questions, and use connected tools.", "capability"),
]

_STOP_WORDS = {
    "a", "an", "the", "is", "am", "are", "was", "were", "be", "been",
    "to", "of", "for", "in", "on", "at", "with", "and", "or", "but",
    "i", "me", "my", "you", "your", "we", "our", "it", "this", "that",
    "can", "could", "would", "should", "do", "does", "did", "please",
}

def _normalize(text: str) -> str:
    value = str(text or "").lower()
    # Keep Unicode letters so Telugu and other scripts are not discarded.
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    words = [word for word in value.split() if word not in _STOP_WORDS]
    return " ".join(words)

def _connect() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=15.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=15000")
    connection.execute("PRAGMA journal_mode=WAL")
    return connection

def _init() -> None:
    with _connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                text TEXT NOT NULL,
                answer TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                source TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        columns = {row["name"] for row in db.execute("PRAGMA table_info(memories)").fetchall()}
        if "user_id" not in columns:
            db.execute("ALTER TABLE memories ADD COLUMN user_id INTEGER")
        db.execute("CREATE INDEX IF NOT EXISTS idx_memory_user ON memories(user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_memory_source ON memories(source)")
        db.commit()

def _compact(text: str, limit: int = 900) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= limit:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept: List[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and sentence not in kept:
            kept.append(sentence)
        if len(" ".join(kept)) >= limit:
            break
    result = " ".join(kept)
    return result[:limit].rsplit(" ", 1)[0] + "..." if len(result) > limit else result

def _migrate_legacy() -> None:
    _init()
    if not os.path.exists(LEGACY_JSON_PATH):
        return
    try:
        with open(LEGACY_JSON_PATH, "r", encoding="utf-8") as file:
            legacy = json.load(file)
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(legacy, list):
        return
    for item in legacy:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        answer = item.get("answer")
        if text and answer:
            remember(
                text,
                answer,
                memory_type=item.get("memory_type", "knowledge"),
                source=item.get("source", "legacy"),
                importance=int((item.get("metadata") or {}).get("importance", 3)),
            )
    try:
        os.remove(LEGACY_JSON_PATH)
    except OSError:
        pass

def _ensure_defaults() -> None:
    _init()
    with _connect() as db:
        for text, answer, memory_type in DEFAULT_MEMORIES:
            normalized = _normalize(text)
            exists = db.execute(
                "SELECT 1 FROM memories WHERE user_id IS NULL AND text = ? LIMIT 1",
                (normalized,),
            ).fetchone()
            if not exists:
                db.execute(
                    """INSERT INTO memories
                       (user_id, text, answer, memory_type, source, importance, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        None,
                        normalized,
                        _compact(answer),
                        memory_type,
                        "built_in_memory",
                        5,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
        db.commit()

def _prepare() -> None:
    _init()
    _migrate_legacy()
    _ensure_defaults()

def remember(
    text: str,
    answer: str,
    memory_type: str = "conversation",
    source: str = "memory",
    metadata: Optional[Dict[str, Any]] = None,
    importance: int = 3,
    user_id: int | None = None,
) -> None:
    if not text or not answer:
        return
    _prepare()
    normalized = _normalize(text)
    if not normalized:
        return
    compact_answer = _compact(answer)
    importance = max(1, min(5, int((metadata or {}).get("importance", importance))))
    with _connect() as db:
        existing = db.execute(
            """SELECT id FROM memories
               WHERE text = ? AND (user_id = ? OR (user_id IS NULL AND ? IS NULL))
               LIMIT 1""",
            (normalized, user_id, user_id),
        ).fetchone()
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            db.execute(
                """UPDATE memories
                   SET answer=?, memory_type=?, source=?, importance=?, updated_at=?
                   WHERE id=?""",
                (compact_answer, memory_type, source, importance, now, existing["id"]),
            )
        else:
            db.execute(
                """INSERT INTO memories
                   (user_id, text, answer, memory_type, source, importance, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, normalized, compact_answer, memory_type, source, importance, now),
            )
        db.commit()
    sync_memory_file()

def search(
    text: str,
    top_k: int = 3,
    min_score: float = 0.30,
    user_id: int | None = None,
) -> List[Dict[str, Any]]:
    if not str(text or "").strip():
        return []
    _prepare()
    query = _normalize(text)
    if not query:
        return []
    with _connect() as db:
        rows = db.execute(
            """SELECT * FROM memories
               WHERE user_id IS NULL OR user_id = ?
               ORDER BY importance DESC, id DESC""",
            (user_id,),
        ).fetchall()
    if not rows:
        return []
    documents = [row["text"] for row in rows]
    try:
        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            min_df=1,
            sublinear_tf=True,
        )
        matrix = vectorizer.fit_transform(documents + [query])
        scores = cosine_similarity(matrix[-1], matrix[:-1])[0]
    except ValueError:
        return []
    ranked = sorted(
        zip(rows, scores),
        key=lambda pair: (float(pair[1]), pair[0]["importance"]),
        reverse=True,
    )
    results = []
    for row, score in ranked[:top_k]:
        score = float(score)
        if score < min_score:
            continue
        result = dict(row)
        result["score"] = round(score, 4)
        results.append(result)
    return results

def list_memories(
    memory_type: Optional[str] = None,
    limit: int = 100,
    user_id: int | None = None,
) -> List[Dict[str, Any]]:
    _prepare()
    limit = max(1, min(500, int(limit)))
    with _connect() as db:
        if memory_type:
            rows = db.execute(
                """SELECT id, user_id, text, answer, memory_type, source,
                          importance, created_at, updated_at
                   FROM memories
                   WHERE memory_type = ? AND (user_id IS NULL OR user_id = ?)
                   ORDER BY importance DESC, id DESC
                   LIMIT ?""",
                (memory_type, user_id, limit),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT id, user_id, text, answer, memory_type, source,
                          importance, created_at, updated_at
                   FROM memories
                   WHERE user_id IS NULL OR user_id = ?
                   ORDER BY importance DESC, id DESC
                   LIMIT ?""",
                (user_id, limit),
            ).fetchall()
    return [dict(row) for row in rows]

def delete_memory(memory_id: int, user_id: int | None = None) -> bool:
    _prepare()
    with _connect() as db:
        cursor = db.execute(
            "DELETE FROM memories WHERE id = ? AND (user_id IS NULL OR user_id = ?)",
            (int(memory_id), user_id),
        )
        db.commit()
    sync_memory_file()
    return cursor.rowcount > 0

def sync_memory_file() -> None:
    _init()
    memory_file = os.path.join(os.path.dirname(DATA_DIR), "MEMORY.md")
    with _connect() as db:
        rows = db.execute(
            """SELECT id, user_id, memory_type, importance, text, answer
               FROM memories
               ORDER BY importance DESC, id DESC"""
        ).fetchall()
    lines = [
        "# MEDHA MEMORY",
        "",
        "Human-readable mirror of persistent memory.",
        "SQLite database remains the runtime source of truth.",
        "",
    ]
    for row in rows:
        owner = "global" if row["user_id"] is None else f"user={row['user_id']}"
        lines.append(
            f"- [{row['id']}] {owner} | {row['memory_type']} | importance={row['importance']} | "
            f"{row['text']} -> {row['answer']}"
        )
    temp_file = memory_file + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")
    os.replace(temp_file, memory_file)

def count() -> int:
    _prepare()
    with _connect() as db:
        return int(db.execute("SELECT COUNT(*) FROM memories").fetchone()[0])

def recent(limit: int = 10) -> List[Dict[str, Any]]:
    _prepare()
    with _connect() as db:
        rows = db.execute(
            "SELECT * FROM memories ORDER BY id DESC LIMIT ?",
            (max(1, limit),),
        ).fetchall()
    return [dict(row) for row in rows]
