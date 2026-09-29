from dataclasses import dataclass
from typing import List

from backend.agent.permissions import PermissionProfile


@dataclass
class PlanStep:
    action: str
    reason: str
    requires_confirmation: bool = False
    capability: str = ""


@dataclass
class Plan:
    goal: str
    steps: List[PlanStep]


def build_plan(
    goal: str,
    steps: List[PlanStep],
    permissions: PermissionProfile | None = None,
) -> Plan:
    """Validate a plan against the current creator/host capability policy.

    Planning never executes actions. It only annotates steps that are currently
    outside the configured capability set.
    """
    if not goal.strip():
        raise ValueError("Plan goal cannot be empty")

    profile = permissions or PermissionProfile.from_policy()
    checked = []

    for step in steps:
        if step.capability and not profile.can(step.capability):
            checked.append(
                PlanStep(
                    action=step.action,
                    reason=step.reason,
                    requires_confirmation=True,
                    capability=step.capability,
                )
            )
        else:
            checked.append(step)

    return Plan(goal=goal.strip(), steps=checked)
