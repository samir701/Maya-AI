"""Unit tests for HealthChecker."""

import unittest
from core.zetta.health import check_health


class TestHealth(unittest.TestCase):

    def test_foundation_health_check(self):
        health = check_health()
        self.assertEqual(health.status, "OK")
        self.assertEqual(health.checks["config"]["status"], "OK")
        self.assertEqual(health.checks["database"]["status"], "OK")
        self.assertEqual(health.checks["event_bus"]["status"], "OK")
        self.assertEqual(health.checks["tool_registry"]["status"], "OK")
        self.assertEqual(health.checks["task_manager"]["status"], "OK")
        self.assertEqual(health.checks["security"]["status"], "OK")


if __name__ == "__main__":
    unittest.main()
