"""ZETTA Email Communication Provider Interface and Fake Implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class EmailMessage:
    """Standardized email payload."""
    to: List[str]
    subject: str
    body: str
    id: str = field(default_factory=lambda: str(uuid4()))
    cc: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BaseEmailProvider(ABC):
    """Abstract interface for dispatching and receiving email messages."""

    @abstractmethod
    def send_email(self, message: EmailMessage) -> Dict[str, Any]:
        """Dispatch email through provider service."""
        raise NotImplementedError

    @abstractmethod
    def fetch_inbox(self, limit: int = 10) -> List[EmailMessage]:
        """Fetch recent inbox messages."""
        raise NotImplementedError


class FakeEmailProvider(BaseEmailProvider):
    """Deterministic offline email provider."""

    def __init__(self) -> None:
        self.sent_messages: List[EmailMessage] = []
        self._inbox: List[EmailMessage] = [
            EmailMessage(
                to=["user@example.com"],
                subject="Weekly Engineering Update",
                body="Sprint goals completed on schedule. Phase 08 tests passing.",
            )
        ]

    def send_email(self, message: EmailMessage) -> Dict[str, Any]:
        self.sent_messages.append(message)
        return {
            "success": True,
            "message_id": message.id,
            "to": message.to,
            "subject": message.subject,
            "status": "SENT",
        }

    def fetch_inbox(self, limit: int = 10) -> List[EmailMessage]:
        return self._inbox[:limit]
