"""Unit tests for InteractionManager orchestration."""

import unittest
from core.zetta.ai.providers.fake_provider import FakeAIProvider
from core.zetta.ai.brain import AIBrain
from core.zetta.interaction.manager import InteractionManager
from core.zetta.memory import get_memory_manager
from shared.types import MemorySource, MemoryType, AIProviderType


class TestInteractionManager(unittest.TestCase):

    def setUp(self):
        fake_provider = FakeAIProvider()
        self.brain = AIBrain(provider=fake_provider)
        self.mem_mgr = get_memory_manager()
        self.int_mgr = InteractionManager(ai_brain=self.brain, memory_manager=self.mem_mgr)

    def test_process_user_message_chat_flow(self):
        session_id = "test_chat_sess"
        response = self.int_mgr.process_user_message(session_id, "Hello ZETTA Assistant")
        self.assertIn("Mock response to: Hello ZETTA Assistant", response)

        # Check session history
        history = self.int_mgr.session_mgr.get_history(session_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].content, "Hello ZETTA Assistant")

    def test_task_intent_detection(self):
        session_id = "test_task_intent_sess"
        response = self.int_mgr.process_user_message(
            session_id, "Create a task to review ZETTA architecture"
        )
        self.assertIn("Task created successfully.", response)
        self.assertIn("review ZETTA architecture", response)

    def test_memory_context_injection_in_chat(self):
        session_id = "test_mem_chat_sess"
        # Store an explicit memory
        self.mem_mgr.add_memory(
            content="User prefers Python for all scripts.",
            memory_type=MemoryType.LONG_TERM,
            source=MemorySource.USER_EXPLICIT,
            importance=0.9,
        )

        response = self.int_mgr.process_user_message(session_id, "What programming language do I prefer?")
        self.assertIsNotNone(response)

    def test_streaming_user_message(self):
        session_id = "test_stream_sess"
        chunks = list(self.int_mgr.stream_user_message(session_id, "Stream test message"))
        self.assertTrue(len(chunks) > 0)
        full_text = "".join(chunks)
        self.assertIn("Mock response to: Stream test message", full_text)


if __name__ == "__main__":
    unittest.main()
