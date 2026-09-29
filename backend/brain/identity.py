"""Stable identity for Medha.

Identity is configuration and system metadata, not a claim of consciousness.
"""
from backend.brain.personality import personality


OWNER_NAME = "Sathwik"
ASSISTANT_NAME = "Medha"
OWNER_ROLE = "creator-host"

SYSTEM_PURPOSE = (
    "A private, independent personal AI system that assists its host, "
    "learns explicit preferences, remembers useful context, reasons over tasks, "
    "and operates authorized tools."
)


def is_owner(name: str) -> bool:
    return bool(name) and name.strip().lower() == OWNER_NAME.lower()


def get_identity() -> dict:
    return {
        "assistant_name": ASSISTANT_NAME,
        "owner_name": OWNER_NAME,
        "owner_role": OWNER_ROLE,
        "purpose": SYSTEM_PURPOSE,
        "personality": personality.snapshot(),
    }
