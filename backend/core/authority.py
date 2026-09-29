"""Creator/host authority model for Medha.

Privileged authority is resolved from authenticated principal IDs configured
outside model-generated text. The assistant cannot grant itself authority.
"""

import os
from dataclasses import dataclass, field


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
    permissions: dict[str, bool] = field(default_factory=lambda: {
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
        return actor in (CREATOR, HOST)

    def allows(self, capability: str) -> bool:
        return bool(self.permissions.get(capability, False))

    def set_permission(self, actor: Authority, capability: str, enabled: bool) -> None:
        if not self.can_configure(actor):
            raise PermissionError("Only configured creator/host authority may change permissions.")
        capability = capability.strip()
        if not capability:
            raise ValueError("Capability cannot be empty.")
        self.permissions[capability] = bool(enabled)

    def snapshot(self) -> dict:
        return {
            "creator": self.creator.__dict__.copy(),
            "host": self.host.__dict__.copy(),
            "permissions": dict(self.permissions),
        }


authority_policy = AuthorityPolicy()


def configured_host_id() -> str | None:
    return os.getenv("MEDHA_HOST_USER_ID", "").strip() or None


def configured_creator_id() -> str | None:
    return os.getenv("MEDHA_CREATOR_USER_ID", "").strip() or None


def authority_for_user(user: dict) -> Authority:
    subject = str(user.get("sub", "")).strip()
    role = str(user.get("role", "")).strip().lower()

    # Explicit environment configuration has highest priority.
    if configured_creator_id() and subject == configured_creator_id():
        return CREATOR
    if configured_host_id() and subject == configured_host_id():
        return HOST

    # The bootstrap account can operate as creator without requiring a
    # manually copied numeric user ID into the environment.
    if role in {"creator", "admin"}:
        return CREATOR
    if role == "host":
        return HOST

    return MEDHA
