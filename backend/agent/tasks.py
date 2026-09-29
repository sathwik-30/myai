from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class Task:
    goal: str
    status: str = "pending"
    steps: List[str] = field(default_factory=list)
    current_step: int = 0
    task_id: str = ""

    def snapshot(self) -> dict:
        data = asdict(self)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        return data


class TaskManager:
    def __init__(self):
        self._tasks = {}

    def create(self, goal: str, steps: List[str] | None = None) -> Task:
        if not goal.strip():
            raise ValueError("Task goal cannot be empty")
        task_id = f"task-{len(self._tasks) + 1}"
        task = Task(goal=goal.strip(), steps=list(steps or []), task_id=task_id)
        self._tasks[task_id] = task
        return task

    def update(self, task_id: str, status: str | None = None, current_step: int | None = None) -> Task:
        task = self._tasks[task_id]
        if status is not None:
            task.status = status
        if current_step is not None:
            task.current_step = max(0, int(current_step))
        return task

    def list(self) -> list[dict]:
        return [task.snapshot() for task in self._tasks.values()]


tasks = TaskManager()
