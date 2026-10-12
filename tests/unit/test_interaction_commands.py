"""Unit tests for CommandProcessor slash commands and CLI task handling."""

import unittest
from core.zetta.interaction.commands import CommandProcessor
from core.zetta.tasks import get_task_manager


class TestInteractionCommands(unittest.TestCase):

    def setUp(self):
        self.cmd_processor = CommandProcessor()
        self.task_mgr = get_task_manager()

    def test_slash_command_detection(self):
        self.assertTrue(self.cmd_processor.is_slash_command("/help"))
        self.assertTrue(self.cmd_processor.is_slash_command("  /status  "))
        self.assertFalse(self.cmd_processor.is_slash_command("hello world"))

    def test_help_command(self):
        should_exit, msg = self.cmd_processor.process_slash_command(
            "/help", "sess_1", "fake", "fake-model"
        )
        self.assertFalse(should_exit)
        self.assertIn("Available Interactive Commands", msg)

    def test_status_command(self):
        should_exit, msg = self.cmd_processor.process_slash_command(
            "/status", "sess_1", "fake", "fake-model"
        )
        self.assertFalse(should_exit)
        self.assertIn("ZETTA SYSTEM STATUS", msg)
        self.assertIn("Session ID:      sess_1", msg)

    def test_exit_command(self):
        should_exit, msg = self.cmd_processor.process_slash_command(
            "/exit", "sess_1", "fake", "fake-model"
        )
        self.assertTrue(should_exit)
        self.assertEqual(msg, "Session closed.")

    def test_cli_task_command_lifecycle(self):
        task = self.task_mgr.create_task(name="Unit Test Task")
        task_id = task.id

        t_get = self.task_mgr.get_task(task_id)
        self.assertIsNotNone(t_get)
        self.assertEqual(t_get.name, "Unit Test Task")

        t_cancelled = self.task_mgr.cancel_task(task_id)
        self.assertEqual(t_cancelled.status.value, "CANCELLED")

    def test_memory_command(self):
        should_exit, msg = self.cmd_processor.process_slash_command(
            "/memory", "sess_1", "fake", "fake-model"
        )
        self.assertFalse(should_exit)
        self.assertTrue(
            "Memory Summary" in msg or "No memories currently stored" in msg
        )

    def test_memory_search_command(self):
        should_exit, msg = self.cmd_processor.process_slash_command(
            "/memory search test", "sess_1", "fake", "fake-model"
        )
        self.assertFalse(should_exit)
        self.assertTrue(
            "Retrieved" in msg or "No relevant memories found" in msg
        )


if __name__ == "__main__":
    unittest.main()
