"""ZETTA Phone Link Architecture."""

from core.zetta.phone.fake import FakePhoneProvider
from core.zetta.phone.manager import PhoneManager, get_phone_manager
from core.zetta.phone.models import DeviceConnectionState, DeviceInfo, PhoneCommand, PhoneNotification
from core.zetta.phone.provider import BasePhoneProvider

__all__ = [
    "BasePhoneProvider",
    "FakePhoneProvider",
    "PhoneManager",
    "get_phone_manager",
    "DeviceConnectionState",
    "DeviceInfo",
    "PhoneCommand",
    "PhoneNotification",
]
