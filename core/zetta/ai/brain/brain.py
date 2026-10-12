"""ZETTA AI Brain Central Controller."""

import time
from typing import Iterator, List, Optional, Type, TypeVar
from pydantic import BaseModel

from core.zetta.ai.context.builder import ContextBuilder
from core.zetta.ai.prompts.registry import get_prompt_registry
from core.zetta.ai.providers.base import AIProvider
from core.zetta.ai.providers.factory import get_provider
from core.zetta.ai.responses.parser import ResponseParser
from core.zetta.config import get_settings
from core.zetta.events import Event, get_event_bus
from core.zetta.utils.errors import AuthenticationError, ValidationError, ZettaError
from core.zetta.utils.logging import get_logger
from shared.types import (
    AIMessage,
    AIProviderType,
    AIRequest,
    AIResponse,
    AIStreamChunk,
    EventType,
)

logger = get_logger("ai_brain")
T = TypeVar("T", bound=BaseModel)


class AIBrain:
    """Central AI orchestration brain managing requests, context, providers, and event notifications."""

    def __init__(self, provider: Optional[AIProvider] = None) -> None:
        self._provider = provider

    def get_active_provider(self, requested_type: Optional[AIProviderType] = None) -> AIProvider:
        if self._provider:
            return self._provider
        return get_provider(requested_type)

    def generate(self, request: AIRequest, provider_type: Optional[AIProviderType] = None) -> AIResponse:
        """Process AI Request through provider with retry handling, logging, and events."""
        provider = self.get_active_provider(provider_type)
        event_bus = get_event_bus()
        settings = get_settings()

        # Emit AI_REQUEST_STARTED
        event_bus.publish(
            Event(
                event_type=EventType.AI_REQUEST_STARTED,
                payload={"provider": provider.provider_name.value, "model": request.model or provider.model},
            )
        )
        logger.info(f"AI Brain sending request to '{provider.provider_name.value}' [Model: {request.model or provider.model}]")

        max_retries = settings.ai.max_retries
        attempt = 0
        last_exception = None

        while attempt <= max_retries:
            attempt += 1
            try:
                response = provider.generate(request)

                # Emit AI_REQUEST_COMPLETED
                event_bus.publish(
                    Event(
                        event_type=EventType.AI_REQUEST_COMPLETED,
                        payload={
                            "provider": response.provider.value,
                            "model": response.model,
                            "total_tokens": response.usage.total_tokens,
                            "duration_ms": response.usage.duration_ms,
                        },
                    )
                )
                logger.info(
                    f"AI Brain request completed successfully in {response.usage.duration_ms:.2f}ms [Tokens: {response.usage.total_tokens}]"
                )
                return response

            except (AuthenticationError, ValidationError) as permanent_err:
                # Do not retry permanent configuration/authentication/validation errors
                logger.error(f"Permanent AI Brain error: {permanent_err}")
                event_bus.publish(
                    Event(
                        event_type=EventType.AI_REQUEST_FAILED,
                        payload={"provider": provider.provider_name.value, "error": str(permanent_err)},
                    )
                )
                raise permanent_err

            except Exception as transient_err:
                last_exception = transient_err
                logger.warning(f"AI request attempt {attempt}/{max_retries + 1} failed: {transient_err}")
                if attempt <= max_retries:
                    backoff = 0.5 * (2 ** (attempt - 1))
                    time.sleep(backoff)

        # Retries exhausted
        event_bus.publish(
            Event(
                event_type=EventType.AI_REQUEST_FAILED,
                payload={"provider": provider.provider_name.value, "error": str(last_exception)},
            )
        )
        raise ZettaError(f"AI Brain request failed after {max_retries + 1} attempts: {last_exception}")

    def think(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider_type: Optional[AIProviderType] = None,
        response_schema: Optional[Type[T]] = None,
        history: Optional[List[AIMessage]] = None,
    ) -> AIResponse:
        """High-level thinking interface combining context preparation and execution."""
        builder = ContextBuilder()
        if system_prompt:
            builder.set_system_instructions(system_prompt)
        else:
            default_tmpl = get_prompt_registry().get("system_default")
            builder.set_system_instructions(default_tmpl.system_prompt)

        messages = builder.build_messages(prompt, history=history)
        request = AIRequest(messages=messages)

        if response_schema:
            request.response_format = {"type": "json_object"}

        response = self.generate(request, provider_type=provider_type)

        if response_schema:
            # Validate response payload against schema
            parsed_data = ResponseParser.parse_structured(response.text, response_schema)
            response.raw_response = {"parsed_schema": parsed_data.model_dump()}

        return response

    def stream(self, request: AIRequest, provider_type: Optional[AIProviderType] = None) -> Iterator[AIStreamChunk]:
        """Stream chunks from AI Provider."""
        provider = self.get_active_provider(provider_type)
        event_bus = get_event_bus()

        event_bus.publish(
            Event(
                event_type=EventType.AI_STREAM_STARTED,
                payload={"provider": provider.provider_name.value, "model": request.model or provider.model},
            )
        )

        try:
            for chunk in provider.stream(request):
                yield chunk
            event_bus.publish(
                Event(
                    event_type=EventType.AI_STREAM_COMPLETED,
                    payload={"provider": provider.provider_name.value},
                )
            )
        except Exception as e:
            event_bus.publish(
                Event(
                    event_type=EventType.AI_REQUEST_FAILED,
                    payload={"provider": provider.provider_name.value, "error": str(e)},
                )
            )
            raise e

    def stream_messages(self, messages: List[AIMessage], provider_type: Optional[AIProviderType] = None) -> Iterator[AIStreamChunk]:
        """Convenience method to stream directly from a pre-built list of messages."""
        request = AIRequest(messages=messages)
        return self.stream(request, provider_type=provider_type)


_ai_brain_instance: AIBrain = AIBrain()


def get_ai_brain() -> AIBrain:
    return _ai_brain_instance
