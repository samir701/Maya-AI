"""Controlled terminal command execution tool for ZETTA AI Employee."""

import os
import re
import shlex
import subprocess
import time
from typing import Any, Dict, List
from core.zetta.config import get_settings
from core.zetta.security.sandbox.sandbox import SandboxPolicy
from core.zetta.security.secrets.secrets import SecretManager
from core.zetta.tools.base.base_tool import Tool
from shared.types.enums import PermissionLevel

DANGEROUS_PATTERNS = [
    re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\b", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\b\s+if=", re.IGNORECASE),
    re.compile(r"\b(shutdown|reboot|poweroff|init\s+0)\b", re.IGNORECASE),
    re.compile(r"\bsudo\b", re.IGNORECASE),
    re.compile(r"\bchmod\s+(-R\s+)?777\s+/", re.IGNORECASE),
    re.compile(r"\bchown\s+-R\b", re.IGNORECASE),
    re.compile(r"\bsystemctl\s+(stop|disable|mask|poweroff|reboot)\b", re.IGNORECASE),
    re.compile(r"\b(apt|apt-get|dpkg|snap|pacman|dnf)\s+(remove|purge|erase)\b", re.IGNORECASE),
]


class TerminalExecuteTool(Tool):
    """Executes bash terminal commands safely with timeouts and output limits."""

    name = "terminal_execute"
    description = "Executes a controlled bash command with sandbox validation, timeout, and output capture."
    required_permission = PermissionLevel.HIGH
    category = "terminal"
    requires_confirmation = True

    def is_dangerous_command(self, command: str) -> bool:
        """Check if command matches high-risk/dangerous pattern rules."""
        for pattern in DANGEROUS_PATTERNS:
            if pattern.search(command):
                return True
        return False

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        command = input_data.get("command")
        if not command or not command.strip():
            raise ValueError("Command string is required for terminal execution.")

        command = command.strip()
        settings = get_settings()
        secret_mgr = SecretManager()
        sandbox = SandboxPolicy(enabled=settings.security.sandbox_enabled)

        # Timeout & output size parameters
        timeout_sec = float(input_data.get("timeout", 30.0))
        timeout_sec = min(max(1.0, timeout_sec), 120.0)
        max_output_kb = int(input_data.get("max_output_kb", 100))
        max_output_bytes = max_output_kb * 1024

        # Working directory
        cwd = input_data.get("cwd") or str(settings.root_path)
        sandbox.assert_path_safe(cwd, allow_outside_workspace=True)

        start_time = time.perf_counter()
        is_dangerous = self.is_dangerous_command(command)

        try:
            # Environment sanitization
            env = os.environ.copy()
            env["PAGER"] = "cat"

            proc = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                env=env,
            )

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            stdout_text = proc.stdout or ""
            stderr_text = proc.stderr or ""
            exit_code = proc.returncode

            # Output size limiting
            truncated = False
            if len(stdout_text.encode("utf-8")) > max_output_bytes:
                stdout_text = stdout_text[:max_output_bytes] + "\n... [stdout truncated due to size limit]"
                truncated = True
            if len(stderr_text.encode("utf-8")) > max_output_bytes:
                stderr_text = stderr_text[:max_output_bytes] + "\n... [stderr truncated due to size limit]"
                truncated = True

            # Secret masking
            stdout_masked = secret_mgr.mask_secrets(stdout_text)
            stderr_masked = secret_mgr.mask_secrets(stderr_text)
            command_masked = secret_mgr.mask_secrets(command)

            return {
                "command": command_masked,
                "exit_code": exit_code,
                "stdout": stdout_masked,
                "stderr": stderr_masked,
                "duration_ms": round(duration_ms, 2),
                "truncated": truncated,
                "dangerous": is_dangerous,
            }

        except subprocess.TimeoutExpired:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            command_masked = secret_mgr.mask_secrets(command)
            return {
                "command": command_masked,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_sec} seconds.",
                "duration_ms": round(duration_ms, 2),
                "truncated": False,
                "dangerous": is_dangerous,
            }
