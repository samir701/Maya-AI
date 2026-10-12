"""Integration Tests for ZETTA Phase 06: Browser & Web Control Subsystem."""

import os
from unittest.mock import MagicMock, patch
import pytest

from core.zetta.browser import (
    BrowserManager,
    BrowserSession,
    FakeBrowserProvider,
    get_browser_manager,
    set_browser_manager,
)
from core.zetta.events import Event, EventBus, get_event_bus
from core.zetta.interaction.manager import InteractionManager
from core.zetta.interaction.session import SessionManager
from core.zetta.security import SecurityManager, get_security_manager
from core.zetta.tools import ToolRegistry, get_tool_registry
from core.zetta.tools.routing import ToolRouter
from core.zetta.vision.manager import VisionManager, get_vision_manager
from shared.types.enums import EventType, PermissionLevel


class TestPhase06Integration:
    """End-to-end integration tests for Browser Subsystem."""

    def setup_method(self):
        self.security = get_security_manager()
        self._orig_level = self.security.permission_checker.current_level
        self.security.permission_checker.current_level = PermissionLevel.HIGH

        self.event_bus = get_event_bus()
        self.registry = get_tool_registry()
        self.router = ToolRouter()

        # Ensure isolated fake browser manager for deterministic tests
        self.fake_bm = BrowserManager(use_fake=True)
        set_browser_manager(self.fake_bm)

        # Captured events list for assertions
        self.captured_events = []
        self.event_bus.subscribe(
            EventType.TOOL_STARTED, lambda ev: self.captured_events.append(ev)
        )
        self.event_bus.subscribe(
            EventType.TOOL_COMPLETED, lambda ev: self.captured_events.append(ev)
        )

    def teardown_method(self):
        self.security.permission_checker.current_level = self._orig_level
        self.fake_bm.close_all()

    def test_tool_registry_to_event_bus_and_security_audit(self):
        """Verify tool execution publishes events to EventBus and logs audit trail."""
        with patch.object(self.security.audit_logger, "log_event", wraps=self.security.audit_logger.log_event) as spy_audit:
            # 1. Execute browser_launch
            res = self.registry.execute("browser_launch", {"headless": True})
            assert res.success is True

            # Check events
            started_events = [e for e in self.captured_events if e.event_type == EventType.TOOL_STARTED]
            completed_events = [e for e in self.captured_events if e.event_type == EventType.TOOL_COMPLETED]
            assert len(started_events) >= 1
            assert len(completed_events) >= 1

            # Check audit log call
            assert spy_audit.called
            calls = [call.kwargs.get("action") or (call.args[0] if call.args else "") for call in spy_audit.call_args_list]
            assert any("tool_execute:browser_launch" in str(c) for c in calls)

    def test_tool_router_detects_and_routes_browser_intents(self):
        """Verify natural-language browser intents map to appropriate tools and execute."""
        # Test intent: browser status
        intent_status = self.router.detect_intent("what browsers are installed")
        assert intent_status is not None
        assert intent_status["tool"] == "browser_status"
        res = self.router.execute_intent(intent_status)
        assert res.success is True

        # Test intent: navigate to URL
        intent_nav = self.router.detect_intent("navigate to https://github.com")
        assert intent_nav is not None
        assert intent_nav["tool"] == "browser_navigate"
        assert intent_nav["arguments"]["url"] == "https://github.com"
        res_nav = self.router.execute_intent(intent_nav)
        assert res_nav.success is True

        # Test intent: read page
        intent_page = self.router.detect_intent("what is on this page")
        assert intent_page is not None
        assert intent_page["tool"] == "browser_get_page"
        res_page = self.router.execute_intent(intent_page)
        assert res_page.success is True

        # Test intent: detect elements
        intent_elem = self.router.detect_intent("find all elements on this page")
        assert intent_elem is not None
        assert intent_elem["tool"] == "browser_detect_elements"
        res_elem = self.router.execute_intent(intent_elem)
        assert res_elem.success is True

        # Test intent: click button
        intent_click = self.router.detect_intent("click button 'gh_signup'")
        assert intent_click is not None
        assert intent_click["tool"] == "browser_click"
        res_click = self.router.execute_intent(intent_click)
        assert res_click.success is True

        # Test intent: type into search
        intent_type = self.router.detect_intent("type 'pytest testing' into gh_search")
        assert intent_type is not None
        assert intent_type["tool"] == "browser_type"
        assert intent_type["arguments"]["text"] == "pytest testing"
        assert intent_type["arguments"]["target"] == "gh_search"
        res_type = self.router.execute_intent(intent_type)
        assert res_type.success is True

        # Test intent: scroll down
        intent_scroll = self.router.detect_intent("scroll down")
        assert intent_scroll is not None
        assert intent_scroll["tool"] == "browser_scroll"
        assert intent_scroll["arguments"]["direction"] == "down"
        res_scroll = self.router.execute_intent(intent_scroll)
        assert res_scroll.success is True

        # Test intent: go back
        intent_back = self.router.detect_intent("go back in browser")
        assert intent_back is not None
        assert intent_back["tool"] == "browser_history"
        assert intent_back["arguments"]["action"] == "back"
        res_back = self.router.execute_intent(intent_back)
        assert res_back.success is True

        # Test intent: close browser
        intent_close = self.router.detect_intent("close the browser")
        assert intent_close is not None
        assert intent_close["tool"] == "browser_close"
        res_close = self.router.execute_intent(intent_close)
        assert res_close.success is True

    def test_interaction_manager_processes_browser_user_message(self):
        """Verify chat interaction manager handles browser queries seamlessly."""
        session_mgr = SessionManager()
        session = session_mgr.create_session()
        im = InteractionManager(session_manager=session_mgr)

        response = im.process_user_message(
            session_id=session.session_id,
            user_input="check browser status",
        )
        assert "Executed Tool 'browser_status'" in response
        assert "FakeBrowserProvider" in response

    def test_vision_manager_and_browser_multimodal_pipeline(self):
        """Verify browser screenshot integrates directly with Phase 05 VisionManager."""
        # 1. Launch browser & navigate to simulated page
        self.fake_bm.launch()
        self.fake_bm.navigate("https://github.com")

        # 2. Capture screenshot via browser manager
        screenshot_data = self.fake_bm.capture_screenshot(save_to_disk=False)
        png_bytes = screenshot_data["image_data"]
        assert len(png_bytes) > 0

        # 3. Pass captured image to VisionManager for visual processing
        vm = VisionManager(use_fake=True)
        from core.zetta.vision.models.results import ScreenCapture
        capture_obj = ScreenCapture(
            image_data=png_bytes,
            width=1280,
            height=800,
            format="png",
            source_display="browser-viewport",
            duration_ms=10.0,
        )

        # Vision OCR on browser screenshot
        ocr_res = vm.perform_ocr(capture_obj)
        assert ocr_res is not None
        assert len(ocr_res.text) > 0

        # Vision UI detection on browser screenshot
        ui_res = vm.detect_ui(capture_obj)
        assert ui_res is not None
        assert len(ui_res.elements) > 0

        # Full screen analysis
        analysis_res = vm.analyze_screen(capture=capture_obj)
        assert analysis_res is not None
        assert "Screen analysis" in analysis_res.description or len(analysis_res.description) > 0
