"""ZETTA Instant Messaging (WhatsApp/Chat) Provider Interface and Fake Implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class InstantMessage:
    """Standardized chat message payload."""
    recipient: str
    content: str
    channel: str = "whatsapp"
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseMessagingProvider(ABC):
    """Abstract interface for chat/instant messaging (WhatsApp, Signal, Telegram)."""

    @abstractmethod
    def send_message(self, message: InstantMessage) -> Dict[str, Any]:
        """Send message through target chat channel."""
        raise NotImplementedError

    @abstractmethod
    def fetch_messages(self, channel: str = "whatsapp", limit: int = 10) -> List[InstantMessage]:
        """Fetch incoming messages."""
        raise NotImplementedError


class FakeMessagingProvider(BaseMessagingProvider):
    """Deterministic offline messaging provider."""

    def __init__(self) -> None:
        self.sent_messages: List[InstantMessage] = []
        self._incoming: List[InstantMessage] = [
            InstantMessage(
                recipient="me",
                content="Meeting rescheduled to 4 PM.",
                channel="whatsapp",
            )
        ]

    def send_message(self, message: InstantMessage) -> Dict[str, Any]:
        self.sent_messages.append(message)
        return {
            "success": True,
            "message_id": message.id,
            "channel": message.channel,
            "recipient": message.recipient,
            "status": "DELIVERED",
        }

    def fetch_messages(self, channel: str = "whatsapp", limit: int = 10) -> List[InstantMessage]:
        filtered = [m for m in self._incoming if m.channel.lower() == channel.lower()]
        return filtered[:limit]
