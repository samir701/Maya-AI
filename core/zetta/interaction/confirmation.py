"""ZETTA Security Confirmation Interface."""

import sys
from typing import Any, Dict, Optional
from core.zetta.events import Event, EventBus, get_event_bus
from core.zetta.security import SecurityManager, get_security_manager
from core.zetta.utils.logging import get_logger
from shared.types import EventType, PermissionLevel

logger = get_logger("confirmation_interface")


class ConfirmationInterface:
    """Manages security confirmation workflows for sensitive or high-permission actions."""

    def __init__(
        self,
        security_manager: Optional[SecurityManager] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.security = security_manager or get_security_manager()
        self.event_bus = event_bus or get_event_bus()

    def request_confirmation(
        self,
        action: str,
        permission_level: PermissionLevel,
        details: Optional[Dict[str, Any]] = None,
        prompt_user: bool = True,
        auto_answer: Optional[bool] = None,
    ) -> bool:
        """Request confirmation for an action requiring permission approval.

        Returns True if granted/allowed, False if denied/rejected.
        """
        details_dict = details or {}
        requires_confirm = self.security.confirmation.requires_confirmation(permission_level)

        self.event_bus.publish(
            Event(
                event_type=EventType.CONFIRMATION_REQUESTED,
                payload={
                    "action": action,
                    "permission_level": permission_level.value,
                    "requires_confirmation": requires_confirm,
                    "details": details_dict,
                },
            )
        )

        # Check if permission level is granted by checker
        if not self.security.check_tool_permission(permission_level):
            logger.warning(f"Action '{action}' blocked by PermissionChecker ({permission_level.value})")
            return False

        if not requires_confirm:
            return True

        # Render Terminal Confirmation Prompt
        print("\n----------------------------------------")
        print("ACTION REQUIRES CONFIRMATION")
        print("----------------------------------------")
        print(f"Action:     {action}")
        print(f"Permission: {permission_level.value}")
        if details_dict:
            print(f"Details:    {details_dict}")
        print("----------------------------------------")

        if auto_answer is not None:
            granted = auto_answer
        elif prompt_user:
            try:
                response = input("Allow this action? [y/N]: ").strip().lower()
                granted = response in ("y", "yes")
            except (KeyboardInterrupt, EOFError):
                granted = False
        else:
            granted = False

        if granted:
            logger.info(f"User GRANTED confirmation for action '{action}'")
        else:
            logger.info(f"User DENIED confirmation for action '{action}'")

        return granted
