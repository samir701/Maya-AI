"""Deterministic Fake Phone Provider for Offline Development and Testing."""

from typing import Any, Dict, List, Optional
from core.zetta.phone.models import DeviceConnectionState, DeviceInfo, PhoneCommand, PhoneNotification
from core.zetta.phone.provider import BasePhoneProvider


class FakePhoneProvider(BasePhoneProvider):
    """Offline deterministic phone link provider."""

    def __init__(self, default_paired: bool = False) -> None:
        self.state = DeviceConnectionState.CONNECTED if default_paired else DeviceConnectionState.DISCONNECTED
        self.device_info: Optional[DeviceInfo] = (
            DeviceInfo(
                device_id="fake_pixel_8_pro",
                name="Pixel 8 Pro (Fake)",
                model="Google Pixel 8 Pro",
                os_version="Android 14",
                battery_level=85,
                is_charging=False,
            )
            if default_paired
            else None
        )
        self.commands_sent: List[PhoneCommand] = []
        self._mock_notifications: List[PhoneNotification] = [
            PhoneNotification(
                app_name="Messages",
                title="John Doe",
                message="Hey, can you check the deployment status?",
            )
        ]

    def pair(self, pairing_code: str) -> bool:
        """Simulate pairing with a 6-digit code."""
        if pairing_code and len(pairing_code) >= 6:
            self.state = DeviceConnectionState.CONNECTED
            self.device_info = DeviceInfo(
                device_id="fake_pixel_8_pro",
                name="Pixel 8 Pro (Fake)",
                model="Google Pixel 8 Pro",
                os_version="Android 14",
                battery_level=90,
                is_charging=True,
            )
            return True
        return False

    def connect(self, device_id: str) -> bool:
        if self.device_info and self.device_info.device_id == device_id:
            self.state = DeviceConnectionState.CONNECTED
            return True
        return False

    def disconnect(self) -> None:
        self.state = DeviceConnectionState.DISCONNECTED

    def get_connection_state(self) -> DeviceConnectionState:
        return self.state

    def get_device_info(self) -> Optional[DeviceInfo]:
        return self.device_info if self.state == DeviceConnectionState.CONNECTED else None

    def send_command(self, command: PhoneCommand) -> Dict[str, Any]:
        if self.state != DeviceConnectionState.CONNECTED:
            return {"success": False, "error": "Device is not connected."}

        self.commands_sent.append(command)
        action = command.action.lower()
        if action == "ping":
            return {"success": True, "pong": True, "latency_ms": 12.5}
        elif action == "battery":
            return {"success": True, "level": self.device_info.battery_level if self.device_info else 0}
        elif action == "sms":
            return {
                "success": True,
                "sent_to": command.payload.get("recipient"),
                "status": "DELIVERED",
            }
        else:
            return {"success": True, "action": action, "data": command.payload}

    def fetch_notifications(self) -> List[PhoneNotification]:
        if self.state != DeviceConnectionState.CONNECTED:
            return []
        notifs = list(self._mock_notifications)
        self._mock_notifications.clear()
        return notifs
