import os
import re
import sqlite3
from calendar import monthrange
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "medha_memory.db")

# Knowledge learned from the outside world expires after six months of inactivity.
KNOWLEDGE_RETENTION_MONTHS = 6

PERSONAL = "personal"
TEMPORARY = "temporary"
PERMANENT = "permanent"
KNOWLEDGE = "knowledge"
SCOPES = {PERSONAL, TEMPORARY, PERMANENT, KNOWLEDGE}

_STOP_WORDS = {
    "a", "an", "the", "is", "am", "are", "was", "were", "be", "been",
    "to", "of", "for", "in", "on", "at", "with", "and", "or", "but",
    "i", "me", "my", "you", "your", "we", "our", "it", "this", "that",
    "can", "could", "would", "should", "do", "does", "did", "please",
}


def _normalize(text: str) -> str:
    value = str(text or "").lower()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return " ".join(word for word in value.split() if word not in _STOP_WORDS)


def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15.0)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA journal_mode=WAL")
    return db


def _months_after(value: datetime, months: int) -> datetime:
    index = value.year * 12 + value.month - 1 + months
    year, month_zero = divmod(index, 12)
    month = month_zero + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _compact(text: str, limit: int = 900) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def _ensure_column(db, table: str, column: str, definition: str):
    columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _init():
    with _connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS personal_memories (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 5,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS temporary_memories (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                expires_at TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS permanent_memories (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 5,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_memories (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                text TEXT NOT NULL,
                answer TEXT NOT NULL,
                source TEXT NOT NULL,
                importance INTEGER NOT NULL DEFAULT 4,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                expires_at TEXT
            )
        """)

        # Upgrade databases created by the previous three-memory design.
        _ensure_column(db, "temporary_memories", "expires_at", "TEXT")
        _ensure_column(db, "knowledge_memories", "expires_at", "TEXT")

        db.execute("CREATE INDEX IF NOT EXISTS idx_personal_user ON personal_memories(user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_temp_user ON temporary_memories(user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_permanent_user ON permanent_memories(user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_user ON knowledge_memories(user_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_expiry ON knowledge_memories(expires_at)")
        db.commit()

    _migrate_legacy()


def _migrate_legacy():
    """Migrate the old generic memories table without destroying existing data."""
    with _connect() as db:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(memories)").fetchall()}
        if not columns or "text" not in columns:
            return

        rows = db.execute("SELECT * FROM memories").fetchall()
        if not rows:
            return

        for row in rows:
            user_id = row["user_id"]
            text = row["text"]
            answer = row["answer"]
            source = row["source"]
            importance = row["importance"]
            created_at = row["created_at"]
            updated_at = row["updated_at"] or created_at
            last_used_at = row["last_used_at"] or updated_at
            memory_type = row["memory_type"]

            if memory_type == PERSONAL and user_id is not None:
                _insert_if_missing(
                    db, "personal_memories", user_id, text, answer, source,
                    importance, created_at, updated_at, last_used_at
                )
            elif memory_type == PERMANENT and user_id is not None:
                _insert_if_missing(
                    db, "permanent_memories", user_id, text, answer, source,
                    importance, created_at, updated_at, last_used_at
                )
            elif memory_type == TEMPORARY and user_id is not None:
                _insert_if_missing(
                    db, "temporary_memories", user_id, text, answer, source,
                    importance, created_at, updated_at, last_used_at
                )
            else:
                # Old knowledge entries become learned knowledge and receive
                # the new six-month inactivity lifecycle.
                expiry = _months_after(
                    datetime.fromisoformat(last_used_at.replace("Z", "+00:00")),
                    KNOWLEDGE_RETENTION_MONTHS,
                ).isoformat()
                existing = db.execute(
                    "SELECT 1 FROM knowledge_memories WHERE user_id IS ? AND text=?",
                    (user_id, text),
                ).fetchone()
                if not existing:
                    db.execute(
                        """INSERT INTO knowledge_memories
                           (user_id,text,answer,source,importance,created_at,updated_at,last_used_at,expires_at)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (
                            user_id, text, answer, source, importance,
                            created_at, updated_at, last_used_at, expiry,
                        ),
                    )
        db.commit()


def _insert_if_missing(db, table, user_id, text, answer, source, importance, created_at, updated_at, last_used_at):
    exists = db.execute(
        f"SELECT 1 FROM {table} WHERE user_id=? AND text=?",
        (user_id, text),
    ).fetchone()
    if not exists:
        db.execute(
            f"""INSERT INTO {table}
                (user_id,text,answer,source,importance,created_at,updated_at,last_used_at)
                VALUES (?,?,?,?,?,?,?,?)""",
            (
                user_id, text, answer, source, importance,
                created_at, updated_at, last_used_at,
            ),
        )


def _cleanup():
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as db:
        # Temporary memory only expires when an explicit expiry was assigned.
        db.execute(
            "DELETE FROM temporary_memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (now,),
        )
        # Learned knowledge is the only memory type with automatic six-month
        # inactivity deletion.
        db.execute(
            "DELETE FROM knowledge_memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (now,),
        )
        db.commit()


def _table(scope: str) -> str:
    tables = {
        PERSONAL: "personal_memories",
        TEMPORARY: "temporary_memories",
        PERMANENT: "permanent_memories",
        KNOWLEDGE: "knowledge_memories",
    }
    if scope not in tables:
        raise ValueError("Invalid memory scope")
    return tables[scope]


def remember(
    scope: str,
    user_id: Optional[int],
    text: str,
    answer: str,
    source: str,
    importance: int = 3,
    expires_at: Optional[str] = None,
) -> bool:
    if scope not in SCOPES or not text or not answer:
        return False

    # Personal, temporary, and permanent memories are user-owned.
    if scope in {PERSONAL, TEMPORARY, PERMANENT} and user_id is None:
        return False

    _init()
    _cleanup()
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    importance = max(1, min(5, int(importance)))
    normalized = _normalize(text)
    if not normalized:
        return False

    table = _table(scope)

    if scope == KNOWLEDGE:
        # Learned knowledge always gets a six-month last-use expiry.
        expiry = expires_at or _months_after(now, KNOWLEDGE_RETENTION_MONTHS).isoformat()
    else:
        expiry = expires_at

    with _connect() as db:
        if user_id is None:
            existing = db.execute(
                f"SELECT id FROM {table} WHERE user_id IS NULL AND text=?",
                (normalized,),
            ).fetchone()
        else:
            existing = db.execute(
                f"SELECT id FROM {table} WHERE user_id=? AND text=?",
                (user_id, normalized),
            ).fetchone()

        if existing:
            db.execute(
                f"""UPDATE {table}
                    SET answer=?,source=?,importance=?,updated_at=?,last_used_at=?
                    {",expires_at=?" if table in {"knowledge_memories", "temporary_memories"} else ""}
                    WHERE id=?""",
                (
                    _compact(answer), source, importance, now_text, now_text,
                    *(([expiry]) if table in {"knowledge_memories", "temporary_memories"} else []),
                    existing["id"],
                ),
            )
        else:
            if table in {"knowledge_memories", "temporary_memories"}:
                db.execute(
                    f"""INSERT INTO {table}
                        (user_id,text,answer,source,importance,created_at,updated_at,last_used_at,expires_at)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        user_id, normalized, _compact(answer), source, importance,
                        now_text, now_text, now_text, expiry,
                    ),
                )
            else:
                db.execute(
                    f"""INSERT INTO {table}
                        (user_id,text,answer,source,importance,created_at,updated_at,last_used_at)
                        VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        user_id, normalized, _compact(answer), source, importance,
                        now_text, now_text, now_text,
                    ),
                )
        db.commit()
    return True


def search(
    scope: str,
    user_id: Optional[int],
    query: str,
    top_k: int = 3,
    min_score: float = 0.40,
) -> List[Dict[str, Any]]:
    if scope not in SCOPES or not str(query or "").strip():
        return []

    _init()
    _cleanup()
    normalized = _normalize(query)
    if not normalized:
        return []

    table = _table(scope)
    with _connect() as db:
        if scope == KNOWLEDGE:
            rows = db.execute(
                "SELECT * FROM knowledge_memories WHERE user_id IS NULL OR user_id=? "
                "ORDER BY importance DESC,id DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = db.execute(
                f"SELECT * FROM {table} WHERE user_id=? ORDER BY importance DESC,id DESC",
                (user_id,),
            ).fetchall()

    if not rows:
        return []

    docs = [row["text"] for row in rows]
    try:
        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            min_df=1,
            sublinear_tf=True,
        )
        matrix = vectorizer.fit_transform(docs + [normalized])
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
        item = dict(row)
        item["memory_scope"] = scope
        item["score"] = round(score, 4)
        results.append(item)

    if results:
        now = datetime.now(timezone.utc).isoformat()
        with _connect() as db:
            ids = [item["id"] for item in results]
            placeholders = ",".join("?" for _ in ids)
            db.execute(
                f"UPDATE {table} SET last_used_at=? WHERE id IN ({placeholders})",
                (now, *ids),
            )
            # Refresh the six-month window whenever learned knowledge is used.
            if scope == KNOWLEDGE:
                expiry = _months_after(
                    datetime.fromisoformat(now),
                    KNOWLEDGE_RETENTION_MONTHS,
                ).isoformat()
                db.execute(
                    f"UPDATE {table} SET expires_at=? WHERE id IN ({placeholders})",
                    (expiry, *ids),
                )
            db.commit()

    return results


