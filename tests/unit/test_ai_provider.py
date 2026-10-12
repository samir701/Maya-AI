"""Unit tests for AI Provider abstraction and adapters."""

import unittest
from core.zetta.ai.providers import (
    FakeAIProvider,
    GeminiProvider,
    OpenAIProvider,
    get_provider,
)
from shared.types import AIMessage, AIProviderType, AIRequest, AIRole


class TestAIProvider(unittest.TestCase):

    def test_fake_provider_generation(self):
        provider = FakeAIProvider(default_response_text="Hello test")
        request = AIRequest(messages=[AIMessage(role=AIRole.USER, content="Ping")])
        response = provider.generate(request)

        self.assertEqual(response.provider, AIProviderType.FAKE)
        self.assertIn("Mock response to: Ping", response.text)
        self.assertEqual(provider.call_count, 1)

    def test_fake_provider_streaming(self):
        provider = FakeAIProvider(default_response_text="Word1 Word2 Word3")
        request = AIRequest(messages=[AIMessage(role=AIRole.USER, content="Ping")])
        chunks = list(provider.stream(request))

        self.assertEqual(len(chunks), 3)
        self.assertTrue(chunks[-1].is_final)
        self.assertEqual("".join(c.content for c in chunks), "Word1 Word2 Word3")

    def test_provider_factory(self):
        p_fake = get_provider(AIProviderType.FAKE)
        self.assertIsInstance(p_fake, FakeAIProvider)

        p_openai = get_provider(AIProviderType.OPENAI)
        self.assertIsInstance(p_openai, OpenAIProvider)

        p_gemini = get_provider(AIProviderType.GEMINI)
        self.assertIsInstance(p_gemini, GeminiProvider)


if __name__ == "__main__":
    unittest.main()
