"""Unit tests for FakeEmbeddingProvider and LocalVectorStore."""

import unittest
from core.zetta.memory.embeddings import FakeEmbeddingProvider, LocalVectorStore, cosine_similarity
from shared.types import Memory


class TestMemoryEmbeddings(unittest.TestCase):

    def test_fake_embedding_provider_deterministic(self):
        provider = FakeEmbeddingProvider(dimensions=16)
        vec1 = provider.embed("Python programming language")
        vec2 = provider.embed("Python programming language")
        vec3 = provider.embed("Pizza and ice cream")

        self.assertEqual(len(vec1), 16)
        self.assertEqual(vec1, vec2)  # Deterministic

        sim_identical = cosine_similarity(vec1, vec2)
        sim_unrelated = cosine_similarity(vec1, vec3)

        self.assertAlmostEqual(sim_identical, 1.0, places=4)
        self.assertGreater(sim_identical, sim_unrelated)

    def test_local_vector_store_ranking(self):
        vector_store = LocalVectorStore()
        mem1 = Memory(content="User likes Python backend development")
        mem2 = Memory(content="User prefers Linux OS setup")
        mem3 = Memory(content="Cooking pasta recipe")

        ranked = vector_store.search_similar("Python development", [mem1, mem2, mem3], top_k=2)
        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0][0].content, "User likes Python backend development")


if __name__ == "__main__":
    unittest.main()
