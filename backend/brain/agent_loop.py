from dataclasses import dataclass
from typing import Callable


@dataclass
class AgentResult:
    goal: str
    completed: bool
    observations: list[str]
    error: str | None = None


def run_loop(goal: str, plan_steps: list[str], execute: Callable[[str], str]) -> AgentResult:
    """Small observe/act/verify loop boundary.

    Tool implementations remain outside the reasoning layer.
    """
    observations = []
    try:
        for step in plan_steps:
            observations.append(execute(step))
        return AgentResult(goal=goal, completed=True, observations=observations)
    except Exception as exc:
        return AgentResult(goal=goal, completed=False, observations=observations, error=str(exc))
