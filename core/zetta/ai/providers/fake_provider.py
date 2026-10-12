"""Deterministic Fake AI Provider for Testing."""

from typing import Iterator, List, Optional
from core.zetta.ai.providers.base import AIProvider
from shared.types import (
    AIChoice,
    AIMessage,
    AIProviderType,
    AIRequest,
    AIResponse,
    AIRole,
    AIStreamChunk,
    AIUsage,
)

DEFAULT_FAKE_TEXT = "This is a deterministic fake AI response."


class FakeAIProvider(AIProvider):
    """Deterministic mock provider for offline development and unit tests."""

    provider_name = AIProviderType.FAKE
    model = "fake-model-v1"
    capabilities: List[str] = ["text", "streaming", "structured_json"]

    def __init__(self, default_response_text: str = DEFAULT_FAKE_TEXT) -> None:
        self.default_response_text = default_response_text
        self.last_request: Optional[AIRequest] = None
        self.call_count: int = 0

    def generate(self, request: AIRequest) -> AIResponse:
        self.call_count += 1
        self.last_request = request

        text = self.default_response_text
        if request.messages:
            last_content = request.messages[-1].content
            if text.startswith("{") or text.startswith("["):
                pass  # Structured JSON string
            elif text in (DEFAULT_FAKE_TEXT, "Fake thinking response", "Hello test") or not text:
                text = f"Mock response to: {last_content}"

        message = AIMessage(role=AIRole.ASSISTANT, content=text)
        choice = AIChoice(index=0, message=message, finish_reason="stop")
        usage = AIUsage(prompt_tokens=10, completion_tokens=15, total_tokens=25, duration_ms=1.5)

        return AIResponse(
            provider=self.provider_name,
            model=request.model or self.model,
            choices=[choice],
            usage=usage,
            raw_response={"status": "fake_ok"},
        )

    def stream(self, request: AIRequest) -> Iterator[AIStreamChunk]:
        self.call_count += 1
        self.last_request = request

        text = self.default_response_text
        if request.messages:
            last_content = request.messages[-1].content
            if text.startswith("{") or text.startswith("["):
                pass
            elif text in (DEFAULT_FAKE_TEXT, "Fake thinking response", "Hello test") or not text:
                text = f"Mock response to: {last_content}"

        words = text.split(" ")
        for i, word in enumerate(words):
            is_last = i == len(words) - 1
            chunk_text = word if is_last else word + " "
            yield AIStreamChunk(
                id=f"chunk_{i}",
                content=chunk_text,
                finish_reason="stop" if is_last else None,
                is_final=is_last,
            )

    def health_check(self) -> bool:
        return True
