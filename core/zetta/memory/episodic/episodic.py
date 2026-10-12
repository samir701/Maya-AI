"""ZETTA Episodic Memory Management."""

from typing import Any, Dict, Optional
from core.zetta.memory.repository import MemoryRepository, get_memory_repository
from core.zetta.utils.logging import get_logger
from shared.types import Memory, MemorySource, MemoryType, TaskStatus

logger = get_logger("episodic_memory")


class EpisodicMemory:
    """Manages history of completed tasks, agent interactions, and system events."""

    def __init__(self, repository: Optional[MemoryRepository] = None) -> None:
        self.repo = repository or get_memory_repository()

    def record_task_outcome(
        self,
        task_id: str,
        task_name: str,
        status: TaskStatus,
        result: Optional[Any] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Memory]:
        """Record completed task outcome into episodic memory if deemed significant."""
        importance = 0.7 if status == TaskStatus.FAILED else 0.5
        content = f"Task '{task_name}' [{task_id}] ended with status '{status.value}'."
        if result:
            content += f" Result snippet: {str(result)[:100]}"
        if error_message:
            content += f" Error: {error_message}"

        memory = Memory(
            content=content,
            memory_type=MemoryType.EPISODIC,
            source=MemorySource.TASK,
            importance=importance,
            confidence=1.0,
            tags=["task_outcome", status.value.lower()],
            provenance={"task_id": task_id, "task_name": task_name, "status": status.value},
            metadata={"result_summary": str(result)[:200] if result else None, "error": error_message},
        )
        saved = self.repo.create(memory, actor="episodic_engine")
        logger.info(f"Recorded episodic memory for task '{task_id}' [{status.value}]")
        return saved
