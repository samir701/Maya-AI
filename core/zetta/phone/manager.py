"""ZETTA Phone Link Manager orchestrating mobile communication and security."""

from typing import Any, Callable, Dict, List, Optional
from core.zetta.phone.fake import FakePhoneProvider
from core.zetta.phone.models import DeviceConnectionState, DeviceInfo, PhoneCommand, PhoneNotification
from core.zetta.phone.provider import BasePhoneProvider
from core.zetta.security.manager import SecurityManager, get_security_manager
from core.zetta.utils.errors import ExecutionError, SecurityError
from core.zetta.utils.logging import get_logger
from shared.types.enums import PermissionLevel

logger = get_logger("phone_manager")


class PhoneManager:
    """Manages secure desktop-mobile pairing, commands, and notification streams."""

    def __init__(
        self,
        provider: Optional[BasePhoneProvider] = None,
        security_manager: Optional[SecurityManager] = None,
    ) -> None:
        self.provider = provider or FakePhoneProvider()
        self.security = security_manager or get_security_manager()

    def pair_device(self, pairing_code: str, user_role: str = "user") -> bool:
        """Authenticate and establish paired session."""
        success = self.provider.pair(pairing_code)
        status = "SUCCESS" if success else "FAILED"
        self.security.audit.log_event(
            action="phone_pair",
            actor=user_role,
            resource="mobile_device",
            status=status,
        )
        return success

    def disconnect_device(self, user_role: str = "user") -> None:
        """Disconnect the paired device."""
        self.provider.disconnect()
        self.security.audit.log_event(
            action="phone_disconnect",
            actor=user_role,
            resource="mobile_device",
            status="SUCCESS",
        )

    def get_status(self) -> Dict[str, Any]:
        """Return connectivity state and device info."""
        state = self.provider.get_connection_state()
        info = self.provider.get_device_info()
        return {
            "state": state.value,
            "device": info.__dict__ if info else None,
        }

    def fetch_notifications(self, user_role: str = "user") -> List[PhoneNotification]:
        """Retrieve recent unread notifications with LOW permission check."""
        has_perm = self.security.check_permission(user_role, PermissionLevel.LOW)
        if not has_perm:
            raise SecurityError("Permission denied to fetch mobile notifications.")
        return self.provider.fetch_notifications()

    def send_command(
        self,
        action: str,
        payload: Optional[Dict[str, Any]] = None,
        user_role: str = "user",
        confirmation_callback: Optional[Callable[[str], bool]] = None,
    ) -> Dict[str, Any]:
        """Dispatch command to mobile device enforcing risk classification and confirmations."""
        action_clean = action.lower()
        payload = payload or {}

        # Determine required permission level
        if action_clean in ["ping", "battery"]:
            req_perm = PermissionLevel.LOW
        elif action_clean in ["open_app", "navigate"]:
            req_perm = PermissionLevel.MEDIUM
        else:  # e.g. sms, call, shell, wipe
            req_perm = PermissionLevel.HIGH

        # Check role permission
        if not self.security.check_permission(user_role, req_perm):
            self.security.audit.log_event(
                action=f"phone_command:{action_clean}",
                actor=user_role,
                resource="mobile_device",
                status="DENIED",
                details={"required_permission": req_perm.value},
            )
            raise SecurityError(
                f"Permission denied for mobile command '{action_clean}'. Requires {req_perm.value}."
            )

        # Check confirmation if high risk
        if self.security.requires_user_confirmation(req_perm):
            confirmed = False
            if confirmation_callback:
                confirmed = confirmation_callback(f"Authorize sending mobile command '{action_clean}'?")
            if not confirmed:
                self.security.audit.log_event(
                    action=f"phone_command:{action_clean}",
                    actor=user_role,
                    resource="mobile_device",
                    status="REJECTED_USER",
                )
                raise SecurityError(f"Mobile command '{action_clean}' rejected by user confirmation policy.")

        cmd = PhoneCommand(action=action_clean, payload=payload)
        res = self.provider.send_command(cmd)

        status = "SUCCESS" if res.get("success") else "FAILED"
        self.security.audit.log_event(
            action=f"phone_command:{action_clean}",
            actor=user_role,
            resource="mobile_device",
            status=status,
            details=payload,
        )
        return res


_global_phone_manager: Optional[PhoneManager] = None


def get_phone_manager(provider: Optional[BasePhoneProvider] = None) -> PhoneManager:
    """Get or initialize global PhoneManager singleton."""
    global _global_phone_manager
    if _global_phone_manager is None:
        _global_phone_manager = PhoneManager(provider=provider)
    return _global_phone_manager
