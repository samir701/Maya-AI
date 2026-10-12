"""Comprehensive Unit Tests for ZETTA Phase 06: Browser & Web Control."""

import os
from unittest.mock import MagicMock, patch
import pytest

from core.zetta.browser import (
    ActionResult,
    BrowserActionType,
    BrowserController,
    BrowserManager,
    BrowserProvider,
    BrowserSession,
    BrowserTab,
    BrowserType,
    ElementLocation,
    ElementType,
    FakeBrowserProvider,
    HistoryAction,
    LocalBrowserProvider,
    PageInfo,
    ScrollDirection,
    SessionState,
    WebElement,
    get_browser_manager,
    get_browser_provider,
)
from core.zetta.browser.providers.local import SimpleHTMLDOMParser
from core.zetta.security import get_security_manager
from core.zetta.tools import get_tool_registry
from core.zetta.tools.browser import (
    BrowserClickTool,
    BrowserCloseTool,
    BrowserDetectElementsTool,
    BrowserGetPageTool,
    BrowserHistoryTool,
    BrowserKeyboardTool,
    BrowserLaunchTool,
    BrowserNavigateTool,
    BrowserScreenshotTool,
    BrowserScrollTool,
    BrowserStatusTool,
    BrowserTypeTool,
)
from core.zetta.utils.errors.exceptions import AuthorizationError, ToolError
from shared.types.enums import PermissionLevel


class TestBrowserModels:
    """Tests for browser data models and serialization."""

    def test_browser_tab_defaults_and_to_dict(self):
        tab = BrowserTab(url="https://example.com", title="Example Domain")
        d = tab.to_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Example Domain"
        assert d["is_active"] is True
        assert "tab_id" in d

    def test_browser_session_initializes_with_default_tab(self):
        session = BrowserSession(browser_type=BrowserType.FAKE, headless=True)
        assert len(session.tabs) == 1
        assert session.active_tab_id == session.tabs[0].tab_id
        active_tab = session.get_active_tab()
        assert active_tab is not None
        assert active_tab.url == "about:blank"

        d = session.to_dict()
        assert d["browser_type"] == "fake"
        assert d["headless"] is True
        assert d["state"] == "launching"

    def test_page_info_serialization_and_snippet(self):
        long_text = "Word " * 200
        page = PageInfo(
            url="https://news.ycombinator.com",
            title="Hacker News",
            visible_text=long_text,
            links_count=30,
            buttons_count=2,
            inputs_count=1,
            load_time_ms=45.2,
        )
        d = page.to_dict()
        assert d["url"] == "https://news.ycombinator.com"
        assert d["title"] == "Hacker News"
        assert d["elements_summary"]["links"] == 30
        assert len(d["visible_text_snippet"]) <= 305
        assert d["visible_text_snippet"].endswith("...")

    def test_web_element_models(self):
        elem = WebElement(
            element_id="btn_1",
            tag_name="button",
            element_type=ElementType.BUTTON,
            text="Submit Form",
            selector="button#submit",
            attributes={"id": "submit", "class": "btn-primary"},
            location=ElementLocation(x=10, y=20, width=100, height=35),
        )
        d = elem.to_dict()
        assert d["element_id"] == "btn_1"
        assert d["element_type"] == "button"
        assert d["location"]["x"] == 10

        summary = elem.to_summary()
        assert "[BUTTON]" in summary
        assert "Submit Form" in summary
        assert "(10,20)" in summary

    def test_action_result_model(self):
        res = ActionResult(
            success=True,
            action_type=BrowserActionType.CLICK,
            message="Clicked successfully",
            data={"target": "btn_1"},
            duration_ms=12.4,
        )
        d = res.to_dict()
        assert d["success"] is True
        assert d["action_type"] == "click"
        assert d["duration_ms"] == 12.4


