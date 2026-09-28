import os
import threading


_lock = threading.Lock()
_enabled = os.getenv("MEDHA_KILL_SWITCH", "false").strip().lower() == "true"


def enabled() -> bool:
    with _lock:
        return _enabled


def set_enabled(value: bool) -> None:
    global _enabled
    with _lock:
        _enabled = bool(value)


def require_enabled() -> None:
    if enabled():
        raise RuntimeError("Medha emergency stop is enabled")
