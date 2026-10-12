"""Local Browser Provider using installed system browsers (Chrome/Chromium/Firefox)."""

import html.parser
import json
import os
import re
import shutil
import signal
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.zetta.browser.drivers.cdp_client import CDPClient
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

logger = get_logger("local_browser_provider")


class SimpleHTMLDOMParser(html.parser.HTMLParser):
    """Lightweight standard library HTML parser to detect interactive elements from DOM dump."""

    def __init__(self) -> None:
        super().__init__()
        self.elements: List[WebElement] = []
        self.text_chunks: List[str] = []
        self.title: str = ""
        self._in_title = False
        self._current_tag: Optional[str] = None
        self._current_attrs: Dict[str, str] = {}
        self._element_counter = 0

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        attr_dict = {k.lower(): v for k, v in attrs if v is not None}
        tag_lower = tag.lower()

        if tag_lower == "title":
            self._in_title = True

        elem_type = ElementType.OTHER
        if tag_lower == "a" and "href" in attr_dict:
            elem_type = ElementType.LINK
        elif tag_lower == "button" or (
            tag_lower == "input" and attr_dict.get("type") in ("button", "submit", "reset")
        ):
            elem_type = ElementType.BUTTON
        elif tag_lower == "input":
            itype = attr_dict.get("type", "text").lower()
            if itype in ("checkbox", "radio"):
                elem_type = ElementType.CHECKBOX if itype == "checkbox" else ElementType.RADIO
            else:
                elem_type = ElementType.INPUT
        elif tag_lower == "textarea":
            elem_type = ElementType.TEXTAREA
        elif tag_lower == "select":
            elem_type = ElementType.SELECT
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            elem_type = ElementType.HEADING
        elif tag_lower == "form":
            elem_type = ElementType.FORM

        if elem_type != ElementType.OTHER:
            self._element_counter += 1
            elem_id = attr_dict.get("id") or f"elem_{tag_lower}_{self._element_counter}"
            selector = (
                f"{tag_lower}#{elem_id}"
                if attr_dict.get("id")
                else f"{tag_lower}[name='{attr_dict.get('name')}']"
                if attr_dict.get("name")
                else tag_lower
            )
            self.elements.append(
                WebElement(
                    element_id=elem_id,
                    tag_name=tag_lower,
                    element_type=elem_type,
                    text="",
                    selector=selector,
                    attributes=attr_dict,
                    location=ElementLocation(
                        x=10 * (self._element_counter % 20),
                        y=30 * self._element_counter,
                        width=150,
                        height=30,
                    ),
                    value=attr_dict.get("value"),
                )
            )

        self._current_tag = tag_lower
        self._current_attrs = attr_dict

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        self._current_tag = None

    def handle_data(self, data: str) -> None:
        clean = data.strip()
        if clean:
            if self._in_title:
                self.title += " " + clean
            else:
                self.text_chunks.append(clean)
                if self.elements and not self.elements[-1].text:
                    self.elements[-1].text = clean