class TestFakeBrowserProvider:
    """Tests for deterministic FakeBrowserProvider."""

    def setup_method(self):
        self.provider = FakeBrowserProvider()

    def test_availability_and_discovery(self):
        assert self.provider.is_available() is True
        browsers = self.provider.discover_browsers()
        assert len(browsers) >= 1
        assert browsers[0]["type"] == "fake"

    def test_session_lifecycle(self):
        session = self.provider.launch_session({"browser_type": "fake", "headless": True})
        assert session.state == SessionState.ACTIVE
        assert session.session_id in self.provider._sessions

        closed = self.provider.close_session(session.session_id)
        assert closed is True
        assert session.state == SessionState.CLOSED

        # Closing non-existent session returns False
        assert self.provider.close_session("invalid_session") is False

    def test_navigation_and_page_info(self):
        session = self.provider.launch_session()
        page = self.provider.navigate(session.session_id, "https://github.com")
        assert page.url == "https://github.com"
        assert "GitHub" in page.title
        assert page.links_count >= 1
        assert page.buttons_count >= 1

        info = self.provider.get_page_info(session.session_id)
        assert info.url == "https://github.com"
        assert info.title == page.title

    def test_detect_elements_and_filtering(self):
        session = self.provider.launch_session()
        self.provider.navigate(session.session_id, "https://google.com")

        all_elements = self.provider.detect_elements(session.session_id)
        assert len(all_elements) >= 3

        inputs = self.provider.detect_elements(session.session_id, filter_type="input")
        assert len(inputs) >= 1
        assert all(e.element_type == ElementType.INPUT for e in inputs)

        buttons = self.provider.detect_elements(session.session_id, filter_type="button")
        assert len(buttons) >= 1
        assert all(e.element_type == ElementType.BUTTON for e in buttons)

    def test_click_element_and_link_navigation(self):
        session = self.provider.launch_session()
        self.provider.navigate(session.session_id, "https://github.com")

        # Click button
        res_btn = self.provider.click(session.session_id, "gh_signup")
        assert res_btn.success is True
        assert "Clicked element" in res_btn.message

        # Click link with navigation
        res_link = self.provider.click(session.session_id, "gh_signin")
        assert res_link.success is True
        assert "navigating" in res_link.message or "navigated" in res_link.message
        # Active tab navigated to login
        tab = session.get_active_tab()
        assert "login" in tab.url

        # Click non-existent element returns failure
        res_fail = self.provider.click(session.session_id, "non_existent_btn")
        assert res_fail.success is False

    def test_type_text(self):
        session = self.provider.launch_session()
        self.provider.navigate(session.session_id, "https://google.com")

        res_type = self.provider.type_text(session.session_id, "search_box", "Python pytest", clear_first=True)
        assert res_type.success is True
        assert "Typed text" in res_type.message

        # Verify value stored
        elements = self.provider.detect_elements(session.session_id, filter_type="input")
        elem = next(e for e in elements if e.element_id == "search_box")
        assert elem.value == "Python pytest"

        # Type again without clear
        self.provider.type_text(session.session_id, "search_box", " test", clear_first=False)
        assert elem.value == "Python pytest test"

    def test_send_keys(self):
        session = self.provider.launch_session()
        res = self.provider.send_keys(session.session_id, "Enter")
        assert res.success is True
        assert "Enter" in res.message

    def test_scroll_and_history(self):
        session = self.provider.launch_session()
        # Scroll down
        res_scroll = self.provider.scroll(session.session_id, ScrollDirection.DOWN, amount=400)
        assert res_scroll.success is True
        assert res_scroll.data["scroll_y"] == 400

        # Scroll up
        res_up = self.provider.scroll(session.session_id, ScrollDirection.UP, amount=150)
        assert res_up.data["scroll_y"] == 250

        # Scroll top
        res_top = self.provider.scroll(session.session_id, ScrollDirection.TOP)
        assert res_top.data["scroll_y"] == 0

        # History: navigate twice then back
        self.provider.navigate(session.session_id, "https://site1.com")
        self.provider.navigate(session.session_id, "https://site2.com")
        assert session.get_active_tab().url == "https://site2.com"

        back_page = self.provider.history_action(session.session_id, HistoryAction.BACK)
        assert back_page.url == "https://site1.com"

        fwd_page = self.provider.history_action(session.session_id, HistoryAction.FORWARD)
        assert fwd_page.url == "https://site2.com"

    def test_capture_page_screenshot_returns_valid_png(self):
        session = self.provider.launch_session()
        png_bytes = self.provider.capture_page_screenshot(session.session_id)
        assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(png_bytes) > 50


