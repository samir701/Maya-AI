"""Abstract Base AI Provider Interface."""

from abc import ABC, abstractmethod
from typing import Iterator, List
from shared.types import AIProviderType, AIRequest, AIResponse, AIStreamChunk


class AIProvider(ABC):
    """Abstract interface that all ZETTA AI providers must implement."""

    provider_name: AIProviderType
    model: str
    capabilities: List[str] = ["text"]

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        """Synchronously generate a response for an AI request."""
        pass

    @abstractmethod
    def stream(self, request: AIRequest) -> Iterator[AIStreamChunk]:
        """Stream response chunks for an AI request."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Perform provider readiness/connectivity check."""
        pass
