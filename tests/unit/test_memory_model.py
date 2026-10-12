"""Unit tests for Memory contract models."""

import unittest
from shared.types import Memory, MemoryQueryResult, MemorySensitivity, MemorySource, MemoryType
from shared.schemas import MemorySchema


class TestMemoryModel(unittest.TestCase):

    def test_memory_creation_and_serialization(self):
        memory = Memory(
            content="User prefers Python over JavaScript",
            memory_type=MemoryType.LONG_TERM,
            source=MemorySource.USER_EXPLICIT,
            importance=0.9,
            confidence=1.0,
            tags=["preferences", "programming"],
            sensitivity=MemorySensitivity.NORMAL,
        )

        d = memory.to_dict()
        self.assertEqual(d["content"], "User prefers Python over JavaScript")
        self.assertEqual(d["memory_type"], "long_term")
        self.assertEqual(d["source"], "user_explicit")
        self.assertIn("preferences", d["tags"])

        restored = Memory.from_dict(d)
        self.assertEqual(restored.id, memory.id)
        self.assertEqual(restored.memory_type, MemoryType.LONG_TERM)
        self.assertEqual(restored.source, MemorySource.USER_EXPLICIT)

    def test_memory_pydantic_validation(self):
        memory = Memory(content="Test content")
        schema = MemorySchema(**memory.to_dict())
        self.assertEqual(schema.content, "Test content")
        self.assertEqual(schema.importance, 0.5)


if __name__ == "__main__":
    unittest.main()
