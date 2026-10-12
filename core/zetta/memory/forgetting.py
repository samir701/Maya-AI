"""ZETTA Explicit Forgetting & Deletion Engine."""

from typing import List, Optional
from core.zetta.events import Event, EventBus, get_event_bus
from core.zetta.memory.repository import MemoryRepository, get_memory_repository
from core.zetta.utils.logging import get_logger
from shared.types import EventType, MemoryType

logger = get_logger("memory_forgetting")


class ForgettingEngine:
    """Handles targeted, user-directed, and bulk deletion of memories."""

    def __init__(
        self,
        repository: Optional[MemoryRepository] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.repo = repository or get_memory_repository()
        self.event_bus = event_bus or get_event_bus()

    def forget_by_id(self, memory_id: str, actor: str = "user") -> bool:
        """Explicitly delete a memory by ID."""
        success = self.repo.delete(memory_id, actor=actor)
        if success:
            logger.info(f"Memory '{memory_id}' permanently deleted by {actor}.")
            self.event_bus.publish(
                Event(
                    event_type=EventType.MEMORY_DELETED,
                    payload={"memory_id": memory_id, "actor": actor},
                )
            )
        return success

    def forget_by_type(self, memory_type: MemoryType, actor: str = "user") -> int:
        """Delete all memories belonging to a specific MemoryType."""
        memories = self.repo.list(memory_type=memory_type, limit=1000)
        deleted_count = 0
        for m in memories:
            if self.repo.delete(m.id, actor=actor):
                deleted_count += 1

        logger.info(f"Deleted {deleted_count} memories of type '{memory_type.value}'")
        self.event_bus.publish(
            Event(
                event_type=EventType.MEMORY_DELETED,
                payload={"memory_type": memory_type.value, "deleted_count": deleted_count, "actor": actor},
            )
        )
        return deleted_count

    def forget_by_tag(self, tag: str, actor: str = "user") -> int:
        """Delete all memories tagged with a specific tag."""
        memories = self.repo.list(tag=tag, limit=1000)
        deleted_count = 0
        for m in memories:
            if self.repo.delete(m.id, actor=actor):
                deleted_count += 1

        logger.info(f"Deleted {deleted_count} memories with tag '{tag}'")
        self.event_bus.publish(
            Event(
                event_type=EventType.MEMORY_DELETED,
                payload={"tag": tag, "deleted_count": deleted_count, "actor": actor},
            )
        )
        return deleted_count

    def forget_session(self, session_id: str, actor: str = "user") -> int:
        """Delete all short-term memories belonging to a session."""
        all_short = self.repo.list(memory_type=MemoryType.SHORT_TERM, limit=1000)
        session_mems = [m for m in all_short if m.provenance.get("session_id") == session_id]

        deleted_count = 0
        for m in session_mems:
            if self.repo.delete(m.id, actor=actor):
                deleted_count += 1

        logger.info(f"Cleared {deleted_count} memories for session '{session_id}'")
        self.event_bus.publish(
            Event(
                event_type=EventType.MEMORY_DELETED,
                payload={"session_id": session_id, "deleted_count": deleted_count, "actor": actor},
            )
        )
        return deleted_count

    def clear_all_temporary_memories(self, actor: str = "system") -> int:
        """Clear all short-term memories across all sessions."""
        return self.forget_by_type(MemoryType.SHORT_TERM, actor=actor)
