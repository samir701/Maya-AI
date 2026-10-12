"""ZETTA Short-Term Session Memory Management."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from core.zetta.config import get_settings
from core.zetta.memory.repository import MemoryRepository, get_memory_repository
from core.zetta.utils.logging import get_logger
from shared.types import Memory, MemorySensitivity, MemorySource, MemoryType

logger = get_logger("short_term_memory")


class ShortTermMemory:
    """Manages ephemeral, session-bound short-term memory with strict size limits and expiration."""

    def __init__(self, repository: Optional[MemoryRepository] = None) -> None:
        self.repo = repository or get_memory_repository()

    def add_session_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
    ) -> Memory:
        """Store a conversational message bound to a specific session_id."""
        settings = get_settings()
        exp_hours = settings.memory.short_term_expiration_hours
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=exp_hours)).isoformat()

        # Check for duplicate turn in recent short-term messages for this session
        existing_session_mems = self.get_session_memories(session_id, limit=20)
        cleaned_new = content.strip().lower()

        for m in existing_session_mems:
            if m.provenance.get("role") == role and m.content.strip().lower() == cleaned_new:
                logger.info(f"Duplicate short-term session message detected in session '{session_id}'. Merging.")
                m.access_count += 1
                return self.repo.update(m, actor=f"session_{session_id}")

        memory = Memory(
            content=content,
            memory_type=MemoryType.SHORT_TERM,
            source=MemorySource.CONVERSATION,
            importance=0.4,
            expires_at=expires_at,
            sensitivity=sensitivity,
            provenance={"session_id": session_id, "role": role},
            metadata={"role": role, "session_id": session_id},
        )
        saved = self.repo.create(memory, actor=f"session_{session_id}")

        # Enforce maximum short-term session limit
        self.trim_session(session_id, max_size=settings.memory.short_term_limit)
        return saved

    def get_session_memories(self, session_id: str, limit: int = 50) -> List[Memory]:
        """Fetch chronological short-term memories for a session."""
        all_short_term = self.repo.list(memory_type=MemoryType.SHORT_TERM, limit=200)
        session_memories = [
            m for m in all_short_term if m.provenance.get("session_id") == session_id
        ]
        # Sort chronologically
        session_memories.sort(key=lambda m: m.created_at)
        return session_memories[-limit:]

    def trim_session(self, session_id: str, max_size: int = 50) -> int:
        """Trim session memories exceeding max_size (oldest first)."""
        session_mems = self.get_session_memories(session_id, limit=500)
        if len(session_mems) <= max_size:
            return 0

        num_to_delete = len(session_mems) - max_size
        to_delete = session_mems[:num_to_delete]
        for m in to_delete:
            self.repo.delete(m.id, actor="short_term_trimmer")
        logger.info(f"Trimmed {num_to_delete} oldest short-term memories from session '{session_id}'")
        return num_to_delete

    def clear_session(self, session_id: str) -> int:
        """Clear all short-term memories for a given session."""
        session_mems = self.get_session_memories(session_id, limit=1000)
        for m in session_mems:
            self.repo.delete(m.id, actor="session_clear")
        logger.info(f"Cleared {len(session_mems)} short-term memories for session '{session_id}'")
        return len(session_mems)