class TestLocalBrowserProvider:
    """Tests for LocalBrowserProvider and HTML parser."""

    def test_simple_html_dom_parser(self):
        html_text = """
        <!DOCTYPE html>
        <html>
        <head><title>ZETTA Dashboard</title></head>
        <body>
            <h1>Welcome to ZETTA</h1>
            <p>Empowering autonomous work.</p>
            <a href="https://example.com/docs" id="docs-link">Documentation</a>
            <form action="/submit">
                <input type="text" name="username" id="user-field" placeholder="Enter username">
                <input type="password" name="password" id="pass-field">
                <button type="submit" id="login-btn">Login</button>
            </form>
        </body>
        </html>
        """
        parser = SimpleHTMLDOMParser()
        parser.feed(html_text)

        assert "ZETTA Dashboard" in parser.title
        assert len(parser.elements) >= 5

        headings = [e for e in parser.elements if e.element_type == ElementType.HEADING]
        links = [e for e in parser.elements if e.element_type == ElementType.LINK]
        buttons = [e for e in parser.elements if e.element_type == ElementType.BUTTON]
        inputs = [e for e in parser.elements if e.element_type == ElementType.INPUT]

        assert len(headings) >= 1
        assert len(links) >= 1
        assert len(buttons) >= 1
        assert len(inputs) >= 2

    def test_local_provider_detects_binaries(self):
        provider = LocalBrowserProvider()
        browsers = provider.discover_browsers()
        assert isinstance(browsers, list)
        if provider.is_available():
            assert any("chrome" in b["name"] or "chromium" in b["name"] for b in browsers)

    def test_local_provider_launch_and_close(self):
        provider = LocalBrowserProvider()
        if not provider.is_available():
            pytest.skip("No real browser installed on test environment")

        session = provider.launch_session({"headless": True})
        assert session.state == SessionState.ACTIVE
        assert session.user_data_dir is not None
        assert os.path.exists(session.user_data_dir)

        closed = provider.close_session(session.session_id)
        assert closed is True
        assert not os.path.exists(session.user_data_dir)


class TestBrowserController:
    """Tests for BrowserController URL validation, security, and sessions."""

    def setup_method(self):
        self.provider = FakeBrowserProvider()
        self.controller = BrowserController(self.provider)

    def test_url_validation_safe_schemes(self):
        assert self.controller.validate_url("https://example.com") == "https://example.com"
        assert self.controller.validate_url("http://localhost:8000") == "http://localhost:8000"
        assert self.controller.validate_url("about:blank") == "about:blank"
        # Adds https:// by default
        assert self.controller.validate_url("example.com") == "https://example.com"

    def test_url_validation_blocks_unsafe_schemes(self):
        with pytest.raises(AuthorizationError) as exc:
            self.controller.validate_url("javascript:alert(1)")
        assert "blocked for security reasons" in str(exc.value)

        with pytest.raises(AuthorizationError):
            self.controller.validate_url("vbscript:msgbox")

    def test_url_validation_blocks_file_outside_sandbox(self):
        with pytest.raises(AuthorizationError):
            self.controller.validate_url("file:///etc/passwd")

    def test_auto_launch_default_session(self):
        # Starts with no active sessions
        assert len(self.controller.list_sessions()) == 0
        default_sess = self.controller.get_default_session()
        assert default_sess.state == SessionState.ACTIVE
        assert len(self.controller.list_sessions()) == 1

    def test_sensitive_input_credential_masking(self):
        session = self.controller.get_default_session()
        self.controller.navigate("https://example.com", session_id=session.session_id)

        # Type into field named password
        result = self.controller.type_text(
            target="password_input", text="SuperSecret123!", session_id=session.session_id
        )
        assert result.data.get("redacted") is True
        assert "redacted" in result.message.lower()
        # Secret should not appear in message
        assert "SuperSecret123!" not in result.message


