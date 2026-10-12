"""ZETTA Task Queue Abstraction."""

from collections import deque
from typing import Optional
from shared.types.contracts import Task
from core.zetta.utils.errors.exceptions import TaskError


class TaskQueue:
    """In-memory task queue supporting FIFO scheduling."""

    def __init__(self) -> None:
        self._queue: deque[Task] = deque()

    def enqueue(self, task: Task) -> None:
        self._queue.append(task)

    def dequeue(self) -> Optional[Task]:
        if not self._queue:
            return None
        return self._queue.popleft()

    def peek(self) -> Optional[Task]:
        if not self._queue:
            return None
        return self._queue[0]

    def __len__(self) -> int:
        return len(self._queue)
