"""ZETTA Session Abstraction & SessionManager."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from core.zetta.events import Event, EventBus, get_event_bus
from core.zetta.memory.manager import MemoryManager, get_memory_manager
from core.zetta.utils.logging import get_logger
from shared.types import AIMessage, AIRole, EventType

logger = get_logger("interaction_session")


class Session:
    """Represents an active interactive conversation session."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        messages: Optional[List[AIMessage]] = None,
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        self.created_at = created_at or now_iso
        self.updated_at = updated_at or now_iso
        self.metadata = metadata or {}
        self.messages: List[AIMessage] = messages or []

    def add_message(self, role: AIRole, content: str) -> AIMessage:
        msg = AIMessage(role=role, content=content)
        self.messages.append(msg)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return msg

    def get_history(self, limit: Optional[int] = None) -> List[AIMessage]:
        if limit and limit > 0:
            return self.messages[-limit:]
        return list(self.messages)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Session":
        messages = [
            AIMessage(role=AIRole(m["role"]), content=m["content"])
            for m in d.get("messages", [])
        ]
        return cls(
            session_id=d.get("session_id"),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
            metadata=d.get("metadata", {}),
            messages=messages,
        )


class SessionManager:
    """Manages creation, history, persistence, and lifecycle of interactive sessions."""

    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.mem_mgr = memory_manager or get_memory_manager()
        self.event_bus = event_bus or get_event_bus()
        self.active_sessions: Dict[str, Session] = {}

    def create_session(
        self,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        session = Session(session_id=session_id, metadata=metadata)
        self.active_sessions[session.session_id] = session

        self.event_bus.publish(
            Event(
                event_type=EventType.SESSION_CREATED,
                payload={"session_id": session.session_id, "metadata": session.metadata},
            )
        )
        logger.info(f"Created new interactive session '{session.session_id}'")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        return self.active_sessions.get(session_id)

    def load_or_create(
        self,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        if session_id and session_id in self.active_sessions:
            return self.active_sessions[session_id]
        return self.create_session(session_id=session_id, metadata=metadata)

    def append_message(
        self,
        session_id: str,
        role: AIRole,
        content: str,
    ) -> AIMessage:
        session = self.load_or_create(session_id)
        msg = session.add_message(role, content)

        # Store message turn in ShortTermMemory for context persistence
        try:
            self.mem_mgr.short_term.add_session_message(
                session_id=session_id,
                role=role.value,
                content=content,
            )
        except Exception as e:
            logger.warning(f"Failed to persist message turn to short-term memory: {e}")

        return msg

    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[AIMessage]:
        session = self.get_session(session_id)
        if session:
            return session.get_history(limit=limit)

        # Fallback to ShortTermMemory if session object not in memory
        st_memories = self.mem_mgr.short_term.get_session_history(session_id)
        messages = []
        for m in st_memories:
            r = AIRole.USER if m.provenance.get("role") == "user" else AIRole.ASSISTANT
            messages.append(AIMessage(role=r, content=m.content))
        if limit:
            messages = messages[-limit:]
        return messages

    def clear_session(self, session_id: str) -> int:
        cleared_count = 0
        if session_id in self.active_sessions:
            self.active_sessions[session_id].messages.clear()
            cleared_count += 1

        cleared_memories = self.mem_mgr.short_term.clear_session(session_id)
        logger.info(f"Cleared session '{session_id}' (memories purged: {cleared_memories})")
        return cleared_memories

    def close_session(self, session_id: str) -> None:
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            self.event_bus.publish(
                Event(
                    event_type=EventType.SESSION_CLOSED,
                    payload={"session_id": session_id},
                )
            )
            logger.info(f"Closed interactive session '{session_id}'")


_session_manager_instance: Optional[SessionManager] = None


def get_session_manager(reload: bool = False) -> SessionManager:
    global _session_manager_instance
    if _session_manager_instance is None or reload:
        _session_manager_instance = SessionManager()
    return _session_manager_instance
