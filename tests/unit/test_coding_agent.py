"""Unit tests for Milestone 08.6 Coding Agent."""

import tempfile
from pathlib import Path
import pytest
from core.zetta.agents.fleet import CodingAgent
from shared.types.contracts import SubTask
from shared.types.enums import AgentCapability, PermissionLevel, TaskStatus


class TestCodingAgent:
    """Test suite for CodingAgent inspection, modification, and test verification."""

    def test_coding_agent_initialization(self):
        agent = CodingAgent(required_permission=PermissionLevel.MEDIUM)
        assert agent.name == "CodingAgent"
        assert AgentCapability.CODING in agent.capabilities
        assert agent.max_repair_attempts == 2

    def test_workspace_boundary_protection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = CodingAgent(
                required_permission=PermissionLevel.MEDIUM,
                workspace_root=Path(tmpdir),
            )
            # Valid path within workspace
            valid_path = agent._validate_path("src/module.py")
            assert str(valid_path).startswith(str(Path(tmpdir).resolve()))

            # Invalid path escaping workspace via traversal
            with pytest.raises(PermissionError, match="outside approved workspace root"):
                agent._validate_path("../../etc/passwd")

    def test_coding_workflow_execution(self):
        from core.zetta.security import get_security_manager
        sec_mgr = get_security_manager()
        orig = sec_mgr.permission_checker.current_level
        sec_mgr.permission_checker.current_level = PermissionLevel.HIGH
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                sample_file = root / "calculator.py"
                sample_file.write_text("def add(a, b): return a + b\n")

                agent = CodingAgent(
                    required_permission=PermissionLevel.HIGH,
                    workspace_root=root,
                    confirmation_callback=lambda msg: True,
                )
                task = SubTask(
                    name="Add multiply function",
                    description="Implement multiplication in calculator",
                    metadata={"target_file": str(sample_file)},
                )
                result = agent.execute(task)

                assert result.success is True
                assert "file_read" in result.tools_called
                assert "file_write" in result.tools_called
                assert str(sample_file) in result.data["modified_files"]
        finally:
            sec_mgr.permission_checker.current_level = orig

    def test_coding_workflow_with_verification_test(self):
        from core.zetta.security import get_security_manager
        sec_mgr = get_security_manager()
        orig = sec_mgr.permission_checker.current_level
        sec_mgr.permission_checker.current_level = PermissionLevel.HIGH
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                agent = CodingAgent(
                    required_permission=PermissionLevel.HIGH,
                    workspace_root=root,
                    confirmation_callback=lambda msg: True,
                )
                task = SubTask(
                    name="Run build sanity check",
                    description="Run echo test",
                    metadata={"test_command": "echo 'TESTS_PASSED'"},
                )
                result = agent.execute(task)

                assert result.success is True
                assert result.data["verified"] is True
                assert "terminal_execute" in result.tools_called
        finally:
            sec_mgr.permission_checker.current_level = orig
