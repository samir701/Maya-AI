"""Integration test linking AIBrain, EventBus, ContextBuilder, and ResponseParser."""

import unittest
from pydantic import BaseModel
from core.zetta.ai import AIBrain, ContextBuilder, ResponseParser
from core.zetta.ai.providers import FakeAIProvider
from core.zetta.events import Event, get_event_bus
from shared.types import EventType


class AnalysisResultSchema(BaseModel):
    analysis: str
    confidence: float


class TestAIIntegration(unittest.TestCase):

    def test_full_ai_integration_flow(self):
        event_bus = get_event_bus()
        captured_events = []

        def on_event(evt: Event):
            captured_events.append(evt)

        event_bus.subscribe_all(on_event)

        fake_provider = FakeAIProvider(default_response_text='{"analysis": "Phase 01 initialized", "confidence": 0.99}')
        brain = AIBrain(provider=fake_provider)

        # 1. Build Context
        builder = ContextBuilder()
        builder.set_system_instructions("You are ZETTA AI Core.")
        messages = builder.build_messages(user_prompt="Analyze architecture state")

        # 2. Execute Thinking & Structured Parsing
        response = brain.think(
            prompt="Analyze architecture state",
            system_prompt="You are ZETTA AI Core.",
            response_schema=AnalysisResultSchema,
        )

        # 3. Assert Response correctness
        self.assertEqual(response.provider.value, "fake")
        self.assertIsNotNone(response.raw_response.get("parsed_schema"))
        self.assertEqual(response.raw_response["parsed_schema"]["confidence"], 0.99)

        # 4. Verify AI Events published
        event_types = [e.event_type for e in captured_events]
        self.assertIn(EventType.AI_REQUEST_STARTED, event_types)
        self.assertIn(EventType.AI_REQUEST_COMPLETED, event_types)


if __name__ == "__main__":
    unittest.main()
