"""Embedding Provider Factory."""

from typing import Optional
from core.zetta.config import get_settings
from core.zetta.memory.embeddings.base import EmbeddingProvider
from core.zetta.memory.embeddings.fake import FakeEmbeddingProvider


def get_embedding_provider(provider_name: Optional[str] = None) -> EmbeddingProvider:
    settings = get_settings()
    name = (provider_name or settings.memory.embedding_provider).lower()

    if name == "fake":
        return FakeEmbeddingProvider(dimensions=16)

    # Default to fake provider for testing/local-first stability
    return FakeEmbeddingProvider(dimensions=16)
