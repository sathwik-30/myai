from dataclasses import dataclass
from typing import Callable

@dataclass
class AgentResult:
    goal: str
    completed: bool
    observations: list[str]
    verified_steps: list[int]
    failed_step: int | None = None
    error: str | None = None

def run_loop(
    goal: str,
    plan_steps: list[str],
    execute: Callable[[str], str],
    verify: Callable[[str, str], bool] | None = None,
    max_retries: int = 1,
) -> AgentResult:
    """Execute a plan with per-step observation and optional verification.

    A step is not considered complete merely because its tool returned text.
    Verification can reject the observation, causing a bounded retry instead of
    blindly continuing through a broken multi-step task.
    """
    if not str(goal or "").strip():
        raise ValueError("Agent goal cannot be empty")
    observations: list[str] = []
    verified: list[int] = []
    max_retries = max(0, int(max_retries))

    for index, step in enumerate(plan_steps):
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                observation = str(execute(step))
                observations.append(observation)
                if verify is None or bool(verify(step, observation)):
                    verified.append(index)
                    break
                last_error = f"Verification failed for step {index + 1}"
            except Exception as exc:
                last_error = str(exc)
            if attempt == max_retries:
                return AgentResult(
                    goal=goal,
                    completed=False,
                    observations=observations,
                    verified_steps=verified,
                    failed_step=index,
                    error=last_error,
                )
    return AgentResult(
        goal=goal,
        completed=len(verified) == len(plan_steps),
        observations=observations,
        verified_steps=verified,
    )
