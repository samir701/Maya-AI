"""Unit tests for Milestone 08.7 & 08.8 Accessibility and Unified Computer Agent."""

import pytest
from core.zetta.accessibility import (
    AccessibilityAgent,
    AccessibilityCapabilityType,
    AccessibilityManager,
    get_accessibility_manager,
)
from core.zetta.agents.fleet import UnifiedComputerAgent
from shared.types.contracts import SubTask
from shared.types.enums import AgentCapability, PermissionLevel, TaskStatus


class TestAccessibilityAndComputerAgent:
    """Test suite for 25 accessibility capabilities and the UnifiedComputerAgent."""

    def test_accessibility_manager_capabilities_count(self):
        mgr = get_accessibility_manager()
        caps = mgr.list_capabilities()
        assert len(caps) == 25
        assert "find_element" in caps
        assert "click_element" in caps
        assert "type_text" in caps
        assert "scroll_down" in caps
        assert "switch_window" in caps
        assert "describe_accessibility_tree" in caps

    def test_accessibility_manager_actions_execution(self):
        mgr = get_accessibility_manager()

        # Test finding element
        find_res = mgr.execute_action(AccessibilityCapabilityType.FIND_ELEMENT)
        assert find_res.success is True

        # Test typing text
        type_res = mgr.execute_action(AccessibilityCapabilityType.TYPE_TEXT, params={"text": "hello zetta"})
        assert type_res.success is True
        assert type_res.data["typed"] == "hello zetta"

        # Test clipboard copy & paste
        copy_res = mgr.execute_action(AccessibilityCapabilityType.COPY_SELECTION, params={"text": "test copy"})
        assert copy_res.success is True
        paste_res = mgr.execute_action(AccessibilityCapabilityType.PASTE_CLIPBOARD)
        assert paste_res.success is True

        # Test OCR and accessibility tree
        ocr_res = mgr.execute_action(AccessibilityCapabilityType.READ_SCREEN_OCR)
        assert ocr_res.success is True

        tree_res = mgr.execute_action(AccessibilityCapabilityType.DESCRIBE_ACCESSIBILITY_TREE)
        assert tree_res.success is True
        assert "root" in tree_res.data

    def test_accessibility_agent_execution(self):
        agent = AccessibilityAgent(required_permission=PermissionLevel.MEDIUM)
        assert AgentCapability.ACCESSIBILITY in agent.capabilities

        task = SubTask(
            name="Inspect active UI",
            metadata={"action": "describe_accessibility_tree"},
        )
        result = agent.execute(task)

        assert result.success is True
        assert result.data["action"] == "describe_accessibility_tree"
        assert task.status == TaskStatus.COMPLETED

    def test_unified_computer_agent_multi_subsystem_execution(self):
        agent = UnifiedComputerAgent(
            required_permission=PermissionLevel.MEDIUM,
            use_fake=True,
            confirmation_callback=lambda msg: True,
        )
        assert AgentCapability.COMPUTER in agent.capabilities

        task = SubTask(
            name="Multi-subsystem PC inspection",
            required_tools=["system_info", "clipboard_read"],
        )
        result = agent.execute(task)

        assert result.success is True
        assert "system_info" in result.tools_called
        assert "clipboard_read" in result.tools_called
        assert result.data["actions_executed"] == 2
