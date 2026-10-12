"""ZETTA Memory Repository Data Access Layer."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from core.zetta.db import DatabaseManager, get_db_manager
from core.zetta.utils.logging import get_logger
from shared.types import Memory, MemorySensitivity, MemorySource, MemoryType

logger = get_logger("memory_repository")


class MemoryRepository:
    """Encapsulates all SQLite persistence for ZETTA memories, tags, links, and history."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db = db_manager or get_db_manager()
        self.db.initialize_schema()

    def create(self, memory: Memory, actor: str = "system") -> Memory:
        """Persist a new Memory object and its tags and history record."""
        mem_dict = memory.to_dict()
        tags_json = json.dumps(memory.tags)
        metadata_json = json.dumps(memory.metadata)
        provenance_json = json.dumps(memory.provenance)
        embedding_json = json.dumps(memory.embedding) if memory.embedding else None

        statement = """
            INSERT INTO memories (
                id, content, memory_type, source, importance, confidence,
                created_at, updated_at, expires_at, sensitivity, metadata,
                provenance, embedding, access_count, last_accessed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            memory.id,
            memory.content,
            mem_dict["memory_type"],
            mem_dict["source"],
            memory.importance,
            memory.confidence,
            memory.created_at,
            memory.updated_at,
            memory.expires_at,
            mem_dict["sensitivity"],
            metadata_json,
            provenance_json,
            embedding_json,
            memory.access_count,
            memory.last_accessed_at,
        )
        self.db.execute_statement(statement, params)

        # Insert tags
        for tag in memory.tags:
            if tag.strip():
                self.db.execute_statement(
                    "INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                    (memory.id, tag.strip().lower()),
                )

        # Log history
        self._log_history(memory.id, "CREATE", actor=actor, details={"content_snippet": memory.content[:50]})
        return memory

    def get(self, memory_id: str) -> Optional[Memory]:
        """Fetch a single Memory by ID with tags."""
        rows = self.db.execute_query("SELECT * FROM memories WHERE id = ?", (memory_id,))
        if not rows:
            return None
        return self._row_to_memory(rows[0])

    def update(self, memory: Memory, actor: str = "system") -> Memory:
        """Update an existing Memory and sync tags."""
        memory.updated_at = datetime.now(timezone.utc).isoformat()
        mem_dict = memory.to_dict()

        statement = """
            UPDATE memories SET
                content = ?, memory_type = ?, source = ?, importance = ?,
                confidence = ?, updated_at = ?, expires_at = ?, sensitivity = ?,
                metadata = ?, provenance = ?, embedding = ?, access_count = ?,
                last_accessed_at = ?
            WHERE id = ?
        """
        params = (
            memory.content,
            mem_dict["memory_type"],
            mem_dict["source"],
            memory.importance,
            memory.confidence,
            memory.updated_at,
            memory.expires_at,
            mem_dict["sensitivity"],
            json.dumps(memory.metadata),
            json.dumps(memory.provenance),
            json.dumps(memory.embedding) if memory.embedding else None,
            memory.access_count,
            memory.last_accessed_at,
            memory.id,
        )
        self.db.execute_statement(statement, params)

        # Update tags
        self.db.execute_statement("DELETE FROM memory_tags WHERE memory_id = ?", (memory.id,))
        for tag in memory.tags:
            if tag.strip():
                self.db.execute_statement(
                    "INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                    (memory.id, tag.strip().lower()),
                )

        self._log_history(memory.id, "UPDATE", actor=actor)
        return memory

    def delete(self, memory_id: str, actor: str = "system") -> bool:
        """Delete a memory by ID."""
        self._log_history(memory_id, "DELETE", actor=actor)
        self.db.execute_statement("DELETE FROM memory_tags WHERE memory_id = ?", (memory_id,))
        self.db.execute_statement("DELETE FROM memory_links WHERE source_memory_id = ? OR target_memory_id = ?", (memory_id, memory_id))
        count = self.db.execute_statement("DELETE FROM memories WHERE id = ?", (memory_id,))
        return count > 0

    def list(
        self,
        memory_type: Optional[MemoryType] = None,
        source: Optional[MemorySource] = None,
        sensitivity: Optional[MemorySensitivity] = None,
        tag: Optional[str] = None,
        limit: int = 100,
    ) -> List[Memory]:
        """Query memories with optional filters."""
        query = "SELECT m.* FROM memories m"
        params: List[Any] = []
        conditions: List[str] = []

        if tag:
            query += " INNER JOIN memory_tags t ON m.id = t.memory_id"
            conditions.append("t.tag = ?")
            params.append(tag.strip().lower())

        if memory_type:
            conditions.append("m.memory_type = ?")
            params.append(memory_type.value if isinstance(memory_type, MemoryType) else str(memory_type))

        if source:
            conditions.append("m.source = ?")
            params.append(source.value if isinstance(source, MemorySource) else str(source))

        if sensitivity:
            conditions.append("m.sensitivity = ?")
            params.append(sensitivity.value if isinstance(sensitivity, MemorySensitivity) else str(sensitivity))

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY COALESCE(m.updated_at, m.created_at) DESC LIMIT ?"
        params.append(limit)

        rows = self.db.execute_query(query, tuple(params))
        return [self._row_to_memory(r) for r in rows]

    def search_text(self, query_text: str, limit: int = 20) -> List[Memory]:
        """Simple SQL LIKE text search across content."""
        pattern = f"%{query_text.strip()}%"
        rows = self.db.execute_query(
            "SELECT * FROM memories WHERE content LIKE ? ORDER BY importance DESC, created_at DESC LIMIT ?",
            (pattern, limit),
        )
        return [self._row_to_memory(r) for r in rows]

    def expire_memories(self) -> List[str]:
        """Delete memories whose expires_at is past current UTC time."""
        now_iso = datetime.now(timezone.utc).isoformat()
        expired_rows = self.db.execute_query(
            "SELECT id FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (now_iso,),
        )
        expired_ids = [r["id"] for r in expired_rows]

        for eid in expired_ids:
            self.delete(eid, actor="expiration_engine")

        return expired_ids

    def touch_access(self, memory_id: str) -> None:
        """Increment access_count and update last_accessed_at."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self.db.execute_statement(
            "UPDATE memories SET access_count = access_count + 1, last_accessed_at = ? WHERE id = ?",
            (now_iso, memory_id),
        )

    def _row_to_memory(self, row: Dict[str, Any]) -> Memory:
        # Fetch tags
        tag_rows = self.db.execute_query("SELECT tag FROM memory_tags WHERE memory_id = ?", (row["id"],))
        tags = [t["tag"] for t in tag_rows]

        row_dict = dict(row)
        row_dict["tags"] = tags
        return Memory.from_dict(row_dict)

    def _log_history(self, memory_id: str, action: str, actor: str = "system", details: Optional[Dict[str, Any]] = None) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        det_json = json.dumps(details) if details else None
        self.db.execute_statement(
            "INSERT INTO memory_history (memory_id, action, timestamp, actor, details) VALUES (?, ?, ?, ?, ?)",
            (memory_id, action, now_iso, actor, det_json),
        )


_repository_instance: Optional[MemoryRepository] = None


def get_memory_repository() -> MemoryRepository:
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = MemoryRepository()
    return _repository_instance
