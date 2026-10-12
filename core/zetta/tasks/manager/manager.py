"""ZETTA Task Manager."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from core.zetta.events import Event, get_event_bus
from core.zetta.tasks.history.history import TaskHistory
from core.zetta.tasks.queue.queue import TaskQueue
from core.zetta.utils.errors.exceptions import TaskError
from core.zetta.utils.logging import get_logger
from shared.types.contracts import ErrorInfo, Task
from shared.types.enums import EventType, TaskStatus

logger = get_logger("task_manager")


class TaskManager:
    """Manages task lifecycle transitions and queue orchestration."""

    def __init__(self) -> None:
        self.queue = TaskQueue()
        self.history = TaskHistory()
        self._active_tasks: Dict[str, Task] = {}

    def create_task(self, name: str, description: str = "", metadata: Optional[Dict[str, Any]] = None) -> Task:
        """Create a new task in CREATED status."""
        task = Task(name=name, description=description, metadata=metadata or {})
        self.history.record(task)
        logger.info(f"Created Task '{task.name}' [ID: {task.id}]")

        get_event_bus().publish(
            Event(
                event_type=EventType.TASK_CREATED,
                payload={"task_id": task.id, "name": task.name},
                task_id=task.id,
            )
        )
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task by ID."""
        return self.history.get(task_id)

    def list_tasks(self) -> List[Task]:
        """List all recorded tasks."""
        return self.history.list_all()

    def queue_task(self, task_id: str) -> Task:
        """Move task to QUEUED status."""
        task = self.history.get(task_id)
        if not task:
            raise TaskError(f"Task '{task_id}' not found.")
        task.status = TaskStatus.QUEUED
        self.queue.enqueue(task)
        logger.info(f"Queued Task '{task.name}' [ID: {task.id}]")
        return task

    def start_task(self, task_id: str) -> Task:
        """Transition task to RUNNING status."""
        task = self.history.get(task_id)
        if not task:
            raise TaskError(f"Task '{task_id}' not found.")
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc).isoformat()
        self._active_tasks[task.id] = task

        get_event_bus().publish(
            Event(
                event_type=EventType.TASK_STARTED,
                payload={"task_id": task.id},
                task_id=task.id,
            )
        )
        logger.info(f"Started Task '{task.name}' [ID: {task.id}]")
        return task

    def complete_task(self, task_id: str, result: Optional[Any] = None) -> Task:
        """Transition task to COMPLETED status."""
        task = self.history.get(task_id)
        if not task:
            raise TaskError(f"Task '{task_id}' not found.")
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc).isoformat()
        task.result = result
        self._active_tasks.pop(task.id, None)

        get_event_bus().publish(
            Event(
                event_type=EventType.TASK_COMPLETED,
                payload={"task_id": task.id, "result": str(result)},
                task_id=task.id,
            )
        )
        logger.info(f"Completed Task '{task.name}' [ID: {task.id}]")
        return task

    def fail_task(self, task_id: str, error_message: str) -> Task:
        """Transition task to FAILED status."""
        task = self.history.get(task_id)
        if not task:
            raise TaskError(f"Task '{task_id}' not found.")
        task.status = TaskStatus.FAILED
        task.completed_at = datetime.now(timezone.utc).isoformat()
        task.error = ErrorInfo(code="TaskFailed", message=error_message)
        self._active_tasks.pop(task.id, None)

        get_event_bus().publish(
            Event(
                event_type=EventType.TASK_FAILED,
                payload={"task_id": task.id, "error": error_message},
                task_id=task.id,
            )
        )
        logger.error(f"Failed Task '{task.name}' [ID: {task.id}]: {error_message}")
        return task

    def cancel_task(self, task_id: str) -> Task:
        """Transition task to CANCELLED status."""
        task = self.history.get(task_id)
        if not task:
            raise TaskError(f"Task '{task_id}' not found.")
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now(timezone.utc).isoformat()
        self._active_tasks.pop(task.id, None)

        get_event_bus().publish(
            Event(
                event_type=EventType.TASK_CANCELLED,
                payload={"task_id": task.id},
                task_id=task.id,
            )
        )
        logger.warning(f"Cancelled Task '{task.name}' [ID: {task.id}]")
        return task


_task_manager_instance: TaskManager = TaskManager()


def get_task_manager() -> TaskManager:
    return _task_manager_instance
