"""End-to-End Integration test for Phase 03 Interaction Shell."""

import unittest
from core.zetta.ai.providers.fake_provider import FakeAIProvider
from core.zetta.ai.brain import AIBrain
from core.zetta.events import get_event_bus
from core.zetta.interaction import get_interaction_manager
from core.zetta.memory import get_memory_manager
from core.zetta.tasks import get_task_manager
from shared.types import EventType, MemorySource, MemoryType


class TestInteractionIntegration(unittest.TestCase):

    def setUp(self):
        self.fake_provider = FakeAIProvider()
        self.brain = AIBrain(provider=self.fake_provider)
        self.mem_mgr = get_memory_manager()
        self.task_mgr = get_task_manager()
        self.bus = get_event_bus()

        self.int_mgr = get_interaction_manager(reload=True)
        self.int_mgr.brain = self.brain

        self.recorded_events = []
        self.bus.subscribe(EventType.USER_MESSAGE_RECEIVED, lambda e: self.recorded_events.append(e))
        self.bus.subscribe(EventType.ASSISTANT_RESPONSE_GENERATED, lambda e: self.recorded_events.append(e))

    def test_full_interaction_flow_chat_memory_tasks(self):
        session_id = "integration_sess_100"

        # 1. Add explicit user memory
        mem = self.mem_mgr.add_memory(
            content="Project vision is local-first privacy-focused AI employee.",
            memory_type=MemoryType.LONG_TERM,
            source=MemorySource.USER_EXPLICIT,
        )
        self.assertIsNotNone(mem.id)

        # 2. Chat message
        res1 = self.int_mgr.process_user_message(session_id, "What is our project vision?")
        self.assertIn("Mock response to: What is our project vision?", res1)

        # 3. Create task via chat intent
        res2 = self.int_mgr.process_user_message(session_id, "Create a task to audit Phase 03 security")
        self.assertIn("Task created successfully.", res2)

        # 4. Verify task exists in TaskManager
        tasks = self.task_mgr.list_tasks()
        audit_task = [t for t in tasks if "Audit Phase 03 security" in t.name or "audit Phase 03 security" in t.name]
        self.assertTrue(len(audit_task) > 0)

        # 5. Verify event trail
        self.assertTrue(len(self.recorded_events) >= 4)


if __name__ == "__main__":
    unittest.main()
