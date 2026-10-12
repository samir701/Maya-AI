"""ZETTA Conservative Memory Consolidation Engine."""

from typing import List, Optional
from core.zetta.events import Event, EventBus, get_event_bus
from core.zetta.memory.dedup import MemoryDeduplicator
from core.zetta.memory.repository import MemoryRepository, get_memory_repository
from core.zetta.utils.logging import get_logger
from shared.types import EventType, Memory, MemorySource, MemoryType

logger = get_logger("memory_consolidation")


class MemoryConsolidationEngine:
    """Conservatively consolidates valuable short-term memories into persistent long-term knowledge."""

    def __init__(
        self,
        repository: Optional[MemoryRepository] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.repo = repository or get_memory_repository()
        self.event_bus = event_bus or get_event_bus()
        self.dedup = MemoryDeduplicator(self.repo)

    def consolidate_session(self, session_id: str, min_importance: float = 0.8) -> List[Memory]:
        """Consolidate high-importance short-term session memories into long-term memory."""
        all_short = self.repo.list(memory_type=MemoryType.SHORT_TERM, limit=500)
        candidates = [
            m for m in all_short
            if str(m.provenance.get("session_id")) == str(session_id)
            and m.importance >= min_importance
            and not m.content.startswith("Mock response to:")
            and m.provenance.get("role") != "assistant"
        ]

        consolidated: List[Memory] = []
        for cand in candidates:
            long_term_mem = Memory(
                content=cand.content,
                memory_type=MemoryType.LONG_TERM,
                source=MemorySource.DERIVED,
                importance=cand.importance,
                confidence=cand.confidence,
                tags=list(set(cand.tags + ["consolidated"])),
                provenance={"consolidated_from": cand.id, "session_id": session_id},
                sensitivity=cand.sensitivity,
            )

            saved, is_new = self.dedup.merge_or_create(long_term_mem)
            if is_new:
                consolidated.append(saved)
                logger.info(f"Consolidated memory candidate '{cand.id}' -> Long-Term Memory '{saved.id}'")

        if consolidated:
            self.event_bus.publish(
                Event(
                    event_type=EventType.MEMORY_CONSOLIDATED,
                    payload={"session_id": session_id, "consolidated_count": len(consolidated)},
                )
            )

        return consolidated
