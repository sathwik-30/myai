from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import List
from uuid import uuid4


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
        self._tasks: dict[str, Task] = {}
        self._lock = Lock()

    def create(self, goal: str, steps: List[str] | None = None) -> Task:
        if not goal.strip():
            raise ValueError("Task goal cannot be empty")
        task = Task(goal=goal.strip(), steps=list(steps or []), task_id=f"task-{uuid4().hex[:12]}")
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def update(self, task_id: str, status: str | None = None, current_step: int | None = None) -> Task:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(task_id)
            task = self._tasks[task_id]
            if status is not None:
                task.status = status
            if current_step is not None:
                task.current_step = max(0, min(int(current_step), len(task.steps)))
            return task

    def list(self) -> list[dict]:
        with self._lock:
            return [task.snapshot() for task in self._tasks.values()]


tasks = TaskManager()
