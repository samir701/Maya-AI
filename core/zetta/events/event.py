"""ZETTA Event Definition."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from shared.types.enums import EventType


@dataclass
class Event:
    event_type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "core"
    task_id: Optional[str] = None
    agent_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else str(self.event_type),
            "timestamp": self.timestamp,
            "source": self.source,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "payload": self.payload,
        }
