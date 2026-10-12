"""Groq Cloud AI Provider Implementation."""

import time
from typing import Any, Dict, Iterator, List, Optional
from core.zetta.ai.providers.base import AIProvider
from core.zetta.config import get_settings
from core.zetta.integrations.groq.client import GroqClient
from core.zetta.integrations.groq.errors import GroqAPIKeyMissingError
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

logger = get_logger("provider_groq")


class GroqAIProvider(AIProvider):
    """Production provider for Groq Cloud LLMs (e.g. openai/gpt-oss-20b)."""

    provider_name = AIProviderType.GROQ

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
        client: Optional[GroqClient] = None,
    ) -> None:
        settings = get_settings()
        self.model = model or getattr(settings.ai, "groq_llm_model", "openai/gpt-oss-20b")
        self.timeout = timeout or settings.ai.timeout
        self.client = client or GroqClient(
            api_key=api_key if api_key is not None else getattr(settings.ai, "groq_api_key", None),
            base_url=base_url,
            timeout=self.timeout,
        )
        self.capabilities = ["text", "streaming", "structured_json"]

    def __repr__(self) -> str:
        return f"<GroqAIProvider model='{self.model}' client={self.client}>"

    def generate(self, request: AIRequest) -> AIResponse:
        """Synchronously generate a response using Groq Chat Completions."""
        start_time = time.perf_counter()
        messages_payload = [msg.to_dict() for msg in request.messages]
        model_name = request.model or self.model

        try:
            raw_response = self.client.chat_completion(
                messages=messages_payload,
                model=model_name,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stop=request.stop,
                response_format=request.response_format,
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return self._parse_groq_response(raw_response, elapsed_ms)

        except GroqAPIKeyMissingError as e:
            raise AuthenticationError(str(e))
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise IntegrationError(f"Groq LLM generation error: {e}")

    def stream(self, request: AIRequest) -> Iterator[AIStreamChunk]:
        """Stream response chunks for an AI request."""
        # For simplicity and robust fallback in synchronous pipelines,
        # generate full response and yield chunks
        full_response = self.generate(request)
        text = full_response.text
        chunk_size = max(1, len(text) // 5) if text else 1
        for i in range(0, len(text), chunk_size):
            yield AIStreamChunk(content=text[i : i + chunk_size])

    def health_check(self) -> bool:
        """Check provider configuration readiness."""
        return self.client.is_configured()

    def _parse_groq_response(self, data: Dict[str, Any], duration_ms: float) -> AIResponse:
        """Parse Groq API completion JSON into canonical ZETTA AIResponse."""
        choices: List[AIChoice] = []
        for c in data.get("choices", []):
            msg_data = c.get("message", {})
            role_str = msg_data.get("role", "assistant")
            role = AIRole(role_str) if role_str in AIRole._value2member_map_ else AIRole.ASSISTANT
            msg = AIMessage(role=role, content=msg_data.get("content", ""))
            choices.append(
                AIChoice(
                    index=c.get("index", 0),
                    message=msg,
                    finish_reason=c.get("finish_reason"),
                )
            )

        raw_usage = data.get("usage", {})
        usage = AIUsage(
            prompt_tokens=raw_usage.get("prompt_tokens", 0),
            completion_tokens=raw_usage.get("completion_tokens", 0),
            total_tokens=raw_usage.get("total_tokens", 0),
            duration_ms=duration_ms,
        )

        return AIResponse(
            id=data.get("id", f"groq_{int(time.time())}"),
            provider=self.provider_name,
            model=data.get("model", self.model),
            choices=choices,
            usage=usage,
            raw_response=data,
        )
