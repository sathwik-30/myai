"""In-process audit history for Medha development and diagnostics."""
from collections import deque
from threading import Lock
from typing import Any


class AuditStore:
    def __init__(self, max_events: int = 1000):
        self._events = deque(maxlen=max_events)
        self._lock = Lock()

    def record(self, event: str, **data: Any) -> dict:
        item = {"event": event, "data": data}
        with self._lock:
            self._events.append(item)
        return item

    def list(self, limit: int = 100) -> list[dict]:
        with self._lock:
            return list(self._events)[-max(1, min(int(limit), 1000)):]


audit_store = AuditStore()
