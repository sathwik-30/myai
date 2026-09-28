from dataclasses import dataclass, field
from typing import Set


@dataclass
class PermissionProfile:
    """Least-privilege permissions for agent actions."""

    allow_web: bool = True
    allow_files: bool = True
    allow_desktop: bool = False
    allow_network_actions: bool = False
    allow_destructive_actions: bool = False
    allowed_apps: Set[str] = field(default_factory=set)

    def can(self, capability: str) -> bool:
        return {
            "web": self.allow_web,
            "files": self.allow_files,
            "desktop": self.allow_desktop,
            "network": self.allow_network_actions,
            "destructive": self.allow_destructive_actions,
        }.get(capability, False)
