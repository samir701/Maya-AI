"""Unit tests for ShortTermMemory."""

import os
import tempfile
import unittest
from core.zetta.db import DatabaseManager
from core.zetta.memory.repository import MemoryRepository
from core.zetta.memory.short_term import ShortTermMemory


class TestMemoryShortTerm(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_short_term.db")
        self.db = DatabaseManager(db_path=db_path)
        self.repo = MemoryRepository(db_manager=self.db)
        self.short_term = ShortTermMemory(repository=self.repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_session_isolation_and_trimming(self):
        session_a = "sess_111"
        session_b = "sess_222"

        # Add 5 messages to session A
        for i in range(5):
            self.short_term.add_session_message(session_a, role="user", content=f"Msg A{i}")

        # Add 2 messages to session B
        for i in range(2):
            self.short_term.add_session_message(session_b, role="user", content=f"Msg B{i}")

        mems_a = self.short_term.get_session_memories(session_a)
        mems_b = self.short_term.get_session_memories(session_b)

        self.assertEqual(len(mems_a), 5)
        self.assertEqual(len(mems_b), 2)

        # Trim session A to max 3
        trimmed = self.short_term.trim_session(session_a, max_size=3)
        self.assertEqual(trimmed, 2)
        remaining_a = self.short_term.get_session_memories(session_a)
        self.assertEqual(len(remaining_a), 3)
        self.assertEqual(remaining_a[0].content, "Msg A2")  # Oldest A0, A1 purged


if __name__ == "__main__":
    unittest.main()
