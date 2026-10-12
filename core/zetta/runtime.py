"""ZETTA Application Runtime Lifecycle Controller.

Provides a unified, idempotent startup sequence ensuring that system resources,
database schemas, tool registries, and agent fleets are initialized exactly once.
"""

import threading
from typing import Optional
from core.zetta.db import get_db_manager
from core.zetta.events import get_event_bus
from core.zetta.tasks import get_task_manager
from core.zetta.tools import get_tool_registry
from core.zetta.agents.manager.registry import get_agent_registry
from core.zetta.agents.fleet import register_default_fleet
from core.zetta.utils.logging import get_logger

logger = get_logger("runtime_lifecycle")

_runtime_lock = threading.Lock()
_runtime_initialized = False


def initialize_runtime(force: bool = False) -> bool:
    """Initialize core ZETTA runtime subsystems idempotently.

    Args:
        force: If True, forces re-initialization even if already initialized.

    Returns:
        bool: True if initialization was executed, False if already initialized.
    """
    global _runtime_initialized
    with _runtime_lock:
        if _runtime_initialized and not force:
            logger.debug("ZETTA runtime already initialized; skipping initialization.")
            return False

        logger.info("Initializing ZETTA core runtime...")

        # 1. Database Schema Initialization (once)
        try:
            db = get_db_manager()
            db.initialize_schema()
        except Exception as e:
            logger.error(f"Error initializing database schema during runtime startup: {e}")

        # 2. Event Bus & Task Manager
        try:
            get_event_bus()
            get_task_manager()
        except Exception as e:
            logger.error(f"Error initializing event/task infrastructure: {e}")

        # 3. Tool Registry (default tools registered on singleton creation)
        try:
            get_tool_registry()
        except Exception as e:
            logger.error(f"Error initializing tool registry: {e}")

        # 4. Agent Fleet (idempotent registration)
        try:
            agent_reg = get_agent_registry()
            register_default_fleet(agent_reg)
        except Exception as e:
            logger.error(f"Error initializing agent fleet: {e}")

        _runtime_initialized = True
        logger.info("ZETTA core runtime initialized successfully.")
        return True


def is_runtime_initialized() -> bool:
    """Return whether the ZETTA runtime has completed initialization."""
    global _runtime_initialized
    return _runtime_initialized


def reset_runtime_lifecycle() -> None:
    """Reset the runtime initialization state (primarily for test harness isolation)."""
    global _runtime_initialized
    with _runtime_lock:
        _runtime_initialized = False
