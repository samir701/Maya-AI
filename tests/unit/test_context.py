"""Unit tests for ContextBuilder."""

import unittest
from core.zetta.ai.context import ContextBuilder
from shared.types import AIRole


class TestContext(unittest.TestCase):

    def test_context_builder(self):
        builder = ContextBuilder()
        builder.set_system_instructions("System Instructions")
        builder.add_conversation_message(AIRole.USER, "Previous message")
        builder.set_task_context(task_id="t1", task_name="Task1", details={"key": "val"})

        messages = builder.build_messages(user_prompt="Current message")

        self.assertGreaterEqual(len(messages), 3)
        self.assertEqual(messages[0].role, AIRole.SYSTEM)
        self.assertIn("System Instructions", messages[0].content)
        self.assertIn("[Active Task Context]", messages[0].content)
        self.assertEqual(messages[-1].role, AIRole.USER)
        self.assertEqual(messages[-1].content, "Current message")


if __name__ == "__main__":
    unittest.main()
