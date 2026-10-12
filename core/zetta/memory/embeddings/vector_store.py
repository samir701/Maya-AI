"""Local-first Vector Store implementation."""

from typing import List, Optional, Tuple
from core.zetta.memory.embeddings.base import EmbeddingProvider
from core.zetta.memory.embeddings.fake import cosine_similarity
from core.zetta.memory.embeddings.factory import get_embedding_provider
from shared.types import Memory


class LocalVectorStore:
    """In-memory & SQLite backed local vector index for semantic similarity search."""

    def __init__(self, provider: Optional[EmbeddingProvider] = None) -> None:
        self.provider = provider or get_embedding_provider()

    def ensure_memory_embedding(self, memory: Memory) -> Memory:
        """Generate embedding vector for memory content if missing."""
        if not memory.embedding:
            memory.embedding = self.provider.embed(memory.content)
        return memory

    def search_similar(self, query: str, candidate_memories: List[Memory], top_k: int = 10) -> List[Tuple[Memory, float]]:
        """Rank candidate memories by cosine similarity against query text vector."""
        if not candidate_memories:
            return []

        query_vector = self.provider.embed(query)
        scored: List[Tuple[Memory, float]] = []

        for mem in candidate_memories:
            if not mem.embedding:
                mem.embedding = self.provider.embed(mem.content)
            sim = cosine_similarity(query_vector, mem.embedding)
            scored.append((mem, sim))

        # Sort descending by similarity
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]
