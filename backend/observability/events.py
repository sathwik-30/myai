import json
import logging
import time
from typing import Any, Dict


logger = logging.getLogger("medha.audit")


def audit(event: str, user_id: int | None = None, **data: Any) -> None:
    """
    Structured audit event.

    Never pass secrets, passwords, tokens, or raw authorization headers.
    """
    safe = {
        "event": event,
        "user_id": user_id,
        "timestamp": time.time(),
        "data": data,
    }
    logger.info(json.dumps(safe, ensure_ascii=False, default=str))
