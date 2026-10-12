"""Centralized ZETTA Structured Logger."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from core.zetta.config.settings import get_settings


class StructuredJsonFormatter(logging.Formatter):
    """JSON formatter for structured ZETTA log output."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": getattr(record, "component", record.name),
            "message": record.getMessage(),
        }

        # Contextual metadata fields
        for field in ("event", "task_id", "agent_id", "error_info", "execution_context"):
            val = getattr(record, field, None)
            if val is not None:
                log_data[field] = val

        if record.exc_info and not record.msg:
            log_data["error_info"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class StandardFormatter(logging.Formatter):
    """Human-readable console formatter."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        component = getattr(record, "component", record.name)
        task_str = f" [Task:{getattr(record, 'task_id')}]" if hasattr(record, "task_id") and record.task_id else ""
        agent_str = f" [Agent:{getattr(record, 'agent_id')}]" if hasattr(record, "agent_id") and record.agent_id else ""
        return f"[{timestamp}] [{record.levelname:<8}] [{component}]{task_str}{agent_str}: {record.getMessage()}"


def setup_logger(name: str = "zetta") -> logging.Logger:
    """Initialize logger for component."""
    settings = get_settings()
    logger = logging.getLogger(name)

    level_name = settings.logging.log_level.upper()
    log_level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(log_level)

    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(StandardFormatter())
        logger.addHandler(console_handler)

        # File Handler (Structured JSON)
        log_dir = settings.root_path / settings.logging.log_dir
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "zetta.log")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(file_handler)

    return logger


def get_logger(component_name: str) -> logging.Logger:
    """Retrieve logger instance bound to specific component."""
    return setup_logger(component_name)
