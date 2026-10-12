"""ZETTA SQLite Database Manager & Initializer."""

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.zetta.config.settings import get_settings
from core.zetta.utils.logging import get_logger

logger = get_logger("database")


class DatabaseManager:
    """Manages SQLite database connection and schema initialization."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        settings = get_settings()
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = settings.db.get_absolute_db_path(settings.root_path)

    def get_connection(self) -> sqlite3.Connection:
        """Create and return a new SQLite connection."""
        os.makedirs(self.db_path.parent, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_schema(self) -> None:
        """Create foundational Phase 00 & Phase 02 database tables."""
        logger.info(f"Initializing database schema at {self.db_path}")
        conn = self.get_connection()
        try:
            with conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        result TEXT,
                        error TEXT,
                        metadata TEXT
                    );

                    CREATE TABLE IF NOT EXISTS events (
                        id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        source TEXT NOT NULL,
                        task_id TEXT,
                        agent_id TEXT,
                        payload TEXT
                    );

                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        action TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        resource TEXT NOT NULL,
                        status TEXT NOT NULL,
                        details TEXT
                    );

                    /* Phase 02 Memory Architecture Tables */
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        source TEXT NOT NULL,
                        importance REAL NOT NULL DEFAULT 0.5,
                        confidence REAL NOT NULL DEFAULT 1.0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        expires_at TEXT,
                        sensitivity TEXT NOT NULL DEFAULT 'normal',
                        metadata TEXT,
                        provenance TEXT,
                        embedding TEXT,
                        access_count INTEGER DEFAULT 0,
                        last_accessed_at TEXT
                    );

                    CREATE TABLE IF NOT EXISTS memory_tags (
                        memory_id TEXT NOT NULL,
                        tag TEXT NOT NULL,
                        PRIMARY KEY (memory_id, tag),
                        FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS memory_links (
                        id TEXT PRIMARY KEY,
                        source_memory_id TEXT NOT NULL,
                        target_memory_id TEXT NOT NULL,
                        relationship TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (source_memory_id) REFERENCES memories(id) ON DELETE CASCADE,
                        FOREIGN KEY (target_memory_id) REFERENCES memories(id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS memory_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        memory_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        details TEXT
                    );

                    CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
                    CREATE INDEX IF NOT EXISTS idx_memories_source ON memories(source);
                    CREATE INDEX IF NOT EXISTS idx_memories_expires ON memories(expires_at);
                    CREATE INDEX IF NOT EXISTS idx_memory_tags ON memory_tags(tag);
                """)
            logger.info("Database schema initialized successfully.")
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return rows as dictionaries."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def execute_statement(self, statement: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE statement."""
        conn = self.get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(statement, params)
                return cursor.rowcount
        finally:
            conn.close()


_db_manager_instance: Optional[DatabaseManager] = None


def get_db_manager(db_path: Optional[str] = None) -> DatabaseManager:
    global _db_manager_instance
    if _db_manager_instance is None or db_path is not None:
        _db_manager_instance = DatabaseManager(db_path=db_path)
    return _db_manager_instance
