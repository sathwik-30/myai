"""Backward-compatible semantic-memory facade.

The four-layer SQLite system is the single runtime source of truth. This
module remains only so older imports do not create a second memory database.
"""
from backend.memory.layers import (
    KNOWLEDGE,
    PERMANENT,
    PERSONAL,
    TEMPORARY,
    counts,
    delete_memory as _delete_layer,
    list_memories as _list_layer,
    remember as _remember_layer,
    search as _search_layer,
)

MEMORY_RETENTION_MONTHS = 6

def remember(
    text,
    answer,
    memory_type="conversation",
    source="memory",
    metadata=None,
    importance=3,
    user_id=None,
):
    scope = {
        "personal": PERSONAL,
        "permanent": PERMANENT,
        "temporary": TEMPORARY,
        "knowledge": KNOWLEDGE,
        "conversation": TEMPORARY,
    }.get(memory_type, TEMPORARY)
    return _remember_layer(
        scope=scope,
        user_id=user_id,
        text=text,
        answer=answer,
        source=source,
        importance=int((metadata or {}).get("importance", importance)),
    )

def search(text, top_k=3, min_score=0.30, user_id=None):
    results = []
    for scope in (PERSONAL, PERMANENT, TEMPORARY, KNOWLEDGE):
        results.extend(_search_layer(scope, user_id, text, top_k=top_k, min_score=min_score))
    results.sort(key=lambda item: (item.get("score", 0.0), item.get("importance", 0)), reverse=True)
    return results[:top_k]

def list_memories(memory_type=None, limit=100, user_id=None):
    scope = {
        "personal": PERSONAL,
        "permanent": PERMANENT,
        "temporary": TEMPORARY,
        "knowledge": KNOWLEDGE,
    }.get(memory_type)
    if scope:
        return _list_layer(scope, user_id, limit)
    output = []
    for item_scope in (PERSONAL, PERMANENT, TEMPORARY, KNOWLEDGE):
        output.extend(_list_layer(item_scope, user_id, limit))
    return output[:max(1, min(500, int(limit)))]

def delete_memory(memory_id, user_id=None):
    for scope in (PERSONAL, TEMPORARY, PERMANENT):
        if _delete_layer(scope, user_id, memory_id):
            return True
    return False

def touch_memory(memory_id, user_id=None):
    # Layer search updates last_used_at, so touching is implemented by looking
    # up the memory through each applicable scope.
    for scope in (PERSONAL, TEMPORARY, PERMANENT, KNOWLEDGE):
        results = _search_layer(scope, user_id, str(memory_id), top_k=1, min_score=1.0)
        if results:
            return True
    return False

def count():
    return sum(counts(None).values())

def recent(limit=10):
    output = []
    for scope in (PERSONAL, PERMANENT, TEMPORARY, KNOWLEDGE):
        output.extend(_list_layer(scope, None, limit))
    return output[:max(1, int(limit))]

def sync_memory_file():
    return None