class TestBrowserManager:
    """Tests for BrowserManager facade and singleton."""

    def test_browser_manager_status(self):
        bm = BrowserManager(use_fake=True)
        status = bm.status()
        assert status["provider"] == "FakeBrowserProvider"
        assert status["is_available"] is True
        assert "installed_browsers" in status
        assert status["session_count"] == 0

    def test_browser_manager_screenshot_saves_to_captures(self):
        bm = BrowserManager(use_fake=True)
        bm.launch()
        bm.navigate("https://example.com")
        capture = bm.capture_screenshot(save_to_disk=True)

        assert capture["file_path"] is not None
        assert "runtime/captures" in capture["file_path"]
        assert os.path.exists(capture["file_path"])
        assert capture["bytes_length"] > 0

        # Clean up
        if os.path.exists(capture["file_path"]):
            os.unlink(capture["file_path"])
        bm.close_all()


class TestBrowserTools:
    """Tests for all 12 browser tools registered in ToolRegistry."""

    def setup_method(self):
        self.registry = get_tool_registry()
        self.security = get_security_manager()
        self._orig_level = self.security.permission_checker.current_level
        self.security.permission_checker.current_level = PermissionLevel.HIGH

    def teardown_method(self):
        self.security.permission_checker.current_level = self._orig_level

    def test_all_browser_tools_registered(self):
        expected_tools = [
            "browser_status",
            "browser_launch",
            "browser_close",
            "browser_navigate",
            "browser_get_page",
            "browser_detect_elements",
            "browser_click",
            "browser_type",
            "browser_keyboard",
            "browser_scroll",
            "browser_history",
            "browser_screenshot",
        ]
        registered_names = [t["name"] for t in self.registry.list_tools()]
        for name in expected_tools:
            assert name in registered_names, f"Tool '{name}' should be registered in ToolRegistry"

    def test_tool_permission_levels(self):
        low_tools = [
            "browser_status",
            "browser_get_page",
            "browser_detect_elements",
            "browser_scroll",
            "browser_history",
            "browser_screenshot",
        ]
        med_tools = [
            "browser_launch",
            "browser_close",
            "browser_navigate",
            "browser_click",
            "browser_type",
            "browser_keyboard",
        ]

        for name in low_tools:
            tool = self.registry.get(name)
            assert tool.required_permission == PermissionLevel.LOW, f"{name} should be LOW"
            assert tool.category == "browser"

        for name in med_tools:
            tool = self.registry.get(name)
            assert tool.required_permission == PermissionLevel.MEDIUM, f"{name} should be MEDIUM"
            assert tool.category == "browser"

    def test_browser_tools_execution_lifecycle(self):
        # 1. Check status
        res_status = self.registry.execute("browser_status", {})
        assert res_status.success is True

        # 2. Launch browser
        res_launch = self.registry.execute("browser_launch", {"headless": True})
        assert res_launch.success is True

        # 3. Navigate
        res_nav = self.registry.execute("browser_navigate", {"url": "https://example.com"})
        assert res_nav.success is True
        assert res_nav.data["url"] == "https://example.com"

        # 4. Get page
        res_page = self.registry.execute("browser_get_page", {})
        assert res_page.success is True
        assert res_page.data["url"] == "https://example.com"

        # 5. Detect elements
        res_elem = self.registry.execute("browser_detect_elements", {})
        assert res_elem.success is True
        assert res_elem.data["count"] >= 1

        # 6. Type
        res_type = self.registry.execute("browser_type", {"target": "query_input", "text": "ZETTA"})
        assert res_type.success is True

        # 7. Click
        res_click = self.registry.execute("browser_click", {"target": "action_btn"})
        assert res_click.success is True

        # 8. Keyboard
        res_key = self.registry.execute("browser_keyboard", {"key": "Enter"})
        assert res_key.success is True

        # 9. Scroll
        res_scroll = self.registry.execute("browser_scroll", {"direction": "down", "amount": 200})
        assert res_scroll.success is True

        # 10. History
        res_hist = self.registry.execute("browser_history", {"action": "reload"})
        assert res_hist.success is True

        # 11. Screenshot
        res_shot = self.registry.execute("browser_screenshot", {"save": False})
        assert res_shot.success is True
        assert res_shot.data["bytes_length"] > 0

        # 12. Close
        res_close = self.registry.execute("browser_close", {})
        assert res_close.success is True

    def test_browser_permission_enforcement(self):
        # Drop permission level to LOW
        self.security.permission_checker.current_level = PermissionLevel.LOW

        # LOW tools succeed
        res_status = self.registry.execute("browser_status", {})
        assert res_status.success is True

        # MEDIUM tools raise AuthorizationError from ToolRegistry
        with pytest.raises(AuthorizationError) as exc_info:
            self.registry.execute("browser_navigate", {"url": "https://example.com"})
        assert "exceeds current grant" in str(exc_info.value)


