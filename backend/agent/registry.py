from backend.agent.permissions import PermissionProfile
from backend.agent.skills import Skill, SkillRegistry


class ToolRegistry(SkillRegistry):
    """Model-facing tool registry with capability-aware discovery."""

    def available(self, permissions: PermissionProfile | None = None) -> list[dict]:
        profile = permissions or PermissionProfile.from_policy()
        return [
            item for item in self.list()
            if profile.can(item["capability"])
        ]


tools = ToolRegistry()
