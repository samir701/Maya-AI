"""Unit tests for RetrievalEngine and MemoryRanker."""

import os
import tempfile
import unittest
from core.zetta.db import DatabaseManager
from core.zetta.memory.repository import MemoryRepository
from core.zetta.memory.retrieval import RetrievalEngine
from shared.types import Memory, MemorySensitivity, MemorySource, MemoryType


class TestMemoryRetrieval(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_retrieval.db")
        self.db = DatabaseManager(db_path=db_path)
        self.repo = MemoryRepository(db_manager=self.db)
        self.retrieval = RetrievalEngine(repository=self.repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_query_retrieval_and_sensitivity_filtering(self):
        # 1. Add Normal Memory
        mem_normal = Memory(
            content="User prefers Python for data analysis",
            memory_type=MemoryType.LONG_TERM,
            source=MemorySource.USER_EXPLICIT,
            importance=0.9,
            sensitivity=MemorySensitivity.NORMAL,
        )
        self.repo.create(mem_normal)

        # 2. Add Sensitive Memory
        mem_sensitive = Memory(
            content="User bank API key is sk-secret-12345",
            memory_type=MemoryType.LONG_TERM,
            source=MemorySource.USER_EXPLICIT,
            importance=0.9,
            sensitivity=MemorySensitivity.SENSITIVE,
        )
        self.repo.create(mem_sensitive)

        # Query with NORMAL max sensitivity -> Sensitive memory must be filtered out
        results = self.retrieval.query("Python data analysis", max_sensitivity=MemorySensitivity.NORMAL)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].memory.content, "User prefers Python for data analysis")


if __name__ == "__main__":
    unittest.main()
