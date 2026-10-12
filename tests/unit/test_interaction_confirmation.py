"""Unit tests for ConfirmationInterface and security prompts."""

import unittest
from core.zetta.events import get_event_bus
from core.zetta.interaction.confirmation import ConfirmationInterface
from core.zetta.security import SecurityManager
from shared.types import EventType, PermissionLevel


class TestInteractionConfirmation(unittest.TestCase):

    def setUp(self):
        self.security = SecurityManager(current_level=PermissionLevel.HIGH)
        self.bus = get_event_bus()
        self.confirm_iface = ConfirmationInterface(self.security, self.bus)
        self.received_events = []
        self.bus.subscribe(EventType.CONFIRMATION_REQUESTED, self._event_handler)

    def _event_handler(self, event):
        self.received_events.append(event)

    def test_low_permission_auto_granted(self):
        result = self.confirm_iface.request_confirmation(
            action="read_sys_info",
            permission_level=PermissionLevel.LOW,
            prompt_user=False,
        )
        self.assertTrue(result)
        self.assertEqual(len(self.received_events), 1)

    def test_high_permission_explicit_confirmation(self):
        # Auto answer Yes
        res_granted = self.confirm_iface.request_confirmation(
            action="high_risk_op",
            permission_level=PermissionLevel.HIGH,
            prompt_user=False,
            auto_answer=True,
        )
        self.assertTrue(res_granted)

        # Auto answer No
        res_denied = self.confirm_iface.request_confirmation(
            action="high_risk_op",
            permission_level=PermissionLevel.HIGH,
            prompt_user=False,
            auto_answer=False,
        )
        self.assertFalse(res_denied)


if __name__ == "__main__":
    unittest.main()
