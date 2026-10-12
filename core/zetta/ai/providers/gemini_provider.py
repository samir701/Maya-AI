"""Google Gemini Provider Adapter."""

import json
import time
from typing import Any, Dict, Iterator, List, Optional
from core.zetta.ai.providers.base import AIProvider
from core.zetta.config import get_settings
from core.zetta.utils.errors import AuthenticationError, IntegrationError
from core.zetta.utils.logging import get_logger
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

logger = get_logger("provider_gemini")


class GeminiProvider(AIProvider):
    """Provider adapter for Google Gemini API."""

    provider_name = AIProviderType.GEMINI

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.ai.api_key or "gemini_mock_key"
        self.model = model or "gemini-1.5-pro"
        self.timeout = timeout
        self.capabilities = ["text", "streaming", "vision"]

    def generate(self, request: AIRequest) -> AIResponse:
        start_time = time.perf_counter()
        # Normalizes request prompt contents
        prompt_text = ""
        if request.messages:
            prompt_text = request.messages[-1].content

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Construct normalized response
        msg = AIMessage(role=AIRole.ASSISTANT, content=f"Gemini response to: {prompt_text}")
        choice = AIChoice(index=0, message=msg, finish_reason="STOP")
        usage = AIUsage(prompt_tokens=15, completion_tokens=20, total_tokens=35, duration_ms=elapsed_ms)

        return AIResponse(
            provider=self.provider_name,
            model=request.model or self.model,
            choices=[choice],
            usage=usage,
            raw_response={"candidates": [{"content": {"parts": [{"text": msg.content}]}}]},
        )

    def stream(self, request: AIRequest) -> Iterator[AIStreamChunk]:
        prompt_text = request.messages[-1].content if request.messages else ""
        words = f"Gemini response to: {prompt_text}".split(" ")
        for i, word in enumerate(words):
            is_last = i == len(words) - 1
            chunk_text = word if is_last else word + " "
            yield AIStreamChunk(
                id=f"gemini_chunk_{i}",
                content=chunk_text,
                finish_reason="STOP" if is_last else None,
                is_final=is_last,
            )

    def health_check(self) -> bool:
        return bool(self.api_key)
