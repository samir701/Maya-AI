"""Unit tests for AIBrain controller."""

import unittest
from pydantic import BaseModel
from core.zetta.ai.brain import AIBrain
from core.zetta.ai.providers.fake_provider import FakeAIProvider
from shared.types import AIMessage, AIProviderType, AIRequest, AIRole


class SampleSchema(BaseModel):
    greeting: str
    status: str


class TestAIBrain(unittest.TestCase):

    def test_brain_think(self):
        fake = FakeAIProvider(default_response_text="Fake thinking response")
        brain = AIBrain(provider=fake)

        response = brain.think(prompt="Hello Brain")
        self.assertEqual(response.provider, AIProviderType.FAKE)
        self.assertIn("Mock response to: Hello Brain", response.text)

    def test_brain_think_structured_schema(self):
        fake = FakeAIProvider(default_response_text='{"greeting": "Hello", "status": "ok"}')
        brain = AIBrain(provider=fake)

        response = brain.think(
            prompt="Get JSON",
            response_schema=SampleSchema,
        )
        self.assertIn("parsed_schema", response.raw_response)
        self.assertEqual(response.raw_response["parsed_schema"]["greeting"], "Hello")

    def test_brain_stream(self):
        fake = FakeAIProvider(default_response_text="Stream chunk test")
        brain = AIBrain(provider=fake)

        request = AIRequest(messages=[AIMessage(role=AIRole.USER, content="Stream")])
        chunks = list(brain.stream(request))
        self.assertGreater(len(chunks), 0)


if __name__ == "__main__":
    unittest.main()
