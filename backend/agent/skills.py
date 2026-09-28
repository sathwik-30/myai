from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    capability: str
    handler: Optional[Callable] = None


class SkillRegistry:
    """Central registry for future model-callable skills and tools."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        if not skill.name or not skill.capability:
            raise ValueError("A skill requires a name and capability")
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def list(self):
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "capability": skill.capability,
            }
            for skill in self._skills.values()
        ]


registry = SkillRegistry()
