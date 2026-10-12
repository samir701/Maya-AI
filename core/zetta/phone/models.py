"""ZETTA Phone Link Data Contracts and Models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class DeviceConnectionState(str, Enum):
    """Phone connection and authorization state."""
    DISCONNECTED = "DISCONNECTED"
    PAIRING = "PAIRING"
    CONNECTED = "CONNECTED"
    LOCKED = "LOCKED"
    ERROR = "ERROR"


@dataclass
class DeviceInfo:
    """Hardware and identity specifications of a paired phone."""
    device_id: str
    name: str = "Android Device"
    model: str = "Generic Phone"
    os_version: str = "Android 14"
    paired_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    battery_level: Optional[int] = 100
    is_charging: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhoneCommand:
    """Command payload sent across the desktop-phone link."""
    action: str
    payload: Dict[str, Any] = field(default_factory=dict)
    command_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PhoneNotification:
    """Notification received from connected phone."""
    app_name: str
    title: str
    message: str
    notification_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