class TestPhase06Regression:
    """Regression tests for Phase 06 manual-test issues."""

    def test_cli_browser_detect_elements_mismatch_fix(self, capsys):
        from core.zetta.cli import handle_browser_cli
        from core.zetta.tools.routing import ToolRouter

        # 1. Test CLI 'browser detect --fake'
        handle_browser_cli(["detect", "--fake"])
        captured = capsys.readouterr()
        assert "Detected" in captured.out
        assert "Unknown browser command" not in captured.out

        # 2. Test CLI 'browser elements --fake' (alias)
        handle_browser_cli(["elements", "--fake"])
        captured_elem = capsys.readouterr()
        assert "Detected" in captured_elem.out

        # 3. Test ToolRouter intent detection for 'browser detect'
        router = ToolRouter()
        intent = router.detect_intent("browser detect")
        assert intent is not None
        assert intent["tool"] == "browser_detect_elements"

        intent_elem = router.detect_intent("find all elements on page")
        assert intent_elem is not None
        assert intent_elem["tool"] == "browser_detect_elements"

    def test_browser_session_persistence_across_manager_instances(self, tmp_path):
        """Simulate separate CLI process invocations preserving fake browser state."""
        # Process 1: Launch session and navigate to GitHub
        bm1 = BrowserManager(use_fake=True, persist_state=True, storage_dir=tmp_path)
        sess1 = bm1.launch(headless=True)
        assert sess1.session_id.startswith("fake_session_")
        nav_page = bm1.navigate("https://github.com")
        assert nav_page.url == "https://github.com"
        assert "GitHub" in nav_page.title

        # Process 2: Read active page without passing session ID (simulating 'browser page --fake')
        bm2 = BrowserManager(use_fake=True, persist_state=True, storage_dir=tmp_path)
        page2 = bm2.get_page_info()
        assert page2.url == "https://github.com"
        assert page2.title == "GitHub: Let's build from here"
        assert page2.url != "about:blank"

        # Process 2: Detect elements on persisted page
        elements = bm2.detect_elements()
        assert len(elements) == 3
        elem_tags = [e.tag_name for e in elements]
        assert "input" in elem_tags
        assert "button" in elem_tags

        # Process 2: Perform scroll action
        bm2.scroll(direction="down", amount=350)

        # Process 3: Verify scroll position was persisted
        bm3 = BrowserManager(use_fake=True, persist_state=True, storage_dir=tmp_path)
        page3 = bm3.get_page_info()
        assert page3.metadata.get("scroll_y") == 350

        # Process 3: Close session
        closed = bm3.close()
        assert closed is True

        # Process 4: Verify default session is no longer active
        bm4 = BrowserManager(use_fake=True, persist_state=True, storage_dir=tmp_path)
        # Calling get_default_session now creates a fresh default session starting at about:blank
        page4 = bm4.get_page_info()
        assert page4.url == "about:blank"

    def test_explicit_session_id_targeting(self, tmp_path):
        """Test targeting explicit sessions via session_id parameter."""
        bm = BrowserManager(use_fake=True, persist_state=True, storage_dir=tmp_path)
        s1 = bm.launch()
        s2 = bm.launch()

        # Navigate independently
        bm.navigate("https://github.com", session_id=s1.session_id)
        bm.navigate("https://google.com", session_id=s2.session_id)

        # In a new instance, target s1 vs s2 explicitly
        bm_new = BrowserManager(use_fake=True, persist_state=True, storage_dir=tmp_path)
        p1 = bm_new.get_page_info(session_id=s1.session_id)
        p2 = bm_new.get_page_info(session_id=s2.session_id)

        assert p1.url == "https://github.com"
        assert "GitHub" in p1.title
        assert p2.url == "https://google.com"
        assert "Google" in p2.title

        # Close s1 explicitly
        bm_new.close(session_id=s1.session_id)
        with pytest.raises(ToolError):
            bm_new.get_page_info(session_id=s1.session_id)

        # s2 is still active
        p2_active = bm_new.get_page_info(session_id=s2.session_id)
        assert p2_active.url == "https://google.com"

    def test_offline_deterministic_isolation_zero_disk_io(self, tmp_path):
        """Verify default FakeBrowserProvider (persist_state=False) performs zero disk I/O."""
        bm = BrowserManager(use_fake=True, persist_state=False, storage_dir=tmp_path)
        bm.launch()
        bm.navigate("https://example.com")
        bm.detect_elements()
        bm.close()

        # Verify no files were created in tmp_path
        created_files = list(tmp_path.iterdir())
        assert len(created_files) == 0


