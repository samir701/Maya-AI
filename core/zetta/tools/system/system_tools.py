"""Safe read-only system tools for ZETTA AI Employee."""

import os
import platform
import shutil
import sys
import time
from typing import Any, Dict
from core.zetta.config import get_settings
from core.zetta.tools.base.base_tool import Tool
from shared.types.enums import PermissionLevel


class SystemInfoTool(Tool):
    """Retrieves host system platform, hardware, and environment details."""

    name = "system_info"
    description = "Retrieves basic operating system, architecture, and environment information."
    required_permission = PermissionLevel.LOW
    category = "system"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "platform": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "python_version": sys.version.split()[0],
            "os_type": "linux",
            "status": "active",
        }


class SystemUptimeTool(Tool):
    """Retrieves system uptime in seconds and formatted duration."""

    name = "system_uptime"
    description = "Returns host system uptime statistics."
    required_permission = PermissionLevel.LOW
    category = "system"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        uptime_seconds = 0.0
        try:
            with open("/proc/uptime", "r") as f:
                uptime_seconds = float(f.readline().split()[0])
        except Exception:
            uptime_seconds = time.clock_gettime(time.CLOCK_BOOTTIME) if hasattr(time, "CLOCK_BOOTTIME") else 0.0

        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)

        return {
            "uptime_seconds": round(uptime_seconds, 2),
            "formatted": f"{hours}h {minutes}m {seconds}s",
        }


class SystemDiskUsageTool(Tool):
    """Retrieves disk usage information for a specified directory path."""

    name = "system_disk_usage"
    description = "Returns disk space usage statistics for a directory or partition path."
    required_permission = PermissionLevel.LOW
    category = "system"
    input_schema = {"path": "Optional path (defaults to root workspace path)"}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        settings = get_settings()
        target_path = input_data.get("path") or str(settings.root_path)

        total, used, free = shutil.disk_usage(target_path)
        percent_used = round((used / total) * 100.0, 2) if total > 0 else 0.0

        return {
            "path": target_path,
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "percent_used": percent_used,
        }


class SystemMemoryUsageTool(Tool):
    """Retrieves RAM memory usage statistics on Linux."""

    name = "system_memory_usage"
    description = "Returns RAM usage statistics (total, available, used, free)."
    required_permission = PermissionLevel.LOW
    category = "system"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        mem_info: Dict[str, int] = {}
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]
                        mem_info[key] = int(val) * 1024  # Convert kB to Bytes
        except Exception:
            pass

        total = mem_info.get("MemTotal", 0)
        available = mem_info.get("MemAvailable", mem_info.get("MemFree", 0))
        used = total - available if total >= available else 0
        percent_used = round((used / total) * 100.0, 2) if total > 0 else 0.0

        return {
            "total_bytes": total,
            "available_bytes": available,
            "used_bytes": used,
            "total_mb": round(total / (1024**2), 2),
            "available_mb": round(available / (1024**2), 2),
            "used_mb": round(used / (1024**2), 2),
            "percent_used": percent_used,
        }


class SystemCpuUsageTool(Tool):
    """Retrieves CPU processor info and system load averages."""

    name = "system_cpu_usage"
    description = "Returns CPU count, load averages, and processor metrics."
    required_permission = PermissionLevel.LOW
    category = "system"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        cpu_count = os.cpu_count() or 1
        load_avg = [0.0, 0.0, 0.0]
        try:
            load_avg = list(os.getloadavg())
        except Exception:
            pass

        return {
            "cpu_count": cpu_count,
            "load_1min": round(load_avg[0], 2),
            "load_5min": round(load_avg[1], 2),
            "load_15min": round(load_avg[2], 2),
        }


class SystemOsInfoTool(Tool):
    """Retrieves detailed operating system and Linux distribution details."""

    name = "system_os_info"
    description = "Returns detailed distribution name, kernel, and desktop environment info."
    required_permission = PermissionLevel.LOW
    category = "system"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        distro_name = "Linux"
        try:
            if hasattr(platform, "freedesktop_os_release"):
                info = platform.freedesktop_os_release()
                distro_name = info.get("PRETTY_NAME", info.get("NAME", "Linux"))
            elif os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            distro_name = line.split("=")[1].strip().strip('"')
                            break
        except Exception:
            pass

        desktop_env = os.getenv("XDG_CURRENT_DESKTOP", os.getenv("DESKTOP_SESSION", "Unknown"))

        return {
            "os_name": distro_name,
            "kernel_version": platform.release(),
            "architecture": platform.machine(),
            "desktop_environment": desktop_env,
        }
