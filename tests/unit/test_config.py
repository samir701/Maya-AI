"""Unit tests for configuration system."""

import unittest
from core.zetta.config import get_settings
from core.zetta.utils.errors import ConfigurationError


class TestConfig(unittest.TestCase):

    def test_default_config_loading(self):
        settings = get_settings(reload=True)
        self.assertIn(settings.app.env, ["development", "testing", "production"])
        self.assertEqual(settings.app.version, "0.1.0")
        self.assertIsNotNone(settings.db.db_path)
        self.assertIn(settings.logging.log_level, ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])

    def test_environment_variable_override(self):
        import os
        os.environ["ZETTA_ENV"] = "production"
        os.environ["ZETTA_LOG_LEVEL"] = "DEBUG"
        settings = get_settings(reload=True)
        self.assertEqual(settings.app.env, "production")
        self.assertEqual(settings.logging.log_level, "DEBUG")

        # Cleanup
        os.environ.pop("ZETTA_ENV", None)
        os.environ.pop("ZETTA_LOG_LEVEL", None)
        get_settings(reload=True)


if __name__ == "__main__":
    unittest.main()
