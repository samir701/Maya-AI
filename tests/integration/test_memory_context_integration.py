"""Integration test linking MemoryManager, ContextBuilder, AIBrain, and EventBus."""

import os
import tempfile
import unittest
from core.zetta.ai.brain import AIBrain
from core.zetta.ai.context import ContextBuilder
from core.zetta.ai.providers import FakeAIProvider
from core.zetta.db import DatabaseManager
from core.zetta.events import Event, get_event_bus
from core.zetta.memory.manager import MemoryManager
from core.zetta.memory.repository import MemoryRepository
from shared.types import EventType, MemorySource, MemoryType, AIRole


class TestMemoryContextIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_integration.db")
        self.db = DatabaseManager(db_path=db_path)
        self.repo = MemoryRepository(db_manager=self.db)
        self.mem_mgr = MemoryManager(repository=self.repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_full_memory_context_ai_brain_flow(self):
        captured_events = []
        event_bus = get_event_bus()

        def on_event(evt: Event):
            captured_events.append(evt)

        event_bus.subscribe_all(on_event)

        # 1. Add persistent user preferences into memory.
        # NOTE: FakeEmbeddingProvider is hash/lexical-based, not semantic.
        # The memory content intentionally includes the words "programming language"
        # so that the query "What programming language do I prefer?" produces
        # measurable cosine similarity (shared token overlap) and passes
        # the min_similarity_threshold filter.
        self.mem_mgr.add_memory(
            content="User prefer Python programming language for data engineering and dark theme",
            memory_type=MemoryType.LONG_TERM,
            source=MemorySource.USER_EXPLICIT,
            importance=0.9,
        )

        # 2. Build Context with Memory Injection
        user_prompt = "What programming language do I prefer?"
        builder = ContextBuilder()
        builder.set_system_instructions("You are ZETTA AI Employee.")
        builder.inject_relevant_memories(user_prompt=user_prompt, memory_manager=self.mem_mgr)

        messages = builder.build_messages(user_prompt=user_prompt)

        # Assert memory was injected into System prompt
        self.assertTrue(any("Retrieved Relevant Memory Context" in m.content for m in messages if m.role == AIRole.SYSTEM))
        self.assertTrue(any("Python programming language" in m.content for m in messages if m.role == AIRole.SYSTEM))

        # 3. Pass to AIBrain
        fake_provider = FakeAIProvider(default_response_text="Based on your memories, you prefer Python.")
        brain = AIBrain(provider=fake_provider)

        response = brain.think(prompt=user_prompt, system_prompt="You are ZETTA AI Employee.")
        self.assertIn("Python", response.text)

        # 4. Verify Memory and AI Events captured
        event_types = [e.event_type for e in captured_events]
        self.assertIn(EventType.MEMORY_CREATED, event_types)
        self.assertIn(EventType.MEMORY_RETRIEVED, event_types)


if __name__ == "__main__":
    unittest.main()
