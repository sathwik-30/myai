from dataclasses import dataclass, field
from typing import Set

from backend.core.authority import Authority, authority_for, authority_policy


@dataclass
class PermissionProfile:
    """Runtime tool permissions derived from the creator/host policy."""

    allow_web: bool = True
    allow_files: bool = True
    allow_desktop: bool = True
    allow_network_actions: bool = True
    allow_destructive_actions: bool = False
    allow_terminal: bool = True
    allow_self_learning: bool = True
    allowed_apps: Set[str] = field(default_factory=set)

    def can(self, capability: str) -> bool:
        aliases = {
            "network": "network",
            "destructive": "destructive_actions",
        }
        key = aliases.get(capability, capability)
        explicit = {
            "web": self.allow_web,
            "files": self.allow_files,
            "desktop": self.allow_desktop,
            "network": self.allow_network_actions,
            "destructive_actions": self.allow_destructive_actions,
            "terminal": self.allow_terminal,
            "self_learning": self.allow_self_learning,
        }
        return explicit.get(key, authority_policy.allows(key))

    @classmethod
    def from_policy(cls) -> "PermissionProfile":
        return cls(
            allow_web=authority_policy.allows("web"),
            allow_files=authority_policy.allows("files"),
            allow_desktop=authority_policy.allows("desktop"),
            allow_network_actions=authority_policy.allows("network"),
            allow_destructive_actions=authority_policy.allows("destructive_actions"),
            allow_terminal=authority_policy.allows("terminal"),
            allow_self_learning=authority_policy.allows("self_learning"),
        )

    def set_by(self, actor: str, capability: str, enabled: bool) -> None:
        authority: Authority = authority_for(actor)
        authority_policy.set_permission(authority, capability, enabled)
        updated = PermissionProfile.from_policy()
        self.__dict__.update(updated.__dict__)