def search_all(user_id: Optional[int], query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    combined = []
    # Personal and permanent memories have priority over temporary context
    # and automatically expiring learned knowledge.
    for scope in (PERSONAL, PERMANENT, TEMPORARY, KNOWLEDGE):
        combined.extend(search(scope, user_id, query, top_k=top_k, min_score=0.40))
    combined.sort(
        key=lambda item: (
            item["memory_scope"] in {PERSONAL, PERMANENT},
            item["score"],
            item.get("importance", 0),
        ),
        reverse=True,
    )
    return combined[:top_k]


def list_memories(scope: str, user_id: Optional[int], limit: int = 100) -> List[Dict[str, Any]]:
    if scope not in SCOPES:
        return []
    _init()
    _cleanup()
    table = _table(scope)
    with _connect() as db:
        if scope == KNOWLEDGE:
            rows = db.execute(
                f"""SELECT * FROM {table}
                    WHERE user_id IS NULL OR user_id=?
                    ORDER BY id DESC LIMIT ?""",
                (user_id, max(1, min(500, int(limit)))),
            ).fetchall()
        else:
            rows = db.execute(
                f"""SELECT * FROM {table}
                    WHERE user_id=?
                    ORDER BY id DESC LIMIT ?""",
                (user_id, max(1, min(500, int(limit)))),
            ).fetchall()
    return [dict(row, memory_scope=scope) for row in rows]


def delete_memory(scope: str, user_id: int, memory_id: int) -> bool:
    if scope not in SCOPES or scope == KNOWLEDGE:
        return False
    _init()
    table = _table(scope)
    with _connect() as db:
        cur = db.execute(
            f"DELETE FROM {table} WHERE id=? AND user_id=?",
            (int(memory_id), user_id),
        )
        db.commit()
    return cur.rowcount > 0


def cleanup_memory() -> None:
    """Remove expired temporary/knowledge records and refresh no stale state."""
    _init()
    _cleanup()


def counts(user_id: int) -> Dict[str, int]:
    _init()
    _cleanup()
    result = {}
    with _connect() as db:
        for scope in (PERSONAL, TEMPORARY, PERMANENT):
            table = _table(scope)
            result[scope] = int(
                db.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE user_id=?",
                    (user_id,),
                ).fetchone()[0]
            )
        result[KNOWLEDGE] = int(
            db.execute(
                "SELECT COUNT(*) FROM knowledge_memories WHERE user_id IS NULL OR user_id=?",
                (user_id,),
            ).fetchone()[0]
        )
    return result
