"""Unit tests for ZETTA Phase 04 Tools & Local System Control Layer."""

import os
import tempfile
import pytest
from pathlib import Path

from core.zetta.security import get_security_manager
from core.zetta.security.sandbox.sandbox import SandboxPolicy
from core.zetta.tools import get_tool_registry, ToolRouter
from core.zetta.utils.errors import AuthorizationError, SandboxError
from shared.types import PermissionLevel


class TestPhase04Tools:

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        self.registry = get_tool_registry()
        self.security = get_security_manager()
        # Elevate permission to HIGH for tests so allowed tools can run
        self.security.permission_checker.current_level = PermissionLevel.HIGH

    def test_system_info_tools(self):
        res_info = self.registry.execute("system_info", {})
        assert res_info.success is True
        assert res_info.data["os"].lower() == "linux"
        assert "architecture" in res_info.data



        res_uptime = self.registry.execute("system_uptime", {})
        assert res_uptime.success is True
        assert "formatted" in res_uptime.data

        res_disk = self.registry.execute("system_disk_usage", {})
        assert res_disk.success is True
        assert "total_gb" in res_disk.data

        res_mem = self.registry.execute("system_memory_usage", {})
        assert res_mem.success is True
        assert "percent_used" in res_mem.data

        res_cpu = self.registry.execute("system_cpu_usage", {})
        assert res_cpu.success is True
        assert "cpu_count" in res_cpu.data

        res_os = self.registry.execute("system_os_info", {})
        assert res_os.success is True
        assert "kernel_version" in res_os.data

    def test_process_tools(self):
        res_list = self.registry.execute("process_list", {"limit": 10})
        assert res_list.success is True
        assert isinstance(res_list.data, list)
        assert len(res_list.data) > 0

        first_pid = res_list.data[0]["pid"]
        res_get = self.registry.execute("process_get", {"pid": first_pid})
        assert res_get.success is True
        assert res_get.data["found"] is True

        res_running = self.registry.execute("process_is_running", {"pid": first_pid})
        assert res_running.success is True
        assert res_running.data["is_running"] is True

    def test_application_tools(self):
        res_list = self.registry.execute("application_list", {})
        assert res_list.success is True
        assert isinstance(res_list.data, list)

        res_find = self.registry.execute("application_find", {"query": "python"})
        assert res_find.success is True
        assert "matches" in res_find.data

    def test_filesystem_tools_and_sandbox(self):
        with tempfile.TemporaryDirectory(prefix="zetta_phase04_test_") as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test_sample.txt"

            # File create
            res_create = self.registry.execute("file_create", {"path": str(test_file), "content": "Hello ZETTA Phase 04"})
            assert res_create.success is True
            assert test_file.exists()

            # File exists
            res_exists = self.registry.execute("file_exists", {"path": str(test_file)})
            assert res_exists.success is True
            assert res_exists.data["exists"] is True
            assert res_exists.data["is_file"] is True

            # File read
            res_read = self.registry.execute("file_read", {"path": str(test_file)})
            assert res_read.success is True
            assert res_read.data["content"] == "Hello ZETTA Phase 04"

            # File write (with confirmation callback)
            res_write = self.registry.execute(
                "file_write",
                {"path": str(test_file), "content": " - Updated Content", "append": True},
                confirmation_callback=lambda msg: True,
            )
            assert res_write.success is True

            # Re-read
            res_read2 = self.registry.execute("file_read", {"path": str(test_file)})
            assert res_read2.data["content"] == "Hello ZETTA Phase 04 - Updated Content"

            # File search
            res_search = self.registry.execute("file_search", {"path": str(temp_path), "pattern": "*.txt"})
            assert res_search.success is True
            assert res_search.data["count"] >= 1

            # File copy
            copy_file = temp_path / "copy_sample.txt"
            res_copy = self.registry.execute(
                "file_copy",
                {"src_path": str(test_file), "dest_path": str(copy_file)},
                confirmation_callback=lambda msg: True,
            )
            assert res_copy.success is True
            assert copy_file.exists()


            # File move
            moved_file = temp_path / "moved_sample.txt"
            res_move = self.registry.execute(
                "file_move",
                {"src_path": str(copy_file), "dest_path": str(moved_file)},
                confirmation_callback=lambda msg: True,
            )
            assert res_move.success is True
            assert not copy_file.exists()
            assert moved_file.exists()


            # File delete (Requires confirmation & CRITICAL permission level)
            self.security.permission_checker.current_level = PermissionLevel.CRITICAL
            res_del = self.registry.execute(
                "file_delete",
                {"path": str(moved_file)},
                confirmation_callback=lambda msg: True,
            )
            assert res_del.success is True
            assert not moved_file.exists()

    def test_sandbox_protected_paths_blocked(self):
        sandbox = SandboxPolicy(enabled=True)
        assert sandbox.is_system_protected_path("/etc/passwd") is True
        assert sandbox.is_system_protected_path("/sys/kernel") is True
        assert sandbox.is_system_protected_path("/boot/vmlinuz") is True

        with pytest.raises(SandboxError):
            sandbox.assert_path_safe("/etc/shadow")

    def test_terminal_execute_safe_command(self):
        res = self.registry.execute(
            "terminal_execute",
            {"command": "echo 'Hello Terminal'"},
            confirmation_callback=lambda msg: True,
        )
        assert res.success is True
        assert "Hello Terminal" in res.data["stdout"]
        assert res.data["exit_code"] == 0

    def test_terminal_execute_secret_masking(self):
        sec_token = "Bearer test_secret_token_12345"
        self.security.secret_manager.register_secret(sec_token)

        res = self.registry.execute(
            "terminal_execute",
            {"command": f"echo '{sec_token}'"},
            confirmation_callback=lambda msg: True,
        )
        assert res.success is True
        assert sec_token not in res.data["stdout"]
        assert "*****" in res.data["stdout"]

    def test_clipboard_tools(self):
        res_write = self.registry.execute("clipboard_write", {"text": "Phase 04 Clipboard Test"})
        assert res_write.success is True

        res_read = self.registry.execute("clipboard_read", {})
        assert res_read.success is True
        assert "Phase 04 Clipboard Test" in res_read.data["text"]

    def test_permission_denial(self):
        # Drop permission level to LOW
        self.security.permission_checker.current_level = PermissionLevel.LOW

        with pytest.raises(AuthorizationError):
            self.registry.execute("file_write", {"path": "/tmp/test.txt", "content": "fail"})

    def test_rejected_confirmation(self):
        self.security.permission_checker.current_level = PermissionLevel.HIGH

        res = self.registry.execute(
            "file_write",
            {"path": "/tmp/test.txt", "content": "fail"},
            confirmation_callback=lambda msg: False,  # User denies confirmation
        )
        assert res.success is False
        assert res.error.code == "ConfirmationRejected"

    def test_tool_router(self):
        router = ToolRouter()

        intent1 = router.detect_intent("What is my disk usage?")
        assert intent1 is not None
        assert intent1["tool"] == "system_disk_usage"

        intent2 = router.detect_intent('{"tool": "system_info", "arguments": {}}')
        assert intent2 is not None
        assert intent2["tool"] == "system_info"
