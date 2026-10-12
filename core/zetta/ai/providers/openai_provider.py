"""OpenAI-Compatible HTTP AI Provider Adapter."""

import json
import time
import urllib.error
import urllib.request
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

logger = get_logger("provider_openai")


class OpenAIProvider(AIProvider):
    """Production provider for OpenAI and OpenAI-compatible services (vLLM, Ollama, LocalAI, LM Studio)."""

    provider_name = AIProviderType.OPENAI

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.ai.api_key or "mock_key"
        self.base_url = (base_url or settings.ai.api_base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model or settings.ai.default_model or "gpt-4o"
        self.timeout = timeout or settings.ai.timeout
        self.capabilities = ["text", "streaming", "structured_json"]

    def __repr__(self) -> str:
        masked_key = f"{self.api_key[:4]}..." if len(self.api_key) > 6 else "****"
        return f"<OpenAIProvider model='{self.model}' base_url='{self.base_url}' api_key='{masked_key}'>"

    def _prepare_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def generate(self, request: AIRequest) -> AIResponse:
        endpoint = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": request.model or self.model,
            "messages": [msg.to_dict() for msg in request.messages],
            "temperature": request.temperature,
            "stream": False,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        if request.response_format:
            payload["response_format"] = request.response_format

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data_bytes, headers=self._prepare_headers(), method="POST")

        start_time = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                resp_data = json.loads(resp.read().decode("utf-8"))
                return self._parse_openai_response(resp_data, elapsed_ms)
        except urllib.error.HTTPError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            if e.code == 401:
                raise AuthenticationError(f"OpenAI Authentication Failed: {e.reason}")
            raise IntegrationError(f"OpenAI API Error HTTP {e.code}: {e.reason}. Details: {error_body}")
        except Exception as e:
            raise IntegrationError(f"OpenAI request failed: {e}")

    def _parse_openai_response(self, data: Dict[str, Any], duration_ms: float) -> AIResponse:
        choices = []
        for c in data.get("choices", []):
            msg_data = c.get("message", {})
            role_str = msg_data.get("role", "assistant")
            role = AIRole(role_str) if role_str in AIRole._value2member_map_ else AIRole.ASSISTANT
            msg = AIMessage(role=role, content=msg_data.get("content", ""))
            choices.append(AIChoice(index=c.get("index", 0), message=msg, finish_reason=c.get("finish_reason")))

        raw_usage = data.get("usage", {})
        usage = AIUsage(
            prompt_tokens=raw_usage.get("prompt_tokens", 0),
            completion_tokens=raw_usage.get("completion_tokens", 0),
            total_tokens=raw_usage.get("total_tokens", 0),
            duration_ms=duration_ms,
        )

        return AIResponse(
            id=data.get("id", ""),
            provider=self.provider_name,
            model=data.get("model", self.model),
            choices=choices,
            usage=usage,
            raw_response=data,
        )

    def stream(self, request: AIRequest) -> Iterator[AIStreamChunk]:
        endpoint = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": request.model or self.model,
            "messages": [msg.to_dict() for msg in request.messages],
            "temperature": request.temperature,
            "stream": True,
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data_bytes, headers=self._prepare_headers(), method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                for line in resp:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_json = json.loads(data_str)
                            choice = chunk_json.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")
                            finish_reason = choice.get("finish_reason")
                            yield AIStreamChunk(
                                id=chunk_json.get("id", ""),
                                content=content,
                                finish_reason=finish_reason,
                                is_final=finish_reason is not None,
                            )
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise IntegrationError(f"OpenAI streaming request failed: {e}")

    def health_check(self) -> bool:
        """Check provider status."""
        return bool(self.base_url)
