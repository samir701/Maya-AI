"""Unit tests for GroqAIProvider."""

from unittest.mock import MagicMock
import pytest
from core.zetta.ai.providers.factory import ProviderFactory
from core.zetta.ai.providers.groq_provider import GroqAIProvider
from core.zetta.integrations.groq.errors import GroqAPIKeyMissingError
from core.zetta.utils.errors import AuthenticationError, IntegrationError
from shared.types import AIMessage, AIProviderType, AIRequest, AIRole


class TestGroqAI:
    """Test suite for Groq AI Provider."""

    def test_factory_resolves_groq_provider(self):
        factory = ProviderFactory()
        provider = factory.get_provider(AIProviderType.GROQ)
        assert isinstance(provider, GroqAIProvider)
        assert provider.provider_name == AIProviderType.GROQ

    def test_successful_generation_and_parsing(self):
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True
        mock_client.chat_completion.return_value = {
            "id": "chatcmpl_groq_999",
            "model": "openai/gpt-oss-20b",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "I am ZETTA powered by Groq."},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 8, "total_tokens": 23},
        }

        provider = GroqAIProvider(client=mock_client)
        assert provider.health_check()

        req = AIRequest(messages=[AIMessage(role=AIRole.USER, content="Introduce yourself")])
        response = provider.generate(req)

        assert response.id == "chatcmpl_groq_999"
        assert response.model == "openai/gpt-oss-20b"
        assert response.text == "I am ZETTA powered by Groq."
        assert response.usage.total_tokens == 23

    def test_missing_api_key_raises_auth_error(self):
        mock_client = MagicMock()
        mock_client.chat_completion.side_effect = GroqAPIKeyMissingError()

        provider = GroqAIProvider(client=mock_client)
        req = AIRequest(messages=[AIMessage(role=AIRole.USER, content="Hello")])

        with pytest.raises(AuthenticationError):
            provider.generate(req)

    def test_unexpected_error_wrapped_in_integration_error(self):
        mock_client = MagicMock()
        mock_client.chat_completion.side_effect = RuntimeError("Socket dropped")

        provider = GroqAIProvider(client=mock_client)
        req = AIRequest(messages=[AIMessage(role=AIRole.USER, content="Hello")])

        with pytest.raises(IntegrationError):
            provider.generate(req)
