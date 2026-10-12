from core.zetta.memory.embeddings.base import EmbeddingProvider
from core.zetta.memory.embeddings.fake import FakeEmbeddingProvider, cosine_similarity
from core.zetta.memory.embeddings.factory import get_embedding_provider
from core.zetta.memory.embeddings.vector_store import LocalVectorStore

__all__ = [
    "EmbeddingProvider",
    "FakeEmbeddingProvider",
    "cosine_similarity",
    "get_embedding_provider",
    "LocalVectorStore",
]
