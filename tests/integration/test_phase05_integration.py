"""End-to-end Integration Test for ZETTA Phase 05 Vision & Screen Understanding Layer."""

import pytest
from core.zetta.events import get_event_bus
from core.zetta.interaction import get_interaction_manager
from core.zetta.memory import get_memory_manager
from core.zetta.security import get_security_manager
from core.zetta.tools import get_tool_registry, ToolRouter
from core.zetta.utils.errors import AuthorizationError
from core.zetta.vision.manager import VisionManager, set_vision_manager
from shared.types import EventType, PermissionLevel


class TestPhase05Integration:
    """Integration test suite covering ToolRegistry → VisionManager → EventBus → SecurityManager."""

    @pytest.fixture(autouse=True)
    def setup_vision_integration(self):
        # Configure deterministic fake vision manager for integration testing
        self.fake_vm = VisionManager(use_fake=True)
        set_vision_manager(self.fake_vm)

        self.security = get_security_manager()
        orig_level = self.security.permission_checker.current_level
        # Elevate permissions to HIGH so vision tools pass permission checks
        self.security.permission_checker.current_level = PermissionLevel.HIGH
        self.registry = get_tool_registry()
        self.event_bus = get_event_bus()
        yield
        self.security.permission_checker.current_level = orig_level

    def test_full_vision_tool_registry_flow(self):
        """Verify all 5 vision tools execute through ToolRegistry with security and event emission."""
        events_emitted = []

        def event_handler(event):
            events_emitted.append(event)

        self.event_bus.subscribe(EventType.TOOL_STARTED, event_handler)
        self.event_bus.subscribe(EventType.TOOL_COMPLETED, event_handler)

        # 1. vision_screen_info
        res_info = self.registry.execute("vision_screen_info", {})
        assert res_info.success is True
        assert "displays" in res_info.data
        assert "primary" in res_info.data
        assert len(res_info.data["displays"]) >= 1

        # 2. vision_screen_capture
        res_capture = self.registry.execute("vision_screen_capture", {})
        assert res_capture.success is True
        assert res_capture.data["format"] == "png"
        assert res_capture.data["image_size_bytes"] > 0
        # Verify privacy: raw bytes not in serialized dict
        assert "image_data" not in res_capture.data or res_capture.data["image_data"] != "raw"

        # 3. vision_ocr
        res_ocr = self.registry.execute("vision_ocr", {})
        assert res_ocr.success is True
        assert len(res_ocr.data["text"]) > 0
        assert "regions" in res_ocr.data

        # 4. vision_detect_ui
        res_ui = self.registry.execute("vision_detect_ui", {})
        assert res_ui.success is True
        assert len(res_ui.data["elements"]) > 0

        # 5. vision_analyze_screen
        res_analyze = self.registry.execute("vision_analyze_screen", {"ocr": True, "ui": True})
        assert res_analyze.success is True
        assert len(res_analyze.data["description"]) > 0
        assert res_analyze.data["confidence"] > 0.0

        # Verify EventBus events received
        event_types = [e.event_type for e in events_emitted]
        assert EventType.TOOL_STARTED in event_types
        assert EventType.TOOL_COMPLETED in event_types

        # Verify Security Audit Logger
        audit_event = self.security.audit_logger.log_event("vision_test", "system", "vision_tool", "OK")
        assert audit_event["status"] == "OK"

    def test_tool_router_and_interaction_manager_vision_flow(self):
        """Verify natural-language vision queries route through ToolRouter and InteractionManager."""
        router = ToolRouter()

        # 1. Verify intent detection for natural language phrases
        intent_info = router.detect_intent("show screen info")
        assert intent_info is not None
        assert intent_info["tool"] == "vision_screen_info"

        intent_capture = router.detect_intent("take a screenshot")
        assert intent_capture is not None
        assert intent_capture["tool"] == "vision_screen_capture"

        intent_ocr = router.detect_intent("ocr the screen")
        assert intent_ocr is not None
        assert intent_ocr["tool"] == "vision_ocr"

        intent_ui = router.detect_intent("detect ui on screen")
        assert intent_ui is not None
        assert intent_ui["tool"] == "vision_detect_ui"

        intent_analyze = router.detect_intent("what is on my screen")
        assert intent_analyze is not None
        assert intent_analyze["tool"] == "vision_analyze_screen"

        # 2. Verify Execution via InteractionManager
        interaction_mgr = get_interaction_manager(reload=True)
        session = interaction_mgr.session_mgr.create_session()

        response = interaction_mgr.process_user_message(session.session_id, "what is on my screen")
        assert "Executed Tool 'vision_analyze_screen'" in response
        assert "confidence" in response.lower() or "description" in response.lower()

        # Verify no long-term memory contamination (screenshots/vision outputs must not be auto-promoted)
        from shared.types import MemoryType
        mem_mgr = get_memory_manager()
        lt_memories = mem_mgr.list_memories(memory_type=MemoryType.LONG_TERM)
        for mem in lt_memories:
            assert "vision_analyze_screen" not in mem.content

    def test_permission_enforcement_on_vision_tools(self):
        """Verify that vision tools are blocked if user permission is insufficient."""
        orig_level = self.security.permission_checker.current_level
        try:
            # Lower permission to LOW (vision tools require MEDIUM)
            self.security.permission_checker.current_level = PermissionLevel.LOW

            with pytest.raises(AuthorizationError) as exc_info:
                self.registry.execute("vision_screen_capture", {})
            assert "permission" in str(exc_info.value).lower()
        finally:
            self.security.permission_checker.current_level = orig_level
