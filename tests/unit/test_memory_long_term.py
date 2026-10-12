"""Unit tests for LongTermMemory."""

import os
import tempfile
import unittest
from core.zetta.db import DatabaseManager
from core.zetta.memory.long_term import LongTermMemory
from core.zetta.memory.repository import MemoryRepository
from shared.types import MemorySource, MemoryType


class TestMemoryLongTerm(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_long_term.db")
        self.db = DatabaseManager(db_path=db_path)
        self.repo = MemoryRepository(db_manager=self.db)
        self.long_term = LongTermMemory(repository=self.repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_explicit_user_memory(self):
        mem = self.long_term.save_explicit_user_memory("User wants dark mode by default")
        self.assertEqual(mem.memory_type, MemoryType.LONG_TERM)
        self.assertEqual(mem.source, MemorySource.USER_EXPLICIT)
        self.assertIn("user_remembered", mem.tags)
        self.assertEqual(mem.importance, 0.9)


if __name__ == "__main__":
    unittest.main()
