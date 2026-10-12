"""Unit tests for ForgettingEngine and MemoryExpirationEngine."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from core.zetta.db import DatabaseManager
from core.zetta.memory.expiration import MemoryExpirationEngine
from core.zetta.memory.forgetting import ForgettingEngine
from core.zetta.memory.repository import MemoryRepository
from shared.types import Memory, MemoryType


class TestMemoryForgettingExpiration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_forgetting.db")
        self.db = DatabaseManager(db_path=db_path)
        self.repo = MemoryRepository(db_manager=self.db)
        self.forgetting = ForgettingEngine(repository=self.repo)
        self.expiration = MemoryExpirationEngine(repository=self.repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_explicit_forgetting_by_id_and_tag(self):
        mem = Memory(content="Temporary secret token", tags=["secret", "temp"])
        self.repo.create(mem)

        # Forget by tag
        count = self.forgetting.forget_by_tag("secret")
        self.assertEqual(count, 1)
        self.assertIsNone(self.repo.get(mem.id))

    def test_expiration_engine_purges_expired_ttl(self):
        past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        expired_mem = Memory(content="Expired session detail", expires_at=past_iso)
        self.repo.create(expired_mem)

        purged_ids = self.expiration.process_expirations()
        self.assertIn(expired_mem.id, purged_ids)
        self.assertIsNone(self.repo.get(expired_mem.id))


if __name__ == "__main__":
    unittest.main()
