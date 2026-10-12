"""ZETTA Browser & Web Control Subsystem (Phase 06)."""

from core.zetta.browser.controller import BrowserController
from core.zetta.browser.manager import (
    BrowserManager,
    get_browser_manager,
    set_browser_manager,
)
from core.zetta.browser.models import (
    ActionResult,
    BrowserActionType,
    BrowserSession,
    BrowserTab,
    BrowserType,
    ElementLocation,
    ElementType,
    HistoryAction,
    PageInfo,
    ScrollDirection,
    SessionState,
    WebElement,
)
from core.zetta.browser.providers import (
    BrowserProvider,
    FakeBrowserProvider,
    LocalBrowserProvider,
    get_browser_provider,
)

__all__ = [
    "BrowserController",
    "BrowserManager",
    "get_browser_manager",
    "set_browser_manager",
    "ActionResult",
    "BrowserActionType",
    "BrowserSession",
    "BrowserTab",
    "BrowserType",
    "ElementLocation",
    "ElementType",
    "HistoryAction",
    "PageInfo",
    "ScrollDirection",
    "SessionState",
    "WebElement",
    "BrowserProvider",
    "FakeBrowserProvider",
    "LocalBrowserProvider",
    "get_browser_provider",
]
