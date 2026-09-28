from dataclasses import dataclass
from typing import List


@dataclass
class PlanStep:
    action: str
    reason: str
    requires_confirmation: bool = False


@dataclass
class Plan:
    goal: str
    steps: List[PlanStep]


def build_plan(goal: str, steps: List[PlanStep]) -> Plan:
    """Represent an agent plan without executing any action."""
    if not goal.strip():
        raise ValueError("Plan goal cannot be empty")
    return Plan(goal=goal.strip(), steps=steps)
