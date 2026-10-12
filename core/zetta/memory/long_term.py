"""ZETTA Long-Term Memory Management."""

from typing import List, Optional
from core.zetta.memory.repository import MemoryRepository, get_memory_repository
from core.zetta.utils.logging import get_logger
from shared.types import Memory, MemorySensitivity, MemorySource, MemoryType

logger = get_logger("long_term_memory")


class LongTermMemory:
    """Manages persistent, long-term memory facts, user preferences, and project knowledge."""

    def __init__(self, repository: Optional[MemoryRepository] = None) -> None:
        self.repo = repository or get_memory_repository()

    def save_explicit_user_memory(
        self,
        content: str,
        importance: float = 0.9,
        tags: Optional[List[str]] = None,
        sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
    ) -> Memory:
        """Store explicit user-commanded persistent memory ('Remember this')."""
        memory = Memory(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            source=MemorySource.USER_EXPLICIT,
            importance=importance,
            confidence=1.0,
            tags=tags or ["user_remembered"],
            sensitivity=sensitivity,
            provenance={"explicit": True, "created_by": "user"},
        )
        saved = self.repo.create(memory, actor="user_explicit")
        logger.info(f"Saved explicit long-term user memory [ID: {saved.id}]")
        return saved

    def save_derived_fact(
        self,
        content: str,
        importance: float = 0.6,
        confidence: float = 0.8,
        tags: Optional[List[str]] = None,
        sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
        provenance: Optional[dict] = None,
    ) -> Memory:
        """Store derived project or factual knowledge into long-term memory."""
        memory = Memory(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            source=MemorySource.DERIVED,
            importance=importance,
            confidence=confidence,
            tags=tags or ["derived_fact"],
            sensitivity=sensitivity,
            provenance=provenance or {"derived": True},
        )
        return self.repo.create(memory, actor="derived_fact_engine")

    def list_long_term_memories(self, limit: int = 100) -> List[Memory]:
        """Fetch all long-term memories sorted by importance."""
        return self.repo.list(memory_type=MemoryType.LONG_TERM, limit=limit)
