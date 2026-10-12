"""Unit tests for logger initialization."""

import unittest
from core.zetta.utils.logging import get_logger


class TestLogging(unittest.TestCase):

    def test_logger_creation(self):
        logger = get_logger("test_component")
        self.assertEqual(logger.name, "test_component")
        self.assertGreaterEqual(len(logger.handlers), 1)
        logger.info("Test log message")


if __name__ == "__main__":
    unittest.main()
