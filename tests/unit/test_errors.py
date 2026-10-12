"""Unit tests for exception hierarchy."""

import unittest
from core.zetta.utils.errors import (
    ZettaError,
    ConfigurationError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    ToolError,
    AgentError,
    TaskError,
    BrowserError,
    IntegrationError,
    SecurityError,
)


class TestErrors(unittest.TestCase):

    def test_exception_hierarchy(self):
        err = ToolError("Tool failed", details={"tool": "test_tool"})
        self.assertIsInstance(err, ZettaError)
        self.assertEqual(err.code, "ToolError")
        self.assertEqual(err.message, "Tool failed")
        self.assertEqual(err.details["tool"], "test_tool")

        serialized = err.to_dict()
        self.assertEqual(serialized["error"], "ToolError")
        self.assertEqual(serialized["message"], "Tool failed")

    def test_all_custom_exceptions(self):
        exceptions = [
            ConfigurationError("config fail"),
            AuthenticationError("auth fail"),
            AuthorizationError("authz fail"),
            ValidationError("validation fail"),
            ToolError("tool fail"),
            AgentError("agent fail"),
            TaskError("task fail"),
            BrowserError("browser fail"),
            IntegrationError("integration fail"),
            SecurityError("security fail"),
        ]
        for exc in exceptions:
            self.assertIsInstance(exc, ZettaError)
            self.assertIsNotNone(exc.to_dict()["message"])


if __name__ == "__main__":
    unittest.main()
