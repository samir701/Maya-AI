"""Browser Controller managing sessions, navigation, and interactive actions."""

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from core.zetta.browser.models import (
    ActionResult,
    BrowserActionType,
    BrowserSession,
    HistoryAction,
    PageInfo,
    ScrollDirection,
    SessionState,
    WebElement,
)
from core.zetta.browser.providers.base import BrowserProvider
from core.zetta.config import get_settings
from core.zetta.events import Event, get_event_bus
from core.zetta.utils.errors.exceptions import AuthorizationError, ToolError
from core.zetta.utils.logging import get_logger
from shared.types.enums import EventType

logger = get_logger("browser_controller")

_BLOCKED_SCHEMES = {"javascript", "vbscript", "data"}
_SENSITIVE_FIELD_REGEX = re.compile(r"(password|token|secret|pin|cvv|auth_key|private_key)", re.IGNORECASE)


class BrowserController:
    """Controls browser session lifecycle, enforces security bounds, and coordinates actions."""

    def __init__(
        self,
        provider: BrowserProvider,
        persist_state: bool = False,
        storage_dir: Optional[Path] = None,
    ) -> None:
        self.provider = provider
        self.event_bus = get_event_bus()
        self.persist_state = persist_state
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = (get_settings().root_path / "runtime" / "browser").resolve()
        self._active_session_file = self.storage_dir / "active_session.txt"
        self._active_sessions: Dict[str, BrowserSession] = {}
        self._default_session_id: Optional[str] = None

        if self.persist_state:
            self._sync_persisted_state()

    def _save_active_pointer(self, session_id: str) -> None:
        if not self.persist_state:
            return
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self._active_session_file.write_text(session_id.strip(), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save active session pointer: {e}")

    def _clear_active_pointer(self) -> None:
        if not self.persist_state:
            return
        try:
            if self._active_session_file.exists():
                self._active_session_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to clear active session pointer: {e}")

    def _sync_persisted_state(self) -> None:
        """Sync in-memory active sessions with underlying provider sessions and active session pointer."""
        if not self.persist_state:
            return
        if hasattr(self.provider, "_load_state"):
            try:
                self.provider._load_state()
            except Exception as e:
                logger.warning(f"Error calling provider._load_state: {e}")

        if hasattr(self.provider, "_sessions"):
            for sid, sess in getattr(self.provider, "_sessions").items():
                if sess.state == SessionState.ACTIVE:
                    self._active_sessions[sid] = sess
                elif sid in self._active_sessions and sess.state == SessionState.CLOSED:
                    self._active_sessions[sid].state = SessionState.CLOSED

        # Prune closed/removed sessions from _active_sessions
        if hasattr(self.provider, "_sessions"):
            prov_sessions = getattr(self.provider, "_sessions")
            for sid in list(self._active_sessions.keys()):
                if sid not in prov_sessions:
                    self._active_sessions.pop(sid, None)

        if self._active_session_file.exists():
            try:
                active_id = self._active_session_file.read_text(encoding="utf-8").strip()
                if active_id and active_id in self._active_sessions and self._active_sessions[active_id].state == SessionState.ACTIVE:
                    self._default_session_id = active_id
                elif active_id and hasattr(self.provider, "_sessions") and active_id in getattr(self.provider, "_sessions"):
                    sess = getattr(self.provider, "_sessions")[active_id]
                    if sess.state == SessionState.ACTIVE:
                        self._active_sessions[active_id] = sess
                        self._default_session_id = active_id
                    else:
                        self._default_session_id = None
                else:
                    self._default_session_id = None
            except Exception:
                self._default_session_id = None

        if not self._default_session_id or (
            self._default_session_id in self._active_sessions
            and self._active_sessions[self._default_session_id].state == SessionState.CLOSED
        ):
            self._default_session_id = None
            for sid, sess in self._active_sessions.items():
                if sess.state == SessionState.ACTIVE:
                    self._default_session_id = sid
                    break

        if self._default_session_id:
            self._save_active_pointer(self._default_session_id)
        else:
            self._clear_active_pointer()

    def get_active_session(self) -> Optional[BrowserSession]:
        """Get currently active browser session without auto-launching."""
        if self.persist_state:
            self._sync_persisted_state()

        if self._default_session_id and self._default_session_id in self._active_sessions:
            session = self._active_sessions[self._default_session_id]
            if session.state == SessionState.ACTIVE:
                return session

        for session in self._active_sessions.values():
            if session.state == SessionState.ACTIVE:
                self._default_session_id = session.session_id
                if self.persist_state:
                    self._save_active_pointer(session.session_id)
                return session

        return None

    def get_session(self, session_id: str) -> BrowserSession:
        """Get session by ID with validation and cleanup."""
        if self.persist_state:
            self._sync_persisted_state()

        if hasattr(self.provider, "_dead_sessions") and session_id in getattr(self.provider, "_dead_sessions"):
            if self.persist_state and self._active_session_file.exists():
                try:
                    if self._active_session_file.read_text(encoding="utf-8").strip() == session_id:
                        self._clear_active_pointer()
                except Exception:
                    pass
            raise ToolError(f"Browser session '{session_id}' is no longer running.")

        if session_id in self._active_sessions:
            sess = self._active_sessions[session_id]
            if sess.state == SessionState.CLOSED:
                raise ToolError(f"Browser session '{session_id}' is no longer running.")
            return sess

        raise ToolError(f"Specified browser session '{session_id}' is not active.")

    def get_default_session(self) -> BrowserSession:
        """Get or auto-create a default active session."""
        active = self.get_active_session()
        if active:
            return active

        # Auto-launch default session
        settings = get_settings()
        session = self.launch(headless=settings.browser.headless)
        self._default_session_id = session.session_id
        return session

    def launch(
        self,
        browser_type: Optional[str] = None,
        headless: bool = True,
        options: Optional[Dict[str, Any]] = None,
    ) -> BrowserSession:
        """Launch and register a new browser session."""
        start_time = time.perf_counter()
        opts = options or {}
        if browser_type:
            opts["browser_type"] = browser_type
        opts["headless"] = headless

        self.event_bus.publish(
            Event(
                event_type=EventType.TOOL_STARTED,
                payload={"action": "browser_launch", "headless": headless, "browser_type": browser_type},
            )
        )

        try:
            session = self.provider.launch_session(opts)
            self._active_sessions[session.session_id] = session
            self._default_session_id = session.session_id
            if self.persist_state:
                self._save_active_pointer(session.session_id)

            duration_ms = (time.perf_counter() - start_time) * 1000
            self.event_bus.publish(
                Event(
                    event_type=EventType.TOOL_COMPLETED,
                    payload={"action": "browser_launch", "session_id": session.session_id, "duration_ms": duration_ms},
                )
            )
            return session
        except Exception as e:
            self.event_bus.publish(
                Event(
                    event_type=EventType.TOOL_FAILED,
                    payload={"action": "browser_launch", "error": str(e)},
                )
            )
            raise

    def close(self, session_id: Optional[str] = None) -> bool:
        """Close an active browser session."""
        if self.persist_state:
            self._sync_persisted_state()

        target_id = session_id or self._default_session_id
        if not target_id:
            return False

        success = self.provider.close_session(target_id)
        if target_id in self._active_sessions:
            self._active_sessions[target_id].state = SessionState.CLOSED
        if self._default_session_id == target_id:
            self._default_session_id = None
            # Reassign default if other active session exists
            for sid, sess in self._active_sessions.items():
                if sess.state == SessionState.ACTIVE:
                    self._default_session_id = sid
                    break

        if self.persist_state:
            if self._default_session_id:
                self._save_active_pointer(self._default_session_id)
            else:
                self._clear_active_pointer()

        return success

    def close_all(self) -> int:
        """Close all active sessions."""
        closed = 0
        for sid in list(self._active_sessions.keys()):
            if self.close(sid):
                closed += 1
        return closed

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List active sessions and their states."""
        if self.persist_state:
            self._sync_persisted_state()
        return [s.to_dict() for s in self._active_sessions.values() if s.state == SessionState.ACTIVE]

    def validate_url(self, url: str) -> str:
        """Sanitize and validate target URL against security policies."""
        clean_url = url.strip()
        if not clean_url or clean_url in ("about:blank", "about:"):
            return "about:blank"

        parsed = urlparse(clean_url)
        scheme = (parsed.scheme or "").lower()

        if scheme in _BLOCKED_SCHEMES:
            raise AuthorizationError(f"Navigation to URI scheme '{scheme}:' is blocked for security reasons.")

        # If scheme is missing (e.g. example.com), prepend https://
        if not scheme:
            clean_url = "https://" + clean_url
            parsed = urlparse(clean_url)
            scheme = (parsed.scheme or "").lower()

        if scheme not in ("http", "https", "file", "about"):
            raise AuthorizationError(f"Navigation to unsupported URI scheme '{scheme}:' is blocked.")

        if scheme == "file":
            # Must resolve strictly within workspace root
            from pathlib import Path
            root_path = get_settings().root_path.resolve()
            target_path = Path(parsed.path).resolve()
            try:
                target_path.relative_to(root_path)
            except ValueError:
                raise AuthorizationError(f"Access to file '{target_path}' outside workspace root is blocked.")

        return clean_url

    def navigate(self, url: str, session_id: Optional[str] = None) -> PageInfo:
        """Navigate active browser session to sanitized URL."""
        validated_url = self.validate_url(url)
        session = self._resolve_session(session_id)
        return self.provider.navigate(session.session_id, validated_url)

    def get_page_info(self, session_id: Optional[str] = None) -> PageInfo:
        """Fetch current page details from active session."""
        session = self._resolve_session(session_id)
        return self.provider.get_page_info(session.session_id)

    def detect_elements(
        self, filter_type: Optional[str] = None, session_id: Optional[str] = None
    ) -> List[WebElement]:
        """Detect interactive elements on the page."""
        session = self._resolve_session(session_id)
        return self.provider.detect_elements(session.session_id, filter_type)

    def click(self, target: str, session_id: Optional[str] = None) -> ActionResult:
        """Click an interactive element on the page."""
        session = self._resolve_session(session_id)
        return self.provider.click(session.session_id, target)

    def type_text(
        self, target: str, text: str, clear_first: bool = False, session_id: Optional[str] = None
    ) -> ActionResult:
        """Type text into an input or textarea with credential masking."""
        session = self._resolve_session(session_id)
        result = self.provider.type_text(session.session_id, target, text, clear_first)

        # Redact sensitive field in result data if target is sensitive
        if _SENSITIVE_FIELD_REGEX.search(target):
            result.message = f"Typed into sensitive field '{target}' (value redacted)."
            if "data" in result.to_dict():
                result.data["redacted"] = True

        return result

    def send_keys(self, key: str, session_id: Optional[str] = None) -> ActionResult:
        """Send key press to active page."""
        session = self._resolve_session(session_id)
        return self.provider.send_keys(session.session_id, key)

    def scroll(
        self, direction: str = "down", amount: int = 300, session_id: Optional[str] = None
    ) -> ActionResult:
        """Scroll page in desired direction."""
        try:
            scroll_dir = ScrollDirection(direction.lower())
        except Exception:
            scroll_dir = ScrollDirection.DOWN

        session = self._resolve_session(session_id)
        return self.provider.scroll(session.session_id, scroll_dir, amount)

    def history(self, action: str = "back", session_id: Optional[str] = None) -> PageInfo:
        """Execute navigation history action (back, forward, reload)."""
        try:
            h_action = HistoryAction(action.lower())
        except Exception:
            h_action = HistoryAction.RELOAD

        session = self._resolve_session(session_id)
        return self.provider.history_action(session.session_id, h_action)

    def screenshot(self, session_id: Optional[str] = None) -> bytes:
        """Capture viewport screenshot as PNG bytes."""
        session = self._resolve_session(session_id)
        return self.provider.capture_page_screenshot(session.session_id)

    def _resolve_session(self, session_id: Optional[str]) -> BrowserSession:
        if session_id:
            return self.get_session(session_id)

        active = self.get_active_session()
        if active:
            return active

        # If an active session pointer exists in storage but is dead/closed:
        if self.persist_state and self._active_session_file.exists():
            try:
                stale_id = self._active_session_file.read_text(encoding="utf-8").strip()
            except Exception:
                stale_id = ""
            if stale_id and (
                stale_id not in self._active_sessions
                or self._active_sessions[stale_id].state == SessionState.CLOSED
            ):
                self._clear_active_pointer()
                raise ToolError(f"Browser session '{stale_id}' is no longer running.")

        return self.get_default_session()
