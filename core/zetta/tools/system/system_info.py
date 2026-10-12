"""SystemInfoTool sample implementation for Phase 00 tool verification."""

import platform
import sys
from typing import Any, Dict
from core.zetta.tools.base.base_tool import Tool
from shared.types.enums import PermissionLevel


class SystemInfoTool(Tool):
    """Simple test tool returning basic host system details."""

    name = "system_info"
    description = "Retrieves basic operating system and Python environment information."
    required_permission = PermissionLevel.LOW

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": sys.version.split()[0],
            "status": "active",
        }
