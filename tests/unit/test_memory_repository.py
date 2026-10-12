"""Unit tests for MemoryRepository persistence."""

import os
import tempfile
import unittest
from core.zetta.db import DatabaseManager
from core.zetta.memory.repository import MemoryRepository
from shared.types import Memory, MemorySource, MemoryType


class TestMemoryRepository(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_memory.db")
        self.db = DatabaseManager(db_path=db_path)
        self.repo = MemoryRepository(db_manager=self.db)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_repository_crud_operations(self):
        # 1. Create
        memory = Memory(
            content="Project ZETTA architecture uses SQLite",
            memory_type=MemoryType.LONG_TERM,
            source=MemorySource.SYSTEM,
            tags=["architecture", "sqlite"],
        )
        saved = self.repo.create(memory)
        self.assertEqual(saved.id, memory.id)

        # 2. Get
        retrieved = self.repo.get(saved.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.content, "Project ZETTA architecture uses SQLite")
        self.assertIn("sqlite", retrieved.tags)

        # 3. Update
        retrieved.importance = 0.95
        updated = self.repo.update(retrieved)
        self.assertEqual(updated.importance, 0.95)

        # 4. List
        all_memories = self.repo.list()
        self.assertEqual(len(all_memories), 1)

        # 5. Delete
        success = self.repo.delete(saved.id)
        self.assertTrue(success)
        self.assertIsNone(self.repo.get(saved.id))


if __name__ == "__main__":
    unittest.main()
