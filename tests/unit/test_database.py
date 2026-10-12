"""Unit tests for SQLite database initialization and querying."""

import os
import tempfile
import unittest
from core.zetta.db import DatabaseManager


class TestDatabase(unittest.TestCase):

    def test_database_initialization(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_file = os.path.join(tmp_dir, "test_zetta.db")
            db = DatabaseManager(db_path=db_file)
            db.initialize_schema()

            self.assertTrue(os.path.exists(db_file))

            # Insert test row
            db.execute_statement(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("test_key", "test_val", "2026-09-04T00:00:00Z"),
            )

            rows = db.execute_query("SELECT * FROM settings WHERE key = ?", ("test_key",))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["value"], "test_val")


if __name__ == "__main__":
    unittest.main()
