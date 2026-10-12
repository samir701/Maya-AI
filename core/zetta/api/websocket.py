"""WebSocket connection manager for real-time ZETTA event broadcasting."""

import asyncio
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
from core.zetta.events import Event, get_event_bus
from core.zetta.utils.logging import get_logger

logger = get_logger("api_websocket")


class WebSocketManager:
    """Manages active WebSocket connections and broadcasts EventBus events to clients."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._subscribed = False

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Register the asyncio event loop for thread-safe cross-thread broadcasts."""
        self._loop = loop
        self._ensure_subscription()

    def _ensure_subscription(self) -> None:
        """Subscribe to the global event bus once."""
        if not self._subscribed:
            try:
                event_bus = get_event_bus()
                event_bus.subscribe_all(self._on_system_event)
                self._subscribed = True
                logger.info("WebSocketManager subscribed to global EventBus.")
            except Exception as e:
                logger.warning("Could not subscribe WebSocketManager to EventBus: %s", e)

    def _on_system_event(self, event: Event) -> None:
        """Handle incoming EventBus event and dispatch to active WebSockets."""
        if not self.active_connections:
            return

        payload = {
            "type": "event",
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp,
            "source": event.source,
            "task_id": event.task_id,
            "payload": event.payload,
        }

        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast(payload), self._loop)
        else:
            try:
                current_loop = asyncio.get_event_loop()
                if current_loop.is_running():
                    current_loop.create_task(self.broadcast(payload))
            except Exception:
                pass

    async def connect(self, websocket: WebSocket) -> None:
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.debug("WebSocket client connected. Total connections: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove disconnected client."""
        self.active_connections.discard(websocket)
        logger.debug("WebSocket client disconnected. Total connections: %d", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all active WebSocket clients."""
        dead_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """Get or initialize singleton WebSocketManager."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
