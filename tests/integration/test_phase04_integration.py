"""End-to-end Integration Test for ZETTA Phase 04 Local System Control Layer."""

import tempfile
from pathlib import Path
from core.zetta.events import EventBus, get_event_bus
from core.zetta.interaction import get_interaction_manager
from core.zetta.security import get_security_manager
from core.zetta.tools import get_tool_registry
from shared.types import EventType, PermissionLevel


class TestPhase04Integration:

    def test_full_phase04_control_flow(self):
        security = get_security_manager()
        security.permission_checker.current_level = PermissionLevel.HIGH

        event_bus = get_event_bus()
        events_received = []

        def handle_event(event):
            events_received.append(event.event_type)

        event_bus.subscribe(EventType.TOOL_STARTED, handle_event)
        event_bus.subscribe(EventType.TOOL_COMPLETED, handle_event)
        event_bus.subscribe(EventType.USER_MESSAGE_RECEIVED, handle_event)
        event_bus.subscribe(EventType.ASSISTANT_RESPONSE_GENERATED, handle_event)

        interaction_mgr = get_interaction_manager(reload=True)
        session = interaction_mgr.session_mgr.create_session()

        # 1. System info intent query
        resp = interaction_mgr.process_user_message(session.session_id, "What is my system information?")
        assert "Executed Tool 'system_info'" in resp
        assert "linux" in resp.lower()

        # 2. Disk usage intent query
        resp_disk = interaction_mgr.process_user_message(session.session_id, "What is my disk usage?")
        assert "Executed Tool 'system_disk_usage'" in resp_disk
        assert "total_gb" in resp_disk


        # 3. Direct ToolRegistry execution flow
        registry = get_tool_registry()
        res_mem = registry.execute("system_memory_usage", {})
        assert res_mem.success is True
        assert "percent_used" in res_mem.data

        # 4. Verify EventBus integration
        assert EventType.TOOL_STARTED in events_received
        assert EventType.TOOL_COMPLETED in events_received
        assert EventType.USER_MESSAGE_RECEIVED in events_received
        assert EventType.ASSISTANT_RESPONSE_GENERATED in events_received

        # 5. Verify Security Audit Logger
        audit_events = security.audit_logger.log_event("test", "test", "test", "OK")
        assert audit_events["status"] == "OK"
