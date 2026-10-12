"""Comprehensive Regression Test Suite for Phase 03 Final Memory Quality Fix."""

import os
import tempfile
import unittest

from core.zetta.ai.brain import AIBrain
from core.zetta.ai.providers.fake_provider import FakeAIProvider
from core.zetta.db import DatabaseManager
from core.zetta.interaction.manager import InteractionManager
from core.zetta.interaction.session import SessionManager
from core.zetta.memory.manager import MemoryManager
from core.zetta.memory.repository import MemoryRepository
from core.zetta.memory.retrieval import RetrievalEngine
from shared.types import AIRole, MemorySource, MemoryType


class TestPhase03FinalMemoryAudit(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_p3_final_memory.db")
        self.db = DatabaseManager(db_path=db_path)
        self.repo = MemoryRepository(db_manager=self.db)
        self.mem_mgr = MemoryManager(repository=self.repo)
        self.retrieval = RetrievalEngine(repository=self.repo)
        self.session_mgr = SessionManager(memory_manager=self.mem_mgr)
        self.fake_provider = FakeAIProvider()
        self.brain = AIBrain(provider=self.fake_provider)
        self.int_mgr = InteractionManager(
            session_manager=self.session_mgr,
            memory_manager=self.mem_mgr,
            ai_brain=self.brain,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------------------
    # Test A — Fake response is not a durable semantic memory
    # -------------------------------------------------------------------------
    def test_a_fake_response_not_promoted_to_long_term_or_retrieved(self):
        session_id = "test_sess_fake_resp"
        user_msg = "Hello Zetta"
        self.int_mgr.process_user_message(session_id, user_msg)

        # 1. Verify no LONG_TERM memory contains "Mock response to:"
        long_term = self.mem_mgr.list_memories(memory_type=MemoryType.LONG_TERM)
        for m in long_term:
            self.assertNotIn("Mock response to:", m.content)

        # 2. Verify retrieval ignores mock response assistant messages
        retrieved = self.mem_mgr.retrieve_relevant("Hello Zetta", session_id=session_id)
        for r in retrieved:
            self.assertNotIn("Mock response to:", r.memory.content)
            self.assertNotEqual(r.memory.provenance.get("role"), "assistant")

    # -------------------------------------------------------------------------
    # Test B — Explicit fact is durable
    # -------------------------------------------------------------------------
    def test_b_explicit_fact_is_durable(self):
        session_id = "test_sess_explicit_fact"
        input_msg = "Remember that my main project is ZETTA AI Employee."
        self.int_mgr.process_user_message(session_id, input_msg)

        long_term = self.mem_mgr.list_memories(memory_type=MemoryType.LONG_TERM)
        self.assertTrue(len(long_term) >= 1)
        contents = [m.content for m in long_term]
        self.assertIn("my main project is ZETTA AI Employee.", contents)
        self.assertNotIn("Mock response to: Remember that my main project is ZETTA AI Employee.", contents)

    # -------------------------------------------------------------------------
    # Test C — Generic query does not retrieve unrelated memories
    # -------------------------------------------------------------------------
    def test_c_generic_query_returns_no_unrelated_memories(self):
        # Store a long-term memory
        self.mem_mgr.add_memory(
            content="User prefers Python for data engineering",
            memory_type=MemoryType.LONG_TERM,
            source=MemorySource.USER_EXPLICIT,
            importance=0.9,
        )

        results = self.retrieval.query("Hello Zetta")
        self.assertEqual(
            len(results), 0,
            "Generic greeting 'Hello Zetta' should return 0 unrelated memories."
        )

    # -------------------------------------------------------------------------
    # Test D — Relevant query retrieves memory
    # -------------------------------------------------------------------------
    def test_d_relevant_query_retrieves_memory(self):
        self.mem_mgr.add_memory(
            content="my main project is ZETTA AI Employee.",
            memory_type=MemoryType.LONG_TERM,
            source=MemorySource.USER_EXPLICIT,
            importance=0.9,
        )

        results = self.retrieval.query("What is my main project?")
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0].memory.content, "my main project is ZETTA AI Employee.")
        self.assertGreaterEqual(results[0].score, 0.3)

    # -------------------------------------------------------------------------
    # Test E — Conversation history preserved
    # -------------------------------------------------------------------------
    def test_e_conversation_history_in_context(self):
        session_id = "test_sess_history"
        self.int_mgr.process_user_message(session_id, "My favorite programming language is Python.")
        self.int_mgr.process_user_message(session_id, "What programming language did I just mention?")

        last_req = self.fake_provider.last_request
        self.assertIsNotNone(last_req)
        messages = last_req.messages

        # Verify history includes turn 1 user message
        user_msgs = [m.content for m in messages if m.role == AIRole.USER]
        self.assertIn("My favorite programming language is Python.", user_msgs)

    # -------------------------------------------------------------------------
    # Test F — No duplicate current message
    # -------------------------------------------------------------------------
    def test_f_no_duplicate_current_message(self):
        session_id = "test_sess_no_dup_curr"
        prompt = "Unique test prompt for duplication check"
        self.int_mgr.process_user_message(session_id, prompt)

        last_req = self.fake_provider.last_request
        self.assertIsNotNone(last_req)

        # Count occurrences of prompt in request messages
        prompt_occurrences = [m for m in last_req.messages if m.role == AIRole.USER and m.content == prompt]
        self.assertEqual(len(prompt_occurrences), 1, "Current message must appear exactly once in AI request.")

    # -------------------------------------------------------------------------
    # Test G — No 'You >' contamination
    # -------------------------------------------------------------------------
    def test_g_no_you_prefix_contamination(self):
        session_id = "test_sess_prefix"
        raw = "You > You > Hello Zetta"
        self.int_mgr.process_user_message(session_id, raw)

        last_req = self.fake_provider.last_request
        self.assertIsNotNone(last_req)
        for m in last_req.messages:
            self.assertNotIn("You >", m.content)

    # -------------------------------------------------------------------------
    # Test H — Session isolation
    # -------------------------------------------------------------------------
    def test_h_session_isolation(self):
        sess_a = "session_alpha"
        sess_b = "session_beta"

        # Session A message
        self.int_mgr.process_user_message(sess_a, "My favorite programming language is Python.")

        # Session B retrieval query
        results_b = self.mem_mgr.retrieve_relevant("What is my favorite programming language?", session_id=sess_b)
        self.assertEqual(len(results_b), 0, "Session B must not retrieve short-term memory from Session A.")

        # Session A retrieval query
        results_a = self.mem_mgr.retrieve_relevant("What is my favorite programming language?", session_id=sess_a)
        # Should not retrieve short-term conversation turns as semantic memory unless explicitly long-term
        for r in results_a:
            self.assertNotEqual(r.memory.provenance.get("session_id"), sess_b)


if __name__ == "__main__":
    unittest.main()
