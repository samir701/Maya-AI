"""Deterministic Fake Browser Provider for ZETTA Phase 06 Testing & Offline Execution."""

import json
import time
import uuid
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional
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
from core.zetta.browser.providers.base import BrowserProvider
from core.zetta.config import get_settings
from core.zetta.utils.errors.exceptions import ToolError
from core.zetta.utils.logging import get_logger

logger = get_logger("fake_browser_provider")


class FakeBrowserProvider(BrowserProvider):
    """Deterministic, zero-network in-memory browser simulation for offline tests and validation."""

    def __init__(
        self,
        persist_state: bool = False,
        storage_dir: Optional[Path] = None,
    ) -> None:
        self.persist_state = persist_state
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = (get_settings().root_path / "runtime" / "browser").resolve()
        self._state_file = self.storage_dir / "fake_sessions.json"

        self._sessions: Dict[str, BrowserSession] = {}
        self._pages: Dict[str, Dict[str, Any]] = {}  # session_id -> current page state
        self._history: Dict[str, List[str]] = {}      # session_id -> list of visited URLs
        self._history_index: Dict[str, int] = {}      # session_id -> current index in history

        if self.persist_state:
            self._load_state()

    def _save_state(self) -> None:
        if not self.persist_state:
            return
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            serialized_sessions = {sid: sess.to_dict() for sid, sess in self._sessions.items()}
            serialized_pages = {}
            for sid, pstate in self._pages.items():
                serialized_pages[sid] = {
                    "url": pstate["url"],
                    "title": pstate["title"],
                    "text": pstate["text"],
                    "status_code": pstate.get("status_code", 200),
                    "scroll_y": pstate.get("scroll_y", 0),
                    "elements": [
                        e.to_dict() if hasattr(e, "to_dict") else e
                        for e in pstate.get("elements", [])
                    ],
                }
            data = {
                "sessions": serialized_sessions,
                "pages": serialized_pages,
                "history": self._history,
                "history_index": self._history_index,
            }
            tmp_file = self._state_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp_file.replace(self._state_file)
        except Exception as e:
            logger.warning(f"Failed to save fake browser state: {e}")

    def _load_state(self) -> None:
        if not self._state_file.exists():
            return
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for sid, sdata in data.get("sessions", {}).items():
                self._sessions[sid] = BrowserSession.from_dict(sdata)
            for sid, pdata in data.get("pages", {}).items():
                raw_elements = pdata.get("elements", [])
                elements = [
                    WebElement.from_dict(e) if isinstance(e, dict) else e
                    for e in raw_elements
                ]
                self._pages[sid] = {
                    "url": pdata.get("url", "about:blank"),
                    "title": pdata.get("title", "New Tab"),
                    "text": pdata.get("text", ""),
                    "status_code": pdata.get("status_code", 200),
                    "scroll_y": pdata.get("scroll_y", 0),
                    "elements": elements,
                }
            self._history = data.get("history", {})
            self._history_index = data.get("history_index", {})
        except Exception as e:
            logger.warning(f"Failed to load fake browser state: {e}")

    def is_available(self) -> bool:
        return True

    def discover_browsers(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "fake-browser",
                "type": "fake",
                "version": "1.0.0-mock",
                "path": "/mock/bin/fake-browser",
                "headless_supported": True,
                "is_default": True,
            },
            {
                "name": "google-chrome-mock",
                "type": "chrome",
                "version": "120.0.6099.109",
                "path": "/usr/bin/google-chrome",
                "headless_supported": True,
                "is_default": False,
            }
        ]

    def launch_session(self, options: Optional[Dict[str, Any]] = None) -> BrowserSession:
        options = options or {}
        browser_type_val = options.get("browser_type", "fake")
        try:
            b_type = BrowserType(browser_type_val)
        except Exception:
            b_type = BrowserType.FAKE

        headless = options.get("headless", True)
        session_id = f"fake_session_{str(uuid.uuid4())[:8]}"

        session = BrowserSession(
            session_id=session_id,
            browser_type=b_type,
            headless=headless,
            state=SessionState.ACTIVE,
            pid=99999,
            metadata={"fake": True, "engine": "in-memory-dom"},
        )
        self._sessions[session_id] = session
        self._history[session_id] = ["about:blank"]
        self._history_index[session_id] = 0

        # Initialize blank page
        self._pages[session_id] = self._create_page_state("about:blank", "New Tab", "Blank Page")
        self._save_state()
        return session

    def close_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._sessions[session_id].state = SessionState.CLOSED
            self._pages.pop(session_id, None)
            self._history.pop(session_id, None)
            self._history_index.pop(session_id, None)
            self._save_state()
            return True
        return False

    def navigate(self, session_id: str, url: str) -> PageInfo:
        session = self._get_session(session_id)
        clean_url = url.strip()
        if not clean_url:
            clean_url = "about:blank"

        # Update history
        idx = self._history_index.get(session_id, 0)
        hist = self._history.get(session_id, [])
        # truncate forward history if navigating from middle
        hist = hist[: idx + 1]
        hist.append(clean_url)
        self._history[session_id] = hist
        self._history_index[session_id] = len(hist) - 1

        # Generate mock page for URL
        page_state = self._generate_mock_page(clean_url)
        self._pages[session_id] = page_state

        active_tab = session.get_active_tab()
        if active_tab:
            active_tab.url = clean_url
            active_tab.title = page_state["title"]

        self._save_state()
        return self.get_page_info(session_id)

    def get_page_info(self, session_id: str) -> PageInfo:
        self._get_session(session_id)
        if session_id not in self._pages and self.persist_state:
            self._load_state()
        page_state = self._pages.get(session_id) or self._create_page_state("about:blank", "Blank", "")
        elements: List[WebElement] = page_state["elements"]

        links_count = sum(1 for e in elements if e.element_type == ElementType.LINK)
        buttons_count = sum(1 for e in elements if e.element_type == ElementType.BUTTON)
        inputs_count = sum(1 for e in elements if e.element_type in (ElementType.INPUT, ElementType.TEXTAREA))

        return PageInfo(
            url=page_state["url"],
            title=page_state["title"],
            visible_text=page_state["text"],
            status_code=page_state.get("status_code", 200),
            viewport_width=1280,
            viewport_height=800,
            links_count=links_count,
            buttons_count=buttons_count,
            inputs_count=inputs_count,
            load_time_ms=12.5,
            metadata={"scroll_y": page_state.get("scroll_y", 0)},
        )

    def detect_elements(
        self, session_id: str, filter_type: Optional[str] = None
    ) -> List[WebElement]:
        self._get_session(session_id)
        if session_id not in self._pages and self.persist_state:
            self._load_state()
        page_state = self._pages.get(session_id) or self._create_page_state("about:blank", "Blank", "")
        elements: List[WebElement] = page_state["elements"]

        if filter_type:
            ft = filter_type.lower()
            return [e for e in elements if e.element_type.value.lower() == ft]
        return elements.copy()

    def click(self, session_id: str, target: str) -> ActionResult:
        self._get_session(session_id)
        elements = self.detect_elements(session_id)
        target_clean = target.strip()

        matched: Optional[WebElement] = None
        for elem in elements:
            if elem.element_id == target_clean:
                matched = elem
                break
            if elem.attributes.get("id") == target_clean:
                matched = elem
                break
            if elem.selector == target_clean:
                matched = elem
                break
            if target_clean.lower() in elem.text.lower():
                matched = elem
                break

        if not matched:
            return ActionResult(
                success=False,
                action_type=BrowserActionType.CLICK,
                message=f"Element matching '{target}' not found on page.",
                data={"target": target},
                duration_ms=5.0,
            )

        # Handle navigation if link
        if matched.element_type == ElementType.LINK and "href" in matched.attributes:
            href = matched.attributes["href"]
            self.navigate(session_id, href)
            return ActionResult(
                success=True,
                action_type=BrowserActionType.CLICK,
                message=f"Clicked link '{matched.text}', navigated to '{href}'.",
                data={"element": matched.to_dict(), "navigated_to": href},
                duration_ms=8.0,
            )

        return ActionResult(
            success=True,
            action_type=BrowserActionType.CLICK,
            message=f"Clicked element: {matched.to_summary()}",
            data={"element": matched.to_dict()},
            duration_ms=6.0,
        )

    def type_text(
        self, session_id: str, target: str, text: str, clear_first: bool = False
    ) -> ActionResult:
        self._get_session(session_id)
        elements = self.detect_elements(session_id)
        target_clean = target.strip()

        matched: Optional[WebElement] = None
        for elem in elements:
            if elem.element_id == target_clean or elem.attributes.get("id") == target_clean or elem.selector == target_clean:
                matched = elem
                break
            if elem.element_type in (ElementType.INPUT, ElementType.TEXTAREA):
                matched = elem
                break

        if not matched:
            return ActionResult(
                success=False,
                action_type=BrowserActionType.TYPE,
                message=f"Input element matching '{target}' not found.",
                data={"target": target},
                duration_ms=4.0,
            )

        if clear_first:
            matched.value = text
        else:
            matched.value = (matched.value or "") + text

        self._save_state()

        return ActionResult(
            success=True,
            action_type=BrowserActionType.TYPE,
            message=f"Typed text into {matched.to_summary()}",
            data={"element_id": matched.element_id, "text_length": len(text)},
            duration_ms=10.0,
        )

    def send_keys(self, session_id: str, key: str) -> ActionResult:
        self._get_session(session_id)
        key_clean = key.strip()
        return ActionResult(
            success=True,
            action_type=BrowserActionType.KEYBOARD,
            message=f"Sent keyboard key '{key_clean}' to active page.",
            data={"key": key_clean},
            duration_ms=3.0,
        )

    def scroll(
        self, session_id: str, direction: ScrollDirection, amount: int = 300
    ) -> ActionResult:
        self._get_session(session_id)
        page_state = self._pages.get(session_id) or self._create_page_state("about:blank", "Blank", "")
        current_y = page_state.get("scroll_y", 0)

        if direction == ScrollDirection.DOWN:
            current_y += amount
        elif direction == ScrollDirection.UP:
            current_y = max(0, current_y - amount)
        elif direction == ScrollDirection.TOP:
            current_y = 0
        elif direction == ScrollDirection.BOTTOM:
            current_y = 2000
        elif direction == ScrollDirection.TO_ELEMENT:
            current_y += 150

        page_state["scroll_y"] = current_y
        self._save_state()
        return ActionResult(
            success=True,
            action_type=BrowserActionType.SCROLL,
            message=f"Scrolled {direction.value} to offset y={current_y}px.",
            data={"scroll_y": current_y, "direction": direction.value},
            duration_ms=4.0,
        )

    def history_action(self, session_id: str, action: HistoryAction) -> PageInfo:
        self._get_session(session_id)
        hist = self._history.get(session_id, ["about:blank"])
        idx = self._history_index.get(session_id, 0)

        if action == HistoryAction.BACK:
            if idx > 0:
                idx -= 1
                self._history_index[session_id] = idx
        elif action == HistoryAction.FORWARD:
            if idx < len(hist) - 1:
                idx += 1
                self._history_index[session_id] = idx
        elif action == HistoryAction.RELOAD:
            pass

        target_url = hist[idx]
        page_state = self._generate_mock_page(target_url)
        self._pages[session_id] = page_state

        session = self._sessions[session_id]
        tab = session.get_active_tab()
        if tab:
            tab.url = target_url
            tab.title = page_state["title"]

        self._save_state()
        return self.get_page_info(session_id)

    def capture_page_screenshot(self, session_id: str) -> bytes:
        self._get_session(session_id)
        # Generate valid 1280x800 deterministic PNG
        width, height = 1280, 800
        png = b"\x89PNG\r\n\x1a\n"
        ihdr_data = (
            width.to_bytes(4, "big")
            + height.to_bytes(4, "big")
            + b"\x08\x02\x00\x00\x00"
        )
        ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
        png += len(ihdr_data).to_bytes(4, "big") + b"IHDR" + ihdr_data + ihdr_crc.to_bytes(4, "big")

        raw_data = bytearray()
        for y in range(height):
            raw_data.append(0)
            for x in range(width):
                r = (x * 255) // width
                g = (y * 255) // height
                b = 128
                raw_data.extend([r, g, b])

        compressed = zlib.compress(bytes(raw_data))
        idat_crc = zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF
        png += len(compressed).to_bytes(4, "big") + b"IDAT" + compressed + idat_crc.to_bytes(4, "big")

        iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
        png += (0).to_bytes(4, "big") + b"IEND" + iend_crc.to_bytes(4, "big")
        return png

    def _get_session(self, session_id: str) -> BrowserSession:
        if session_id not in self._sessions and self.persist_state:
            self._load_state()
        if session_id not in self._sessions:
            raise ToolError(f"Active browser session '{session_id}' not found.")
        session = self._sessions[session_id]
        if session.state == SessionState.CLOSED:
            raise ToolError(f"Browser session '{session_id}' is closed.")
        return session

    def _create_page_state(self, url: str, title: str, text: str) -> Dict[str, Any]:
        return {
            "url": url,
            "title": title,
            "text": text,
            "status_code": 200,
            "scroll_y": 0,
            "elements": [
                WebElement(
                    element_id="elem_home_link",
                    tag_name="a",
                    element_type=ElementType.LINK,
                    text="Home",
                    selector="a#home",
                    attributes={"href": "https://example.com/", "id": "home"},
                    location=ElementLocation(x=20, y=20, width=60, height=25),
                ),
                WebElement(
                    element_id="elem_search_input",
                    tag_name="input",
                    element_type=ElementType.INPUT,
                    text="",
                    selector="input#search",
                    attributes={"id": "search", "name": "q", "placeholder": "Search..."},
                    location=ElementLocation(x=100, y=20, width=240, height=30),
                    value="",
                ),
                WebElement(
                    element_id="elem_submit_btn",
                    tag_name="button",
                    element_type=ElementType.BUTTON,
                    text="Submit",
                    selector="button#submit",
                    attributes={"id": "submit", "type": "submit"},
                    location=ElementLocation(x=350, y=20, width=80, height=30),
                ),
            ],
        }

    def _generate_mock_page(self, url: str) -> Dict[str, Any]:
        if "github.com" in url.lower():
            title = "GitHub: Let's build from here"
            text = "GitHub is where over 100 million developers shape the future of software, together. Repositories, Pull Requests, Issues."
            elements = [
                WebElement(
                    element_id="gh_search",
                    tag_name="input",
                    element_type=ElementType.INPUT,
                    text="",
                    selector="input.header-search",
                    attributes={"id": "gh-search-input", "placeholder": "Search or jump to..."},
                    location=ElementLocation(x=120, y=15, width=280, height=32),
                ),
                WebElement(
                    element_id="gh_signin",
                    tag_name="a",
                    element_type=ElementType.LINK,
                    text="Sign in",
                    selector="a.HeaderMenu-link--sign-in",
                    attributes={"href": "https://github.com/login", "id": "sign-in-link"},
                    location=ElementLocation(x=1150, y=15, width=70, height=30),
                ),
                WebElement(
                    element_id="gh_signup",
                    tag_name="button",
                    element_type=ElementType.BUTTON,
                    text="Sign up for GitHub",
                    selector="button.btn-signup",
                    attributes={"id": "btn-signup"},
                    location=ElementLocation(x=200, y=320, width=180, height=45),
                ),
            ]
        elif "google.com" in url.lower():
            title = "Google"
            text = "Google Search. I'm Feeling Lucky. About, Store, Gmail, Images."
            elements = [
                WebElement(
                    element_id="search_box",
                    tag_name="input",
                    element_type=ElementType.INPUT,
                    text="",
                    selector="input[name='q']",
                    attributes={"name": "q", "id": "q", "placeholder": "Search Google"},
                    location=ElementLocation(x=350, y=250, width=580, height=44),
                ),
                WebElement(
                    element_id="search_btn",
                    tag_name="button",
                    element_type=ElementType.BUTTON,
                    text="Google Search",
                    selector="button#search-btn",
                    attributes={"id": "search-btn"},
                    location=ElementLocation(x=450, y=320, width=130, height=36),
                ),
                WebElement(
                    element_id="lucky_btn",
                    tag_name="button",
                    element_type=ElementType.BUTTON,
                    text="I'm Feeling Lucky",
                    selector="button#lucky-btn",
                    attributes={"id": "lucky-btn"},
                    location=ElementLocation(x=600, y=320, width=150, height=36),
                ),
            ]
        else:
            title = f"Web Page - {url}"
            text = f"Simulated content for {url}. Interactive webpage containing links, articles, forms, and tools."
            elements = [
                WebElement(
                    element_id="nav_home",
                    tag_name="a",
                    element_type=ElementType.LINK,
                    text="Home",
                    selector="nav a.home",
                    attributes={"href": url, "id": "nav-home"},
                    location=ElementLocation(x=50, y=20, width=60, height=24),
                ),
                WebElement(
                    element_id="main_heading",
                    tag_name="h1",
                    element_type=ElementType.HEADING,
                    text="Welcome to " + url,
                    selector="h1",
                    attributes={"id": "heading"},
                    location=ElementLocation(x=50, y=80, width=400, height=40),
                ),
                WebElement(
                    element_id="query_input",
                    tag_name="input",
                    element_type=ElementType.INPUT,
                    text="",
                    selector="input#query",
                    attributes={"id": "query", "placeholder": "Enter search query..."},
                    location=ElementLocation(x=50, y=140, width=320, height=36),
                ),
                WebElement(
                    element_id="action_btn",
                    tag_name="button",
                    element_type=ElementType.BUTTON,
                    text="Search",
                    selector="button#search",
                    attributes={"id": "btn-search"},
                    location=ElementLocation(x=380, y=140, width=90, height=36),
                ),
            ]

        return {
            "url": url,
            "title": title,
            "text": text,
            "status_code": 200,
            "scroll_y": 0,
            "elements": elements,
        }
