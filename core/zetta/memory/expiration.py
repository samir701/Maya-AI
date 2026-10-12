"""ZETTA Memory Expiration Engine."""

from typing import List, Optional
from core.zetta.events import Event, EventBus, get_event_bus
from core.zetta.memory.repository import MemoryRepository, get_memory_repository
from core.zetta.utils.logging import get_logger
from shared.types import EventType

logger = get_logger("memory_expiration")


class MemoryExpirationEngine:
    """Scans and purges expired temporary memories."""

    def __init__(
        self,
        repository: Optional[MemoryRepository] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.repo = repository or get_memory_repository()
        self.event_bus = event_bus or get_event_bus()

    def process_expirations(self) -> List[str]:
        """Expire memories past their TTL and publish MEMORY_EXPIRED event."""
        expired_ids = self.repo.expire_memories()
        if expired_ids:
            logger.info(f"Purged {len(expired_ids)} expired memories.")
            self.event_bus.publish(
                Event(
                    event_type=EventType.MEMORY_EXPIRED,
                    payload={"expired_count": len(expired_ids), "expired_ids": expired_ids},
                )
            )
        return expired_ids
