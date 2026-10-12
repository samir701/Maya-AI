"""ZETTA Task History Recorder."""

from typing import Dict, List, Optional
from shared.types.contracts import Task


class TaskHistory:
    """In-memory task history buffer."""

    def __init__(self) -> None:
        self._history: Dict[str, Task] = {}

    def record(self, task: Task) -> None:
        self._history[task.id] = task

    def get(self, task_id: str) -> Optional[Task]:
        return self._history.get(task_id)

    def list_all(self) -> List[Task]:
        return list(self._history.values())
