"""ZETTA Phone Link Base Provider Interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from core.zetta.phone.models import DeviceConnectionState, DeviceInfo, PhoneCommand, PhoneNotification


class BasePhoneProvider(ABC):
    """Abstract interface for desktop-to-phone connectivity."""

    @abstractmethod
    def pair(self, pairing_code: str) -> bool:
        """Attempt to authenticate and pair with a target mobile device."""
        raise NotImplementedError

    @abstractmethod
    def connect(self, device_id: str) -> bool:
        """Establish active communication channel."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Close communication channel."""
        raise NotImplementedError

    @abstractmethod
    def get_connection_state(self) -> DeviceConnectionState:
        """Query current connection state."""
        raise NotImplementedError

    @abstractmethod
    def get_device_info(self) -> Optional[DeviceInfo]:
        """Fetch device specifications and status metadata."""
        raise NotImplementedError

    @abstractmethod
    def send_command(self, command: PhoneCommand) -> Dict[str, Any]:
        """Send a command over the secure control channel."""
        raise NotImplementedError

    @abstractmethod
    def fetch_notifications(self) -> List[PhoneNotification]:
        """Retrieve recent unread notifications."""
        raise NotImplementedError
