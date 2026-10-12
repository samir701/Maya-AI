"""Unit tests for MemoryDeduplicator and MemoryConsolidationEngine."""

import os
import tempfile
import unittest
from core.zetta.db import DatabaseManager
from core.zetta.memory.consolidation import MemoryConsolidationEngine
from core.zetta.memory.dedup import MemoryDeduplicator
from core.zetta.memory.repository import MemoryRepository
from core.zetta.memory.short_term import ShortTermMemory
from shared.types import Memory, MemoryType


class TestMemoryDedupConsolidation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_dedup.db")
        self.db = DatabaseManager(db_path=db_path)
        self.repo = MemoryRepository(db_manager=self.db)
        self.dedup = MemoryDeduplicator(repository=self.repo)
        self.short_term = ShortTermMemory(repository=self.repo)
        self.consolidation = MemoryConsolidationEngine(repository=self.repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_deduplication_prevents_duplicate_entries(self):
        mem1 = Memory(content="User prefers dark theme", memory_type=MemoryType.LONG_TERM)
        mem2 = Memory(content="User prefers dark theme", memory_type=MemoryType.LONG_TERM)

        saved1, is_new1 = self.dedup.merge_or_create(mem1)
        saved2, is_new2 = self.dedup.merge_or_create(mem2)

        self.assertTrue(is_new1)
        self.assertFalse(is_new2)
        self.assertEqual(saved1.id, saved2.id)

    def test_conservative_consolidation(self):
        session_id = "sess_cons"
        msg = self.short_term.add_session_message(session_id, role="user", content="Crucial project instruction")
        msg.importance = 0.9  # High importance candidate
        self.repo.update(msg)

        consolidated = self.consolidation.consolidate_session(session_id, min_importance=0.8)
        self.assertEqual(len(consolidated), 1)
        self.assertEqual(consolidated[0].memory_type, MemoryType.LONG_TERM)


if __name__ == "__main__":
    unittest.main()
