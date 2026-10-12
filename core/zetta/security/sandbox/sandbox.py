"""ZETTA Sandbox Execution Policy."""

import os
from pathlib import Path
from typing import List, Optional
from core.zetta.config import get_settings
from core.zetta.utils.errors import SandboxError


class SandboxPolicy:
    """Enforces execution boundaries for plugins, tools, scripts, and filesystem operations."""

    PROTECTED_SYSTEM_PATHS: List[str] = [
        "/etc",
        "/boot",
        "/root",
        "/usr",
        "/bin",
        "/sbin",
        "/var",
        "/sys",
        "/proc",
        "/dev",
        "/lib",
        "/lib64",
    ]

    def __init__(self, enabled: bool = True, workspace_path: Optional[str] = None) -> None:
        self.enabled = enabled
        settings = get_settings()
        self.workspace_path = Path(workspace_path or settings.root_path).resolve()

    def is_system_protected_path(self, target_path: str) -> bool:
        """Check if target path is a critical OS system path."""
        try:
            resolved = Path(target_path).resolve()
            resolved_str = str(resolved)
            for protected in self.PROTECTED_SYSTEM_PATHS:
                if resolved_str == protected or resolved_str.startswith(protected + "/"):
                    return True
            return False
        except Exception:
            return True

    def validate_execution_path(self, target_path: str, allow_outside_workspace: bool = False) -> bool:
        """Check if target path is safe and within sandbox boundaries."""
        if not self.enabled:
            return True

        if self.is_system_protected_path(target_path):
            return False

        if not allow_outside_workspace:
            try:
                resolved = Path(target_path).resolve()
                # Ensure target is under workspace or workspace is target
                if not (resolved == self.workspace_path or self.workspace_path in resolved.parents):
                    # Check if user explicitly allowed temp directories for testing
                    temp_dir = Path("/tmp").resolve()
                    if temp_dir in resolved.parents or resolved == temp_dir:
                        return True
                    return False
            except Exception:
                return False

        return True

    def assert_path_safe(self, target_path: str, allow_outside_workspace: bool = False) -> None:
        """Raise SandboxError if path is unsafe."""
        if not self.validate_execution_path(target_path, allow_outside_workspace=allow_outside_workspace):
            raise SandboxError(f"Path '{target_path}' violates sandbox policy or accesses protected system resources.")

