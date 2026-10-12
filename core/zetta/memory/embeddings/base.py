"""Provider-Independent Embedding Provider Interface."""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Abstract base class for ZETTA vector embedding providers."""

    dimensions: int = 16

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate vector embedding for single text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for multiple text strings."""
        pass
