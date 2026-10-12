"""Browser Manager - Central Orchestration Layer for ZETTA Phase 06."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.zetta.browser.controller import BrowserController
from core.zetta.browser.models import (
    ActionResult,
    BrowserSession,
    PageInfo,
    WebElement,
)
from core.zetta.browser.providers import (
    BrowserProvider,
    FakeBrowserProvider,
    LocalBrowserProvider,
    get_browser_provider,
)
from core.zetta.config import get_settings
from core.zetta.utils.logging import get_logger

logger = get_logger("browser_manager")


class BrowserManager:
    """Orchestrates browser automation, session management, and vision bridges."""

    def __init__(
        self,
        provider: Optional[BrowserProvider] = None,
        use_fake: bool = False,
        persist_state: bool = False,
        storage_dir: Optional[Path] = None,
    ) -> None:
        self._use_fake = use_fake
        self._persist_state = persist_state
        self._storage_dir = storage_dir
        self._provider = provider or get_browser_provider(
            use_fake=use_fake, persist_state=persist_state, storage_dir=storage_dir
        )
        self._controller = BrowserController(
            self._provider, persist_state=persist_state, storage_dir=storage_dir
        )

    @property
    def controller(self) -> BrowserController:
        return self._controller

    @property
    def provider(self) -> BrowserProvider:
        return self._provider

    def status(self) -> Dict[str, Any]:
        """Get overall status of browser subsystem, installed binaries, and sessions."""
        browsers = self._provider.discover_browsers()
        active_sessions = self._controller.list_sessions()
        return {
            "provider": self._provider.__class__.__name__,
            "is_available": self._provider.is_available(),
            "installed_browsers": browsers,
            "active_sessions": active_sessions,
            "session_count": len(active_sessions),
        }

    def launch(
        self,
        browser_type: Optional[str] = None,
        headless: bool = True,
        options: Optional[Dict[str, Any]] = None,
    ) -> BrowserSession:
        return self._controller.launch(browser_type=browser_type, headless=headless, options=options)

    def close(self, session_id: Optional[str] = None) -> bool:
        return self._controller.close(session_id=session_id)

    def close_all(self) -> int:
        return self._controller.close_all()

    def navigate(self, url: str, session_id: Optional[str] = None) -> PageInfo:
        return self._controller.navigate(url=url, session_id=session_id)

    def get_page_info(self, session_id: Optional[str] = None) -> PageInfo:
        return self._controller.get_page_info(session_id=session_id)

    def detect_elements(
        self, filter_type: Optional[str] = None, session_id: Optional[str] = None
    ) -> List[WebElement]:
        return self._controller.detect_elements(filter_type=filter_type, session_id=session_id)

    def click(self, target: str, session_id: Optional[str] = None) -> ActionResult:
        return self._controller.click(target=target, session_id=session_id)

    def type_text(
        self, target: str, text: str, clear_first: bool = False, session_id: Optional[str] = None
    ) -> ActionResult:
        return self._controller.type_text(target=target, text=text, clear_first=clear_first, session_id=session_id)

    def send_keys(self, key: str, session_id: Optional[str] = None) -> ActionResult:
        return self._controller.send_keys(key=key, session_id=session_id)

    def scroll(
        self, direction: str = "down", amount: int = 300, session_id: Optional[str] = None
    ) -> ActionResult:
        return self._controller.scroll(direction=direction, amount=amount, session_id=session_id)

    def history(self, action: str = "back", session_id: Optional[str] = None) -> PageInfo:
        return self._controller.history(action=action, session_id=session_id)

    def get_active_session(self) -> Optional[BrowserSession]:
        """Get currently active browser session without auto-launching."""
        return self._controller.get_active_session()

    def get_session(self, session_id: str) -> BrowserSession:
        """Get session by ID with validation."""
        return self._controller.get_session(session_id)

    def capture_screenshot(
        self, session_id: Optional[str] = None, save_to_disk: bool = True
    ) -> Dict[str, Any]:
        """Capture webpage screenshot, optionally saving to runtime/captures/ directory."""
        resolved_session = self._controller._resolve_session(session_id)
        png_bytes = self._controller.screenshot(session_id=resolved_session.session_id)
        current_page = self._controller.get_page_info(session_id=resolved_session.session_id)

        file_path_str: Optional[str] = None
        if save_to_disk:
            root_path = get_settings().root_path
            captures_dir = (root_path / "runtime" / "captures").resolve()
            captures_dir.mkdir(parents=True, exist_ok=True)

            timestamp = int(time.time() * 1000)
            clean_host = "page"
            try:
                from urllib.parse import urlparse
                host = urlparse(current_page.url).netloc
                if host:
                    clean_host = host.replace(":", "_").replace(".", "_")
            except Exception:
                pass

            filename = f"browser_{timestamp}_{clean_host}.png"
            saved_file = captures_dir / filename
            with open(saved_file, "wb") as f:
                f.write(png_bytes)
            file_path_str = str(saved_file)

        return {
            "url": current_page.url,
            "title": current_page.title,
            "bytes_length": len(png_bytes),
            "file_path": file_path_str,
            "image_data": png_bytes,
        }


# Global instance
_browser_manager_instance: Optional[BrowserManager] = None


def get_browser_manager(
    use_fake: bool = False,
    persist_state: bool = False,
    storage_dir: Optional[Path] = None,
) -> BrowserManager:
    """Get global browser manager instance."""
    global _browser_manager_instance
    if _browser_manager_instance is None:
        _browser_manager_instance = BrowserManager(
            use_fake=use_fake,
            persist_state=persist_state,
            storage_dir=storage_dir,
        )
    elif (
        (use_fake and not _browser_manager_instance._use_fake)
        or (persist_state and not _browser_manager_instance._persist_state)
        or (storage_dir and _browser_manager_instance._storage_dir != storage_dir)
    ):
        _browser_manager_instance = BrowserManager(
            use_fake=use_fake,
            persist_state=persist_state,
            storage_dir=storage_dir,
        )
    return _browser_manager_instance


def set_browser_manager(manager: BrowserManager) -> None:
    """Set global browser manager instance (for testing)."""
    global _browser_manager_instance
    _browser_manager_instance = manager
