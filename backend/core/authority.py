"""Creator/host authority model for Medha.

Identity for privileged control is bound to explicit configuration rather than
assuming that every authenticated account is the host.
"""
import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class Authority:
    principal: str
    role: str
    priority: int


CREATOR = Authority("creator", "creator", 100)
HOST = Authority("host", "host", 90)
MEDHA = Authority("medha", "assistant", 10)


@dataclass
class AuthorityPolicy:
    creator: Authority = CREATOR
    host: Authority = HOST
    permissions: Dict[str, bool] = field(default_factory=lambda: {
        "web": True,
        "files": True,
        "desktop": True,
        "network": True,
        "terminal": True,
        "self_learning": True,
        "autonomous_planning": True,
        "destructive_actions": False,
        "credential_access": False,
        "external_messages": False,
    })

    def can_configure(self, actor: Authority) -> bool:
        return actor.priority >= self.host.priority

    def allows(self, capability: str) -> bool:
        return bool(self.permissions.get(capability, False))

    def set_permission(self, actor: Authority, capability: str, enabled: bool) -> None:
        if not self.can_configure(actor):
            raise PermissionError("Only creator/host authority may change Medha permissions.")
        if not capability.strip():
            raise ValueError("Capability cannot be empty.")
        self.permissions[capability.strip()] = bool(enabled)

    def snapshot(self) -> dict:
        return {
            "creator": self.creator.__dict__.copy(),
            "host": self.host.__dict__.copy(),
            "permissions": dict(self.permissions),
        }


authority_policy = AuthorityPolicy()


def configured_host_id() -> str | None:
    value = os.getenv("MEDHA_HOST_USER_ID", "").strip()
    return value or None


def configured_creator_id() -> str | None:
    value = os.getenv("MEDHA_CREATOR_USER_ID", "").strip()
    return value or None


def authority_for_user(user: dict) -> Authority:
    """Resolve authority from configured principal IDs, never display names."""
    subject = str(user.get("sub", "")).strip()
    if configured_creator_id() and subject == configured_creator_id():
        return CREATOR
    if configured_host_id() and subject == configured_host_id():
        return HOST
    return MEDHA
