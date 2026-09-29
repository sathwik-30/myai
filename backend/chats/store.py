import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "data", "medha_memory.db")

def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15.0)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA journal_mode=WAL")
    return db

def init_chat_tables():
    with _connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL)""")
        # Migrate databases created before the role column existed.
        columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        if "role" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        db.execute("""CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, title TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, role TEXT NOT NULL,
            message TEXT NOT NULL, source TEXT, latency_ms INTEGER, created_at TEXT NOT NULL)""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_chats_user ON chats(user_id, updated_at DESC)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat ON chat_messages(chat_id, id)")
        db.commit()

def _now():
    return datetime.now(timezone.utc).isoformat()

def create_user(username, password_hash, role="user", recovery_code_hash=None):
    init_chat_tables()
    with _connect() as db:
        try:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()}
            if "recovery_code_hash" not in columns:
                db.execute("ALTER TABLE users ADD COLUMN recovery_code_hash TEXT")
            cur = db.execute(
                "INSERT INTO users(username,password_hash,role,recovery_code_hash,created_at) VALUES(?,?,?,?,?)",
                (username, password_hash, role, recovery_code_hash, _now()),
            )
            db.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

def update_password(user_id, password_hash, recovery_code_hash=None):
    init_chat_tables()
    with _connect() as db:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        if "recovery_code_hash" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN recovery_code_hash TEXT")
        if recovery_code_hash is None:
            cur = db.execute(
                "UPDATE users SET password_hash=? WHERE id=?",
                (password_hash, int(user_id)),
            )
        else:
            cur = db.execute(
                "UPDATE users SET password_hash=?, recovery_code_hash=? WHERE id=?",
                (password_hash, recovery_code_hash, int(user_id)),
            )
        db.commit()
        return cur.rowcount > 0

def get_user(username):
    init_chat_tables()
    with _connect() as db:
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id):
    init_chat_tables()
    with _connect() as db:
        row = db.execute("SELECT * FROM users WHERE id=?", (int(user_id),)).fetchone()
        return dict(row) if row else None

def has_admin():
    init_chat_tables()
    with _connect() as db:
        return db.execute("SELECT 1 FROM users WHERE role IN ('admin','creator','host') LIMIT 1").fetchone() is not None

def create_chat(user_id, title="New chat"):
    init_chat_tables()
    now = _now()
    with _connect() as db:
        cur = db.execute("INSERT INTO chats(user_id,title,created_at,updated_at) VALUES(?,?,?,?)",
                         (user_id, title[:120] or "New chat", now, now))
        db.commit()
        return cur.lastrowid

def list_chats(user_id):
    init_chat_tables()
    with _connect() as db:
        rows = db.execute("SELECT id,title,created_at,updated_at FROM chats WHERE user_id=? ORDER BY updated_at DESC",
                          (user_id,)).fetchall()
        return [dict(row) for row in rows]

def get_chat(user_id, chat_id):
    init_chat_tables()
    with _connect() as db:
        row = db.execute("SELECT * FROM chats WHERE id=? AND user_id=?", (chat_id, user_id)).fetchone()
        return dict(row) if row else None

def add_message(user_id, chat_id, role, message, source="", latency_ms=0):
    init_chat_tables()
    now = _now()
    with _connect() as db:
        owned = db.execute("SELECT id FROM chats WHERE id=? AND user_id=?", (chat_id, user_id)).fetchone()
        if not owned:
            return False
        db.execute("INSERT INTO chat_messages(chat_id,role,message,source,latency_ms,created_at) VALUES(?,?,?,?,?,?)",
                   (chat_id, role, message, source, latency_ms, now))
        if role == "user":
            db.execute(
                """UPDATE chats SET updated_at=?, title=CASE
                   WHEN title='New chat' THEN substr(?,1,80) ELSE title END WHERE id=?""",
                (now, message, chat_id),
            )
        else:
            db.execute("UPDATE chats SET updated_at=? WHERE id=?", (now, chat_id))
        db.commit()
        return True

def list_messages(user_id, chat_id):
    if not get_chat(user_id, chat_id):
        return None
    with _connect() as db:
        rows = db.execute("SELECT id,role,message,source,latency_ms,created_at FROM chat_messages WHERE chat_id=? ORDER BY id",
                          (chat_id,)).fetchall()
        return [dict(row) for row in rows]

def rename_chat(user_id, chat_id, title):
    with _connect() as db:
        cur = db.execute("UPDATE chats SET title=? WHERE id=? AND user_id=?",
                         (title[:120] or "New chat", chat_id, user_id))
        db.commit()
        return cur.rowcount > 0

def delete_chat(user_id, chat_id):
    with _connect() as db:
        owned = db.execute("SELECT id FROM chats WHERE id=? AND user_id=?", (chat_id, user_id)).fetchone()
        if not owned:
            return False
        db.execute("DELETE FROM chat_messages WHERE chat_id=?", (chat_id,))
        db.execute("DELETE FROM chats WHERE id=? AND user_id=?", (chat_id, user_id))
        db.commit()
        return True
