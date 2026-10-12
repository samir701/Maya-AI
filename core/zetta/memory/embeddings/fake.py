"""Deterministic Fake Embedding Provider for Testing."""

import hashlib
import math
from typing import List
from core.zetta.memory.embeddings.base import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic hash-based embedding provider requiring zero external API dependencies."""

    def __init__(self, dimensions: int = 16) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> List[float]:
        """Generate normalized floating point vector from text hash."""
        vec = [0.0] * self.dimensions
        words = text.lower().split()

        for word in words:
            # MD5 hash of word to seed values across dimension positions
            h = hashlib.md5(word.encode("utf-8")).digest()
            for i in range(self.dimensions):
                val = (h[i % len(h)] / 255.0) - 0.5
                vec[i] += val

        # Calculate L2 norm
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0.0:
            return [0.0] * self.dimensions

        return [round(x / norm, 6) for x in vec]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vector lists."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return max(0.0, min(1.0, dot / (norm1 * norm2)))
