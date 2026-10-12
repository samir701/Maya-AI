"""ZETTA Central Memory Manager Facade."""

from typing import Any, Dict, List, Optional
from core.zetta.config import get_settings
from core.zetta.events import Event, EventBus, get_event_bus
from core.zetta.memory.consolidation import MemoryConsolidationEngine
from core.zetta.memory.dedup import MemoryDeduplicator
from core.zetta.memory.episodic import EpisodicMemory
from core.zetta.memory.expiration import MemoryExpirationEngine
from core.zetta.memory.forgetting import ForgettingEngine
from core.zetta.memory.long_term import LongTermMemory
from core.zetta.memory.repository import MemoryRepository, get_memory_repository
from core.zetta.memory.retrieval import RetrievalEngine
from core.zetta.memory.short_term import ShortTermMemory
from core.zetta.security import SecurityManager, get_security_manager
from core.zetta.utils.logging import get_logger
from shared.types import (
    EventType,
    Memory,
    MemoryQueryResult,
    MemorySensitivity,
    MemorySource,
    MemoryType,
    TaskStatus,
)

logger = get_logger("memory_manager")


class MemoryManager:
    """Central orchestration facade for all ZETTA memory subsystems."""

    def __init__(
        self,
        repository: Optional[MemoryRepository] = None,
        event_bus: Optional[EventBus] = None,
        security: Optional[SecurityManager] = None,
    ) -> None:
        self.repo = repository or get_memory_repository()
        self.event_bus = event_bus or get_event_bus()
        self.security = security or get_security_manager()

        self.short_term = ShortTermMemory(self.repo)
        self.long_term = LongTermMemory(self.repo)
        self.episodic = EpisodicMemory(self.repo)
        self.retrieval = RetrievalEngine(self.repo, self.security)
        self.dedup = MemoryDeduplicator(self.repo)
        self.expiration = MemoryExpirationEngine(self.repo, self.event_bus)
        self.forgetting = ForgettingEngine(self.repo, self.event_bus)
        self.consolidation = MemoryConsolidationEngine(self.repo, self.event_bus)

    def add_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.LONG_TERM,
        source: MemorySource = MemorySource.USER_EXPLICIT,
        importance: float = 0.5,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
        sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
        provenance: Optional[Dict[str, Any]] = None,
        expires_at: Optional[str] = None,
    ) -> Memory:
        """Create or merge a new Memory object."""
        memory = Memory(
            content=content,
            memory_type=memory_type,
            source=source,
            importance=importance,
            confidence=confidence,
            tags=tags or [],
            sensitivity=sensitivity,
            provenance=provenance or {},
            expires_at=expires_at,
        )

        saved, is_new = self.dedup.merge_or_create(memory)
        if is_new:
            self.event_bus.publish(
                Event(
                    event_type=EventType.MEMORY_CREATED,
                    payload={"memory_id": saved.id, "memory_type": saved.memory_type.value, "source": saved.source.value},
                )
            )
        else:
            self.event_bus.publish(
                Event(
                    event_type=EventType.MEMORY_UPDATED,
                    payload={"memory_id": saved.id, "action": "merged"},
                )
            )

        return saved

    def retrieve_relevant(
        self,
        query: str,
        limit: Optional[int] = None,
        max_sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
        session_id: Optional[str] = None,
    ) -> List[MemoryQueryResult]:
        """Query relevant memories using full retrieval and ranking pipeline."""
        settings = get_settings()
        if not settings.memory.memory_enabled:
            return []

        # Run expirations before query
        self.expiration.process_expirations()

        results = self.retrieval.query(
            query_text=query,
            limit=limit,
            max_sensitivity=max_sensitivity,
            session_id=session_id,
        )

        if results:
            self.event_bus.publish(
                Event(
                    event_type=EventType.MEMORY_RETRIEVED,
                    payload={"query_snippet": query[:30], "retrieved_count": len(results)},
                )
            )

        return results

    def record_task(
        self,
        task_id: str,
        task_name: str,
        status: TaskStatus,
        result: Optional[Any] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Memory]:
        """Record task outcome into episodic memory."""
        return self.episodic.record_task_outcome(
            task_id=task_id,
            task_name=task_name,
            status=status,
            result=result,
            error_message=error_message,
        )

    def delete_memory(self, memory_id: str) -> bool:
        """Delete memory by ID."""
        return self.forgetting.forget_by_id(memory_id)

    def list_memories(
        self,
        memory_type: Optional[MemoryType] = None,
        tag: Optional[str] = None,
        limit: int = 100,
    ) -> List[Memory]:
        """List stored memories."""
        return self.repo.list(memory_type=memory_type, tag=tag, limit=limit)


_memory_manager_instance: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager_instance
    if _memory_manager_instance is None:
        _memory_manager_instance = MemoryManager()
    return _memory_manager_instance
