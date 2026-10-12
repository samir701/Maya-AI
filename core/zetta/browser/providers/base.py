"""Abstract Base Browser Provider for ZETTA Phase 06."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from core.zetta.browser.models import (
    ActionResult,
    BrowserSession,
    HistoryAction,
    PageInfo,
    ScrollDirection,
    WebElement,
)


class BrowserProvider(ABC):
    """Abstract interface for all ZETTA browser automation drivers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider dependencies/executables are available on host."""
        pass

    @abstractmethod
    def discover_browsers(self) -> List[Dict[str, Any]]:
        """Discover installed browser binaries and capabilities."""
        pass

    @abstractmethod
    def launch_session(self, options: Optional[Dict[str, Any]] = None) -> BrowserSession:
        """Launch and initialize a new browser session."""
        pass

    @abstractmethod
    def close_session(self, session_id: str) -> bool:
        """Terminate and clean up an active browser session."""
        pass

    @abstractmethod
    def navigate(self, session_id: str, url: str) -> PageInfo:
        """Navigate current active tab to destination URL."""
        pass

    @abstractmethod
    def get_page_info(self, session_id: str) -> PageInfo:
        """Extract structured page information from active tab."""
        pass

    @abstractmethod
    def detect_elements(
        self, session_id: str, filter_type: Optional[str] = None
    ) -> List[WebElement]:
        """Detect interactive elements on the active page."""
        pass

    @abstractmethod
    def click(self, session_id: str, target: str) -> ActionResult:
        """Click an element by selector, element_id, or visible text."""
        pass

    @abstractmethod
    def type_text(
        self, session_id: str, target: str, text: str, clear_first: bool = False
    ) -> ActionResult:
        """Type text into an input field or textarea."""
        pass

    @abstractmethod
    def send_keys(self, session_id: str, key: str) -> ActionResult:
        """Send keyboard key press (Enter, Escape, Tab, ArrowDown, etc.)."""
        pass

    @abstractmethod
    def scroll(
        self, session_id: str, direction: ScrollDirection, amount: int = 300
    ) -> ActionResult:
        """Scroll the active page in given direction."""
        pass

    @abstractmethod
    def history_action(self, session_id: str, action: HistoryAction) -> PageInfo:
        """Perform navigation history action (back, forward, reload)."""
        pass

    @abstractmethod
    def capture_page_screenshot(self, session_id: str) -> bytes:
        """Capture viewport screenshot as PNG bytes."""
        pass
