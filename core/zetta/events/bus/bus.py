"""ZETTA In-Process Event Bus."""

from typing import Callable, Dict, List, Set
from core.zetta.events.event import Event
from core.zetta.utils.logging import get_logger
from shared.types.enums import EventType

logger = get_logger("event_bus")

EventHandler = Callable[[Event], None]


class EventBus:
    """Lightweight in-process event bus for pub/sub messaging across ZETTA components."""

    def __init__(self) -> None:
        self._handlers: Dict[EventType, Set[EventHandler]] = {}
        self._wildcard_handlers: Set[EventHandler] = set()

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a callback handler for a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = set()
        self._handlers[event_type].add(handler)
        logger.debug(f"Subscribed handler {handler.__name__} to event {event_type.value}")

    def subscribe_all(self, handler: EventHandler) -> None:
        """Register a callback handler for all published events."""
        self._wildcard_handlers.add(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Remove a callback handler for a specific event type."""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def publish(self, event: Event) -> int:
        """Dispatch an event synchronously to all registered subscribers."""
        logger.debug(f"Publishing event {event.event_type.value} [ID: {event.event_id}]")
        dispatched_count = 0

        # Dedicated handlers
        handlers = self._handlers.get(event.event_type, set())
        for handler in list(handlers):
            try:
                handler(event)
                dispatched_count += 1
            except Exception as e:
                logger.error(
                    f"Error in event handler {handler.__name__} for event {event.event_type.value}: {e}",
                    exc_info=True,
                )

        # Wildcard handlers
        for handler in list(self._wildcard_handlers):
            try:
                handler(event)
                dispatched_count += 1
            except Exception as e:
                logger.error(
                    f"Error in wildcard event handler {handler.__name__}: {e}",
                    exc_info=True,
                )

        return dispatched_count


_event_bus_instance: EventBus = EventBus()


def get_event_bus() -> EventBus:
    """Retrieve global singleton event bus instance."""
    return _event_bus_instance
