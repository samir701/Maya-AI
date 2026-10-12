"""Browser Action and Result Models for ZETTA Phase 06."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ScrollDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    TOP = "top"
    BOTTOM = "bottom"
    TO_ELEMENT = "to_element"


class HistoryAction(str, Enum):
    BACK = "back"
    FORWARD = "forward"
    RELOAD = "reload"


class BrowserActionType(str, Enum):
    LAUNCH = "launch"
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    KEYBOARD = "keyboard"
    SCROLL = "scroll"
    HISTORY = "history"
    CLOSE = "close"
    SCREENSHOT = "screenshot"


@dataclass
class ActionResult:
    """Standard result returned from any browser interaction action."""
    success: bool
    action_type: BrowserActionType
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action_type": self.action_type.value,
            "message": self.message,
            "data": self.data,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
        }
