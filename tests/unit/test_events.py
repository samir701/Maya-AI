"""Unit tests for EventBus and Event handling."""

import unittest
from core.zetta.events import Event, EventBus
from shared.types.enums import EventType


class TestEvents(unittest.TestCase):

    def test_event_bus_publish_subscribe(self):
        bus = EventBus()
        received_events = []

        def handle_event(event: Event):
            received_events.append(event)

        bus.subscribe(EventType.APP_STARTED, handle_event)
        test_event = Event(event_type=EventType.APP_STARTED, payload={"key": "value"})

        dispatched = bus.publish(test_event)
        self.assertEqual(dispatched, 1)
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].payload["key"], "value")

    def test_event_bus_unsubscribe(self):
        bus = EventBus()
        received = []

        def handler(event: Event):
            received.append(event)

        bus.subscribe(EventType.TASK_CREATED, handler)
        bus.unsubscribe(EventType.TASK_CREATED, handler)

        bus.publish(Event(event_type=EventType.TASK_CREATED))
        self.assertEqual(len(received), 0)


if __name__ == "__main__":
    unittest.main()
