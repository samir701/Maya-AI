"""Browser Session and Tab Models for ZETTA Phase 06."""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BrowserType(str, Enum):
    CHROME = "chrome"
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    EDGE = "edge"
    FAKE = "fake"


class SessionState(str, Enum):
    LAUNCHING = "launching"
    ACTIVE = "active"
    IDLE = "idle"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class BrowserTab:
    """Represents a single tab/window within a browser session."""
    tab_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    url: str = "about:blank"
    title: str = "New Tab"
    is_active: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tab_id": self.tab_id,
            "url": self.url,
            "title": self.title,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BrowserTab":
        return cls(
            tab_id=d.get("tab_id", str(uuid.uuid4())[:8]),
            url=d.get("url", "about:blank"),
            title=d.get("title", "New Tab"),
            is_active=d.get("is_active", True),
            created_at=d.get("created_at", time.time()),
        )


@dataclass
class BrowserSession:
    """Represents an active or managed browser session."""
    session_id: str = field(default_factory=lambda: f"browser_{str(uuid.uuid4())[:8]}")
    browser_type: BrowserType = BrowserType.FAKE
    headless: bool = True
    state: SessionState = SessionState.LAUNCHING
    created_at: float = field(default_factory=time.time)
    tabs: List[BrowserTab] = field(default_factory=list)
    active_tab_id: Optional[str] = None
    pid: Optional[int] = None
    user_data_dir: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tabs:
            default_tab = BrowserTab(url="about:blank", title="Initial Tab", is_active=True)
            self.tabs.append(default_tab)
            self.active_tab_id = default_tab.tab_id

    def get_active_tab(self) -> Optional[BrowserTab]:
        for tab in self.tabs:
            if tab.tab_id == self.active_tab_id:
                return tab
        return self.tabs[0] if self.tabs else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "browser_type": self.browser_type.value,
            "headless": self.headless,
            "state": self.state.value,
            "created_at": self.created_at,
            "tab_count": len(self.tabs),
            "active_tab_id": self.active_tab_id,
            "pid": self.pid,
            "tabs": [t.to_dict() for t in self.tabs],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BrowserSession":
        raw_tabs = d.get("tabs", [])
        tabs = [BrowserTab.from_dict(t) for t in raw_tabs] if raw_tabs else []
        b_type = BrowserType(d.get("browser_type", "fake"))
        state = SessionState(d.get("state", "active"))
        return cls(
            session_id=d["session_id"],
            browser_type=b_type,
            headless=d.get("headless", True),
            state=state,
            created_at=d.get("created_at", time.time()),
            tabs=tabs,
            active_tab_id=d.get("active_tab_id"),
            pid=d.get("pid"),
            user_data_dir=d.get("user_data_dir"),
            metadata=d.get("metadata", {}),
        )