class TestLocalBrowserPersistenceRegression:
    """Regression tests specifically verifying separate-process behavior for LocalBrowserProvider."""

    @pytest.fixture(autouse=True)
    def check_local_browser_available(self):
        prov = LocalBrowserProvider()
        if not prov.is_available():
            pytest.skip("Local Chrome browser not available in this test environment")

    def test_local_launch_new_manager_same_session(self, tmp_path):
        """A. launch -> new manager/process -> page returns the same session ID and initial URL."""
        bm1 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        try:
            sess1 = bm1.launch(headless=True)
            assert sess1.session_id.startswith("local_browser_")

            # New manager instance (simulating separate CLI process)
            bm2 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
            active_sess = bm2.get_active_session()
            assert active_sess is not None
            assert active_sess.session_id == sess1.session_id

            page2 = bm2.get_page_info()
            assert page2.url == "about:blank"
        finally:
            bm1.close_all()

    def test_local_launch_navigate_new_manager_page(self, tmp_path):
        """B. launch -> navigate -> new process -> page."""
        bm1 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        try:
            sess1 = bm1.launch(headless=True)
            nav_page = bm1.navigate("https://example.com")
            assert "Example Domain" in nav_page.title

            # New manager instance
            bm2 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
            page2 = bm2.get_page_info()
            assert page2.url.startswith("https://example.com")
            assert "Example Domain" in page2.title
            assert page2.url != "about:blank"
        finally:
            bm1.close_all()

    def test_local_launch_navigate_new_manager_detect(self, tmp_path):
        """C. launch -> navigate -> new process -> detect."""
        bm1 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        try:
            bm1.launch(headless=True)
            bm1.navigate("https://example.com")

            # New manager instance
            bm2 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
            elements = bm2.detect_elements()
            assert len(elements) >= 1
            links = [e for e in elements if e.element_type == ElementType.LINK]
            assert len(links) >= 1
            assert "iana.org" in str(links[0].attributes.get("href"))
        finally:
            bm1.close_all()

    def test_local_launch_navigate_new_manager_screenshot(self, tmp_path):
        """D. launch -> navigate -> new process -> screenshot."""
        bm1 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        try:
            sess1 = bm1.launch(headless=True)
            bm1.navigate("https://example.com")

            # New manager instance
            bm2 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
            shot = bm2.capture_screenshot(save_to_disk=False)
            assert shot["url"].startswith("https://example.com")
            assert "Example Domain" in shot["title"]
            assert shot["bytes_length"] > 1000
            assert shot["image_data"][:8] == b"\x89PNG\r\n\x1a\n"
        finally:
            bm1.close_all()

    def test_local_explicit_session_targeting(self, tmp_path):
        """E. explicit --session targeting."""
        bm1 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        try:
            s1 = bm1.launch(headless=True)
            bm1.navigate("https://example.com", session_id=s1.session_id)

            # New manager instance explicitly targeting s1
            bm2 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
            p1 = bm2.get_page_info(session_id=s1.session_id)
            assert p1.url.startswith("https://example.com")
            assert "Example Domain" in p1.title

            # Invalid session ID raises ToolError
            with pytest.raises(ToolError) as exc_info:
                bm2.get_page_info(session_id="local_browser_nonexistent")
            assert "not active" in str(exc_info.value).lower()
        finally:
            bm1.close_all()

    def test_local_stale_dead_chrome_session_handling(self, tmp_path):
        """F. stale/dead Chrome session handling cleanly raises ToolError and cleans metadata."""
        import os
        import signal

        bm1 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        sess = bm1.launch(headless=True)
        pid = sess.pid
        session_id = sess.session_id

        # Kill the Chrome process externally
        if pid:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass

        # Allow OS to reap
        import time
        time.sleep(0.5)

        # New manager instance attempts to resolve session
        bm2 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        with pytest.raises(ToolError) as exc_info:
            bm2.get_page_info(session_id=session_id)
        assert "no longer running" in str(exc_info.value).lower()

        # Active session pointer was cleaned
        active_pointer_file = tmp_path / "active_session.txt"
        if active_pointer_file.exists():
            assert active_pointer_file.read_text().strip() != session_id

    def test_local_close_removes_persisted_session_state(self, tmp_path):
        """G. close removes persisted session state and cleans active pointer."""
        bm1 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        sess = bm1.launch(headless=True)
        session_id = sess.session_id

        active_file = tmp_path / "active_session.txt"
        assert active_file.exists()
        assert active_file.read_text().strip() == session_id

        # Close session
        closed = bm1.close(session_id=session_id)
        assert closed is True

        # In a new manager, session is no longer active
        bm2 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        assert bm2.get_active_session() is None
        assert len(bm2.status()["active_sessions"]) == 0

    def test_fake_provider_zero_disk_io_preserved(self, tmp_path):
        """H. fake provider remains zero-disk-I/O by default."""
        bm = BrowserManager(use_fake=True, persist_state=False, storage_dir=tmp_path)
        bm.launch()
        bm.navigate("https://example.com")
        bm.detect_elements()
        bm.close()
        assert len(list(tmp_path.iterdir())) == 0


