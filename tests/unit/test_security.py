"""Unit tests for Security permission and confirmation policies."""

import unittest
from core.zetta.security import SecurityManager, PermissionChecker, ConfirmationPolicy
from shared.types.enums import PermissionLevel
from core.zetta.utils.errors import AuthorizationError
from shared.types.contracts import Permission


class TestSecurity(unittest.TestCase):

    def test_permission_checker(self):
        checker = PermissionChecker(current_level=PermissionLevel.MEDIUM)
        self.assertTrue(checker.is_granted(PermissionLevel.LOW))
        self.assertTrue(checker.is_granted(PermissionLevel.MEDIUM))
        self.assertFalse(checker.is_granted(PermissionLevel.HIGH))

        with self.assertRaises(AuthorizationError):
            checker.validate_permission(Permission(name="high_op", level=PermissionLevel.HIGH))

    def test_confirmation_policy(self):
        policy = ConfirmationPolicy(threshold=PermissionLevel.HIGH)
        self.assertFalse(policy.requires_confirmation(PermissionLevel.LOW))
        self.assertTrue(policy.requires_confirmation(PermissionLevel.HIGH))
        self.assertTrue(policy.requires_confirmation(PermissionLevel.CRITICAL))


if __name__ == "__main__":
    unittest.main()
