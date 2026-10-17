"""Creator-only learning queue and knowledge review for Medha."""

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.auth.dependencies import current_user
from backend.brain.intent import understand
from backend.chats.store import DB_PATH, init_chat_tables
from backend.core.authority import authority_for_user, CREATOR, HOST
from backend.memory.layers import KNOWLEDGE, list_memories
from backend.memory.manager import MemoryManager
from backend.observability.audit_store import audit_store

router = APIRouter(prefix="/creator", tags=["creator"])


def _connect():
    init_chat_tables()
    db = sqlite3.connect(DB_PATH, timeout=15.0)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""
        CREATE TABLE IF NOT EXISTS creator_learning_queue (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            kind TEXT NOT NULL,
            intent TEXT NOT NULL DEFAULT 'general',
            response TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            owner_answer TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_creator_queue_user_status ON creator_learning_queue(user_id,status,kind)")
    db.commit()
    return db


def _require_creator(user):
    actor = authority_for_user(user)
    if actor not in (CREATOR, HOST):
        raise HTTPException(status_code=403, detail="Creator/host authority required")
    return int(user["sub"])


def record_learning_item(question: str, kind: str, response: str = "", source: str = "", user_id: int | None = None):
    """Persist an unanswered owner question or failed answer for creator review."""
    question = " ".join(str(question or "").split())[:8000]
    if not question or kind not in {"owner_question", "failed_response"}:
        return False
    now = datetime.now(timezone.utc).isoformat()
    intent = str(understand(question).get("intent", "general"))
    owner_id = int(user_id) if user_id is not None else None
    if owner_id is None:
        return False
    with _connect() as db:
        existing = db.execute(
            """SELECT id FROM creator_learning_queue
               WHERE user_id=? AND question=? AND kind=? AND status='pending'""",
            (owner_id, question, kind),
        ).fetchone()
        if existing:
            db.execute(
                """UPDATE creator_learning_queue SET response=?,source=?,updated_at=? WHERE id=?""",
                (str(response or "")[:8000], str(source or "")[:100], now, existing["id"]),
            )
        else:
            db.execute(
                """INSERT INTO creator_learning_queue
                   (user_id,question,kind,intent,response,source,status,owner_answer,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,'pending','',?,?)""",
                (owner_id, question, kind, intent, str(response or "")[:8000],
                 str(source or "")[:100], now, now),
            )
        db.commit()
    return True


class OwnerAnswer(BaseModel):
    answer: str = Field(..., min_length=1, max_length=8000)


class QueueStatus(BaseModel):
    status: str = Field(..., pattern="^(dismissed|pending)$")


@router.get("/overview")
def creator_overview(user=Depends(current_user)):
    user_id = _require_creator(user)
    with _connect() as db:
        rows = db.execute(
            """SELECT kind,status,COUNT(*) AS count FROM creator_learning_queue
               WHERE user_id=? GROUP BY kind,status""",
            (user_id,),
        ).fetchall()
    counts = {(row["kind"], row["status"]): row["count"] for row in rows}
    memories = list_memories(KNOWLEDGE, user_id, 500)
    return {
        "pending_owner_questions": counts.get(("owner_question", "pending"), 0),
        "failed_responses": counts.get(("failed_response", "pending"), 0),
        "resolved_items": sum(row["count"] for row in rows if row["status"] == "answered"),
        "dismissed_items": counts.get(("owner_question", "dismissed"), 0) + counts.get(("failed_response", "dismissed"), 0),
        "learned_knowledge": len(memories),
        "recent_activity": audit_store.list(20),
    }


@router.get("/learning-queue")
def get_learning_queue(
    kind: str | None = Query(default=None, pattern="^(owner_question|failed_response)$"),
    status: str = Query(default="pending", pattern="^(pending|answered|dismissed|all)$"),
    limit: int = Query(default=100, ge=1, le=500),
    user=Depends(current_user),
):
    user_id = _require_creator(user)
    clauses = ["user_id=?"]
    params: list[object] = [user_id]
    if kind:
        clauses.append("kind=?")
        params.append(kind)
    if status != "all":
        clauses.append("status=?")
        params.append(status)
    params.append(limit)
    with _connect() as db:
        rows = db.execute(
            f"""SELECT id,question,kind,intent,response,source,status,owner_answer,created_at,updated_at
                FROM creator_learning_queue WHERE {' AND '.join(clauses)}
                ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, updated_at DESC LIMIT ?""",
            params,
        ).fetchall()
    return {"items": [dict(row) for row in rows], "count": len(rows)}


@router.post("/learning-queue/{item_id}/answer")
def answer_learning_item(item_id: int, request: OwnerAnswer, user=Depends(current_user)):
    user_id = _require_creator(user)
    answer = request.answer.strip()
    if not answer:
        raise HTTPException(status_code=400, detail="Answer cannot be blank")
    with _connect() as db:
        item = db.execute(
            "SELECT * FROM creator_learning_queue WHERE id=? AND user_id=?",
            (item_id, user_id),
        ).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Learning item not found")
        manager = MemoryManager(user_id=user_id)
        intent = item["intent"]
        if intent in {"technical", "knowledge", "research"}:
            manager.learn_knowledge(
                item["question"], answer, source="creator_answer", importance=5
            )
        else:
            manager.learn_personal(item["question"], answer, importance=5)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            """UPDATE creator_learning_queue SET status='answered',owner_answer=?,updated_at=?
               WHERE id=? AND user_id=?""",
            (answer, now, item_id, user_id),
        )
        db.commit()
    audit_store.record("creator.learning_answer", user_id=user_id, item_id=item_id, intent=intent)
    return {"saved": True, "status": "answered", "message": "Answer saved to Medha's reusable memory."}


@router.post("/learning-queue/{item_id}/dismiss")
def dismiss_learning_item(item_id: int, user=Depends(current_user)):
    user_id = _require_creator(user)
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as db:
        cur = db.execute(
            """UPDATE creator_learning_queue SET status='dismissed',updated_at=?
               WHERE id=? AND user_id=? AND status='pending'""",
            (now, item_id, user_id),
        )
        db.commit()
    if not cur.rowcount:
        raise HTTPException(status_code=404, detail="Pending learning item not found")
    return {"dismissed": True}


@router.get("/knowledge")
def creator_knowledge(limit: int = Query(default=100, ge=1, le=500), user=Depends(current_user)):
    user_id = _require_creator(user)
    memories = list_memories(KNOWLEDGE, user_id, limit)
    return {"items": memories, "count": len(memories)}