class TestLocalBrowserCDPNavigationLifecycle:
    """Tests for local Chrome CDP target lifecycle, navigation history, and recovery."""

    def test_local_history_back_reconnects_cdp_target(self, tmp_path):
        """A. launch -> navigate example.com -> history back -> get_page_info. Expected: URL == about:blank."""
        bm = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        try:
            bm.launch(headless=True)
            bm.navigate("https://example.com")
            p_back = bm.history("back")
            assert p_back.url == "about:blank"

            p_page = bm.get_page_info()
            assert p_page.url == "about:blank"
        finally:
            bm.close_all()

    def test_local_history_forward_reconnects_cdp_target(self, tmp_path):
        """B. launch -> navigate example.com -> history back -> history forward -> get_page_info. Expected: URL == https://example.com."""
        bm = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        try:
            bm.launch(headless=True)
            bm.navigate("https://example.com")
            bm.history("back")
            p_fwd = bm.history("forward")
            assert "example.com" in p_fwd.url
            assert "Example Domain" in p_fwd.title

            p_page = bm.get_page_info()
            assert "example.com" in p_page.url
            assert "Example Domain" in p_page.title
        finally:
            bm.close_all()

    def test_local_history_reload_reconnects_cdp_target(self, tmp_path):
        """C. launch -> navigate example.com -> reload -> get_page_info. Expected: URL == https://example.com."""
        bm = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        try:
            bm.launch(headless=True)
            bm.navigate("https://example.com")
            p_reload = bm.history("reload")
            assert "example.com" in p_reload.url
            assert "Example Domain" in p_reload.title

            p_page = bm.get_page_info()
            assert "example.com" in p_page.url
            assert "Example Domain" in p_page.title
        finally:
            bm.close_all()

    def test_local_history_then_screenshot(self, tmp_path):
        """D. history back -> screenshot (about:blank), then history forward -> screenshot (example.com)."""
        bm = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        try:
            bm.launch(headless=True)
            bm.navigate("https://example.com")

            bm.history("back")
            shot_blank = bm.capture_screenshot(save_to_disk=False)
            assert shot_blank["url"] == "about:blank"
            assert shot_blank["bytes_length"] > 500
            assert shot_blank["image_data"][:8] == b"\x89PNG\r\n\x1a\n"

            bm.history("forward")
            shot_example = bm.capture_screenshot(save_to_disk=False)
            assert "example.com" in shot_example["url"]
            assert "Example Domain" in shot_example["title"]
            assert shot_example["bytes_length"] > 1000
            assert shot_example["image_data"][:8] == b"\x89PNG\r\n\x1a\n"
        finally:
            bm.close_all()

    def test_local_history_across_new_manager(self, tmp_path):
        """E. simulate separate CLI processes: Manager A: launch, B: navigate, C: back, D: page, E: forward, F: screenshot."""
        bm1 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        bm1.launch(headless=True)

        try:
            bm2 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
            bm2.navigate("https://example.com")

            bm3 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
            p_back = bm3.history("back")
            assert p_back.url == "about:blank"

            bm4 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
            p_page = bm4.get_page_info()
            assert p_page.url == "about:blank"

            bm5 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
            p_fwd = bm5.history("forward")
            assert "example.com" in p_fwd.url
            assert "Example Domain" in p_fwd.title

            bm6 = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
            shot = bm6.capture_screenshot(save_to_disk=False)
            assert "example.com" in shot["url"]
            assert "Example Domain" in shot["title"]
            assert shot["bytes_length"] > 1000
        finally:
            bm_cleanup = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
            bm_cleanup.close_all()

    def test_local_history_explicit_session_targeting(self, tmp_path):
        """F. two sessions: perform history actions on session A, verify session B is unaffected."""
        bm = BrowserManager(use_fake=False, persist_state=True, storage_dir=tmp_path)
        try:
            sess_a = bm.launch(headless=True)
            sess_b = bm.launch(headless=True)

            bm.navigate("https://example.com", session_id=sess_a.session_id)
            bm.navigate("https://www.iana.org", session_id=sess_b.session_id)

            # Back on session A
            p_a_back = bm.history("back", session_id=sess_a.session_id)
            assert p_a_back.url == "about:blank"

            # Verify session B is untouched
            p_b = bm.get_page_info(session_id=sess_b.session_id)
            assert "iana.org" in p_b.url
            assert "Internet Assigned Numbers Authority" in p_b.title

            # Forward on session A
            p_a_fwd = bm.history("forward", session_id=sess_a.session_id)
            assert "example.com" in p_a_fwd.url

            # Verify session B still untouched
            p_b_after = bm.get_page_info(session_id=sess_b.session_id)
            assert "iana.org" in p_b_after.url
        finally:
            bm.close_all()

    def test_local_stale_cdp_target_recovery(self):
        """G: stale CDP target recovery on 'Inspected target navigated or closed'."""
        from core.zetta.browser.drivers.cdp_client import CDPClient
        import json

        client = CDPClient(port=9999)
        client._sock = MagicMock()

        call_count = 0

        def fake_recv_frame():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return json.dumps({
                    "id": 1,
                    "error": {"message": "Inspected target navigated or closed"}
                })
            return json.dumps({
                "id": 2,
                "result": {"value": "recovered"}
            })

        client._send_frame = MagicMock()
        client._recv_frame = fake_recv_frame
        client.reconnect = MagicMock()

        res = client.send_command("Runtime.evaluate", {"expression": "test()"})
        assert res == {"value": "recovered"}
        assert client.reconnect.call_count == 1