class LocalBrowserProvider(BrowserProvider):
    """Controls real installed system browsers via persistent sessions and CDP automation."""

    KNOWN_BINARIES = [
        ("google-chrome", BrowserType.CHROME),
        ("google-chrome-stable", BrowserType.CHROME),
        ("chromium", BrowserType.CHROMIUM),
        ("chromium-browser", BrowserType.CHROMIUM),
        ("firefox", BrowserType.FIREFOX),
    ]

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
        self._state_file = self.storage_dir / "local_sessions.json"

        self._sessions: Dict[str, BrowserSession] = {}
        self._processes: Dict[str, subprocess.Popen] = {}
        self._cdp_clients: Dict[str, CDPClient] = {}
        self._cached_pages: Dict[str, PageInfo] = {}
        self._active_elements: Dict[str, List[WebElement]] = {}
        self._history: Dict[str, List[str]] = {}
        self._history_index: Dict[str, int] = {}
        self._dead_sessions: set = set()
        self._installed_browsers = self._detect_installed_browsers()

        if self.persist_state:
            self._load_state()

    def _save_state(self) -> None:
        """Persist safe session metadata to disk for cross-process CLI reconnection."""
        if not self.persist_state:
            return
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            serialized_sessions: Dict[str, Any] = {}
            for sid, sess in self._sessions.items():
                active_tab = sess.get_active_tab()
                last_url = active_tab.url if active_tab else "about:blank"
                last_title = active_tab.title if active_tab else "New Tab"
                if sid in self._cached_pages:
                    last_url = self._cached_pages[sid].url
                    last_title = self._cached_pages[sid].title

                serialized_sessions[sid] = {
                    "session_id": sid,
                    "browser_type": sess.browser_type.value,
                    "headless": sess.headless,
                    "state": sess.state.value,
                    "pid": sess.pid,
                    "user_data_dir": sess.user_data_dir,
                    "port": sess.metadata.get("port"),
                    "ws_url": sess.metadata.get("ws_url"),
                    "binary": sess.metadata.get("binary"),
                    "version": sess.metadata.get("version"),
                    "created_at": sess.metadata.get("created_at", time.time()),
                    "last_url": last_url,
                    "last_title": last_title,
                }

            data = {
                "sessions": serialized_sessions,
                "history": self._history,
                "history_index": self._history_index,
            }
            tmp_file = self._state_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp_file.replace(self._state_file)
        except Exception as e:
            logger.warning(f"Failed to save local browser state: {e}")

    def _is_process_alive(self, pid: Optional[int], port: Optional[int]) -> bool:
        """Check whether the Chrome process and its DevTools port are responding."""
        if not pid:
            return False
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, OSError):
            return False

        if port:
            return CDPClient.is_port_responding(port)
        return True

    def _load_state(self) -> None:
        """Load persisted session metadata from disk and clean dead sessions."""
        if not self._state_file.exists():
            return
        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            dirty = False
            sessions_data = data.get("sessions", {})
            for sid, sdata in sessions_data.items():
                pid = sdata.get("pid")
                port = sdata.get("port")
                state_str = sdata.get("state", "active")

                if state_str == SessionState.ACTIVE.value and not self._is_process_alive(pid, port):
                    # Stale / crashed process
                    self._dead_sessions.add(sid)
                    dirty = True
                    continue

                try:
                    b_type = BrowserType(sdata.get("browser_type", "chrome"))
                except Exception:
                    b_type = BrowserType.CHROME

                session = BrowserSession(
                    session_id=sid,
                    browser_type=b_type,
                    headless=sdata.get("headless", True),
                    state=SessionState(state_str) if state_str in [s.value for s in SessionState] else SessionState.ACTIVE,
                    pid=pid,
                    user_data_dir=sdata.get("user_data_dir"),
                    metadata={
                        "binary": sdata.get("binary"),
                        "version": sdata.get("version"),
                        "port": port,
                        "ws_url": sdata.get("ws_url"),
                        "created_at": sdata.get("created_at"),
                    },
                )
                last_url = sdata.get("last_url", "about:blank")
                last_title = sdata.get("last_title", "New Tab")
                active_tab = session.get_active_tab()
                if active_tab:
                    active_tab.url = last_url
                    active_tab.title = last_title

                self._sessions[sid] = session
                self._cached_pages[sid] = PageInfo(
                    url=last_url,
                    title=last_title,
                    visible_text="",
                )

            self._history = data.get("history", {})
            self._history_index = data.get("history_index", {})

            if dirty:
                self._save_state()
        except Exception as e:
            logger.warning(f"Failed to load local browser state: {e}")

    def _detect_installed_browsers(self) -> List[Dict[str, Any]]:
        results = []
        for name, b_type in self.KNOWN_BINARIES:
            bin_path = shutil.which(name)
            if bin_path:
                version = "unknown"
                try:
                    out = subprocess.run([bin_path, "--version"], capture_output=True, text=True, timeout=3)
                    if out.returncode == 0:
                        version = out.stdout.strip()
                except Exception:
                    pass
                results.append({
                    "name": name,
                    "type": b_type.value,
                    "path": bin_path,
                    "version": version,
                    "headless_supported": True,
                    "is_default": len(results) == 0,
                })
        return results

    def is_available(self) -> bool:
        return len(self._installed_browsers) > 0

    def discover_browsers(self) -> List[Dict[str, Any]]:
        return self._installed_browsers.copy()

    def _get_default_binary(self, preferred_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if preferred_type:
            for b in self._installed_browsers:
                if b["type"] == preferred_type:
                    return b
        return self._installed_browsers[0] if self._installed_browsers else None

    def launch_session(self, options: Optional[Dict[str, Any]] = None) -> BrowserSession:
        options = options or {}
        preferred_type = options.get("browser_type")
        browser_info = self._get_default_binary(preferred_type)

        if not browser_info:
            raise ToolError("No supported browser (Chrome, Chromium, Firefox) found on this system.")

        session_id = f"local_browser_{str(uuid.uuid4())[:8]}"
        headless = options.get("headless", True)

        runtime_browser_dir = self.storage_dir / session_id
        runtime_browser_dir.mkdir(parents=True, exist_ok=True)

        binary_path = browser_info["path"]
        cmd = [
            binary_path,
            "--headless=new" if headless and "chrome" in binary_path.lower() else ("--headless" if headless else ""),
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--remote-debugging-port=0",
            f"--user-data-dir={runtime_browser_dir}",
            "about:blank",
        ]
        cmd = [c for c in cmd if c]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._processes[session_id] = proc
        except Exception as e:
            raise ToolError(f"Failed to launch browser executable '{binary_path}': {e}")

        # Wait for DevToolsActivePort file to be generated
        port_file = runtime_browser_dir / "DevToolsActivePort"
        port: Optional[int] = None
        ws_path: Optional[str] = None

        deadline = time.time() + 6.0
        while time.time() < deadline:
            if port_file.exists():
                try:
                    lines = port_file.read_text(encoding="utf-8").splitlines()
                    if lines and lines[0].strip().isdigit():
                        port = int(lines[0].strip())
                        ws_path = lines[1].strip() if len(lines) > 1 else None
                        break
                except Exception:
                    pass
            time.sleep(0.1)

        if not port:
            try:
                proc.terminate()
            except Exception:
                pass
            raise ToolError(f"Browser launched (PID {proc.pid}) but failed to open DevTools port within timeout.")

        ws_url = f"ws://127.0.0.1:{port}{ws_path}" if ws_path else None

        session = BrowserSession(
            session_id=session_id,
            browser_type=BrowserType(browser_info["type"]),
            headless=headless,
            state=SessionState.ACTIVE,
            pid=proc.pid,
            user_data_dir=str(runtime_browser_dir),
            metadata={
                "binary": browser_info["path"],
                "version": browser_info["version"],
                "port": port,
                "ws_url": ws_url,
                "created_at": time.time(),
            },
        )

        self._sessions[session_id] = session
        self._history[session_id] = ["about:blank"]
        self._history_index[session_id] = 0
        self._cached_pages[session_id] = PageInfo(url="about:blank", title="New Tab", visible_text="")
        self._active_elements[session_id] = []

        self._save_state()
        return session

    def _get_cdp_client(self, session: BrowserSession, force_refresh: bool = False) -> CDPClient:
        """Obtain or initialize an active CDP connection for the session."""
        session_id = session.session_id
        if not force_refresh and session_id in self._cdp_clients:
            return self._cdp_clients[session_id]

        if session_id in self._cdp_clients:
            try:
                self._cdp_clients[session_id].close()
            except Exception:
                pass
            self._cdp_clients.pop(session_id, None)

        port = session.metadata.get("port")
        if not port:
            raise ToolError(f"Session '{session_id}' does not have an active DevTools port.")

        cdp = CDPClient(port=port)
        cdp.connect()
        self._cdp_clients[session_id] = cdp
        return cdp

    def close_session(self, session_id: str) -> bool:
        """Close local browser session, terminate Chrome process, and prune storage."""
        if session_id not in self._sessions and self.persist_state:
            self._load_state()

        session = self._sessions.get(session_id)
        if not session:
            return False

        # Close CDP connection
        cdp = self._cdp_clients.pop(session_id, None)
        if cdp:
            cdp.close()

        # Terminate running process
        pid = session.pid
        proc = self._processes.pop(session_id, None)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        elif pid:
            try:
                os.kill(pid, signal.SIGTERM)
                deadline = time.time() + 2.0
                while time.time() < deadline:
                    try:
                        os.kill(pid, 0)
                        time.sleep(0.1)
                    except (ProcessLookupError, OSError):
                        break
                else:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except Exception:
                        pass
            except Exception:
                pass

        session.state = SessionState.CLOSED

        # Clean up temporary user data directory if created
        if session.user_data_dir and os.path.exists(session.user_data_dir):
            try:
                shutil.rmtree(session.user_data_dir, ignore_errors=True)
            except Exception:
                pass

        self._sessions.pop(session_id, None)
        self._cached_pages.pop(session_id, None)
        self._active_elements.pop(session_id, None)
        self._history.pop(session_id, None)
        self._history_index.pop(session_id, None)

        self._save_state()
        return True

    def navigate(self, session_id: str, url: str) -> PageInfo:
        session = self._get_session(session_id)
        clean_url = url.strip() or "about:blank"

        # Update history
        hist = self._history.get(session_id, [])
        idx = self._history_index.get(session_id, 0)
        hist = hist[: idx + 1]
        hist.append(clean_url)
        self._history[session_id] = hist
        self._history_index[session_id] = len(hist) - 1

        tab = session.get_active_tab()
        if tab:
            tab.url = clean_url

        start_time = time.perf_counter()
        cdp = self._get_cdp_client(session)
        cdp.navigate(clean_url)

        # Force refresh live page details and update tab
        page_info = self.get_page_info(session_id, force_refresh=True)
        if clean_url != "about:blank" and not clean_url.endswith("/") and page_info.url == clean_url + "/":
            page_info.url = clean_url
            if tab:
                tab.url = clean_url

        page_info.load_time_ms = (time.perf_counter() - start_time) * 1000

        self._cached_pages[session_id] = page_info
        self._save_state()
        return page_info

    def get_page_info(self, session_id: str, force_refresh: bool = False) -> PageInfo:
        session = self._get_session(session_id)
        try:
            cdp = self._get_cdp_client(session, force_refresh=force_refresh)
            details = cdp.get_page_details()
            parser = SimpleHTMLDOMParser()
            if details.get("html"):
                try:
                    parser.feed(details["html"])
                except Exception:
                    pass

            resolved_url = details.get("url") or "about:blank"
            if (
                session.get_active_tab()
                and session.get_active_tab().url
                and not session.get_active_tab().url.endswith("/")
                and resolved_url == session.get_active_tab().url + "/"
            ):
                resolved_url = session.get_active_tab().url
            title = details.get("title") or parser.title.strip() or "New Tab"
            visible_text = details.get("text") or " ".join(parser.text_chunks)
            elements = parser.elements

            links_count = sum(1 for e in elements if e.element_type == ElementType.LINK)
            buttons_count = sum(1 for e in elements if e.element_type == ElementType.BUTTON)
            inputs_count = sum(1 for e in elements if e.element_type in (ElementType.INPUT, ElementType.TEXTAREA))

            page_info = PageInfo(
                url=resolved_url,
                title=title,
                visible_text=visible_text,
                status_code=200,
                links_count=links_count,
                buttons_count=buttons_count,
                inputs_count=inputs_count,
            )
            self._cached_pages[session_id] = page_info
            self._active_elements[session_id] = elements

            tab = session.get_active_tab()
            if tab:
                tab.url = resolved_url
                tab.title = title

            # Update session metadata with target info
            if cdp._target_id:
                session.metadata["target_id"] = cdp._target_id
            if cdp._ws_url:
                session.metadata["ws_url"] = cdp._ws_url

            self._save_state()
            return page_info

        except Exception as e:
            if not force_refresh:
                try:
                    logger.info(f"Target query failed ({e}); retrying with force_refresh...")
                    return self.get_page_info(session_id, force_refresh=True)
                except Exception as retry_err:
                    e = retry_err

            logger.error(f"Failed to query live page details for session '{session_id}': {e}")
            if session_id in self._cached_pages:
                return self._cached_pages[session_id]
            raise ToolError(f"Failed to query page details for session '{session_id}': {e}")

    def detect_elements(
        self, session_id: str, filter_type: Optional[str] = None
    ) -> List[WebElement]:
        session = self._get_session(session_id)
        if session_id not in self._active_elements or not self._active_elements[session_id]:
            self.get_page_info(session_id)

        elements = self._active_elements.get(session_id, [])
        if filter_type:
            ft = filter_type.lower()
            return [e for e in elements if e.element_type.value.lower() == ft]
        return elements.copy()

    def click(self, session_id: str, target: str) -> ActionResult:
        session = self._get_session(session_id)
        elements = self.detect_elements(session_id)
        target_clean = target.strip()

        matched: Optional[WebElement] = None
        for elem in elements:
            if elem.element_id == target_clean or elem.attributes.get("id") == target_clean or elem.selector == target_clean:
                matched = elem
                break
            if target_clean.lower() in elem.text.lower():
                matched = elem
                break

        if not matched:
            return ActionResult(
                success=False,
                action_type=BrowserActionType.CLICK,
                message=f"Element '{target}' not found on active page.",
                data={"target": target},
            )

        # If it's a link with href, navigate
        if matched.element_type == ElementType.LINK and "href" in matched.attributes:
            href = matched.attributes["href"]
            self.navigate(session_id, href)
            return ActionResult(
                success=True,
                action_type=BrowserActionType.CLICK,
                message=f"Clicked link '{matched.text}', navigating to '{href}'.",
                data={"element": matched.to_dict(), "navigated_to": href},
            )

        try:
            cdp = self._get_cdp_client(session)
            click_js = f"""
            (() => {{
                var el = document.querySelector({json.dumps(matched.selector)});
                if (!el) el = document.getElementById({json.dumps(matched.element_id)});
                if (el) {{
                    el.click();
                    return true;
                }}
                return false;
            }})()
            """
            cdp.evaluate(click_js)
        except Exception as e:
            logger.warning(f"Error triggering click via CDP: {e}")

        return ActionResult(
            success=True,
            action_type=BrowserActionType.CLICK,
            message=f"Clicked element: {matched.to_summary()}",
            data={"element": matched.to_dict()},
        )

    def type_text(
        self, session_id: str, target: str, text: str, clear_first: bool = False
    ) -> ActionResult:
        session = self._get_session(session_id)
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
                message=f"Input element '{target}' not found.",
                data={"target": target},
            )

        try:
            cdp = self._get_cdp_client(session)
            type_js = f"""
            (() => {{
                var el = document.querySelector({json.dumps(matched.selector)});
                if (!el) el = document.getElementById({json.dumps(matched.element_id)});
                if (el) {{
                    if ({'true' if clear_first else 'false'}) el.value = '';
                    el.value += {json.dumps(text)};
                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    el.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return true;
                }}
                return false;
            }})()
            """
            cdp.evaluate(type_js)
        except Exception as e:
            logger.warning(f"Error typing text via CDP: {e}")

        if clear_first:
            matched.value = text
        else:
            matched.value = (matched.value or "") + text

        return ActionResult(
            success=True,
            action_type=BrowserActionType.TYPE,
            message=f"Typed text into {matched.to_summary()}",
            data={"element_id": matched.element_id, "text_length": len(text)},
        )

    def send_keys(self, session_id: str, key: str) -> ActionResult:
        session = self._get_session(session_id)
        key_clean = key.strip()
        try:
            cdp = self._get_cdp_client(session)
            cdp.send_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": key_clean})
            cdp.send_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": key_clean})
        except Exception as e:
            logger.warning(f"Error sending key via CDP: {e}")

        return ActionResult(
            success=True,
            action_type=BrowserActionType.KEYBOARD,
            message=f"Sent keyboard key '{key_clean}' to active page.",
            data={"key": key_clean},
        )

    def scroll(
        self, session_id: str, direction: ScrollDirection, amount: int = 300
    ) -> ActionResult:
        session = self._get_session(session_id)
        scroll_y = 0
        try:
            cdp = self._get_cdp_client(session)
            if direction == ScrollDirection.DOWN:
                expr = f"window.scrollBy(0, {amount}); window.scrollY;"
            elif direction == ScrollDirection.UP:
                expr = f"window.scrollBy(0, -{amount}); window.scrollY;"
            elif direction == ScrollDirection.TOP:
                expr = "window.scrollTo(0, 0); window.scrollY;"
            elif direction == ScrollDirection.BOTTOM:
                expr = "window.scrollTo(0, document.body.scrollHeight || 2000); window.scrollY;"
            else:
                expr = f"window.scrollBy(0, {amount}); window.scrollY;"
            res = cdp.evaluate(expr)
            if isinstance(res, (int, float)):
                scroll_y = int(res)
        except Exception as e:
            logger.warning(f"Error scrolling via CDP: {e}")

        return ActionResult(
            success=True,
            action_type=BrowserActionType.SCROLL,
            message=f"Scrolled {direction.value} to offset y={scroll_y}px.",
            data={"scroll_y": scroll_y, "direction": direction.value},
        )

    def history_action(self, session_id: str, action: HistoryAction) -> PageInfo:
        session = self._get_session(session_id)
        cdp = self._get_cdp_client(session)
        cdp.history_navigate(action.value)

        # Force refresh live page details and update tab
        page_info = self.get_page_info(session_id, force_refresh=True)

        # Sync history index based on action
        hist = self._history.get(session_id, ["about:blank"])
        idx = self._history_index.get(session_id, 0)
        if action == HistoryAction.BACK:
            if idx > 0:
                self._history_index[session_id] = idx - 1
        elif action == HistoryAction.FORWARD:
            if idx < len(hist) - 1:
                self._history_index[session_id] = idx + 1
        elif action == HistoryAction.RELOAD:
            pass

        self._save_state()
        return page_info

    def capture_page_screenshot(self, session_id: str) -> bytes:
        session = self._get_session(session_id)
        try:
            cdp = self._get_cdp_client(session)
            return cdp.capture_screenshot()
        except Exception as e:
            logger.info(f"Screenshot error ({e}); refreshing CDP target connection...")
            cdp = self._get_cdp_client(session, force_refresh=True)
            return cdp.capture_screenshot()

    def _get_session(self, session_id: str) -> BrowserSession:
        if session_id not in self._sessions and self.persist_state:
            self._load_state()

        if session_id not in self._sessions:
            if session_id in self._dead_sessions:
                raise ToolError(f"Browser session '{session_id}' is no longer running.")
            raise ToolError(f"Active browser session '{session_id}' not found.")

        session = self._sessions[session_id]
        # Verify process is still alive
        if not self._is_process_alive(session.pid, session.metadata.get("port")):
            session.state = SessionState.CLOSED
            self._sessions.pop(session_id, None)
            self._save_state()
            raise ToolError(f"Browser session '{session_id}' is no longer running.")

        if session.state == SessionState.CLOSED:
            raise ToolError(f"Browser session '{session_id}' is no longer running.")

        return session
