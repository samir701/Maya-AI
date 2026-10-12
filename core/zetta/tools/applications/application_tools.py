"""Linux desktop application discovery and control tools for ZETTA AI Employee."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.zetta.tools.base.base_tool import Tool
from shared.types.enums import PermissionLevel


def _discover_desktop_apps() -> List[Dict[str, str]]:
    """Scan standard Linux desktop directories for installed applications."""
    desktop_dirs = [
        Path("/usr/share/applications"),
        Path("/usr/local/share/applications"),
        Path(os.path.expanduser("~/.local/share/applications")),
        Path("/var/lib/snapd/desktop/applications"),
        Path("/var/lib/flatpak/exports/share/applications"),
    ]

    apps: List[Dict[str, str]] = []
    seen_names = set()

    for d in desktop_dirs:
        if not d.exists() or not d.is_dir():
            continue

        for desktop_file in d.glob("*.desktop"):
            try:
                name = None
                exec_cmd = None
                comment = ""
                icon = ""
                nodisplay = False

                with open(desktop_file, "r", encoding="utf-8", errors="ignore") as f:
                    in_entry = False
                    for line in f:
                        line = line.strip()
                        if line == "[Desktop Entry]":
                            in_entry = True
                            continue
                        elif line.startswith("[") and line.endswith("]"):
                            in_entry = False

                        if in_entry and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip()
                            if k == "Name" and not name:
                                name = v
                            elif k == "Exec" and not exec_cmd:
                                exec_cmd = v.split("%")[0].strip()
                            elif k == "Comment" and not comment:
                                comment = v
                            elif k == "Icon" and not icon:
                                icon = v
                            elif k == "NoDisplay" and v.lower() == "true":
                                nodisplay = True

                if name and exec_cmd and not nodisplay:
                    if name not in seen_names:
                        seen_names.add(name)
                        apps.append({
                            "name": name,
                            "exec": exec_cmd,
                            "comment": comment,
                            "icon": icon,
                            "desktop_file": str(desktop_file),
                        })
            except Exception:
                pass

    return apps


class ApplicationListTool(Tool):
    """Lists installed desktop applications discovered on the host system."""

    name = "application_list"
    description = "Scans and lists installed Linux desktop applications (.desktop files)."
    required_permission = PermissionLevel.LOW
    category = "applications"

    def run(self, input_data: Dict[str, Any]) -> List[Dict[str, str]]:
        return _discover_desktop_apps()


class ApplicationFindTool(Tool):
    """Finds installed applications matching a query name or binary."""

    name = "application_find"
    description = "Finds desktop applications or PATH binaries matching a query."
    required_permission = PermissionLevel.LOW
    category = "applications"
    input_schema = {"query": "Application or binary name to search"}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        query = (input_data.get("query") or input_data.get("app_name") or "").lower().strip()
        if not query:
            return {"found": False, "query": query, "matches": []}

        all_apps = _discover_desktop_apps()
        matches = []

        for app in all_apps:
            if query in app["name"].lower() or query in app["exec"].lower():
                matches.append(app)

        # Fallback check if binary exists in system PATH
        path_binary = shutil.which(query)
        if path_binary and not any(m["exec"].startswith(query) for m in matches):
            matches.append({
                "name": query.capitalize(),
                "exec": path_binary,
                "comment": "System PATH executable",
                "icon": "",
                "desktop_file": "",
            })

        return {
            "found": True if matches else False,
            "query": query,
            "count": len(matches),
            "matches": matches,
        }


class ApplicationOpenTool(Tool):
    """Launches a desktop application or binary safely."""

    name = "application_open"
    description = "Opens a desktop application or binary safely in a detached process."
    required_permission = PermissionLevel.MEDIUM
    category = "applications"
    input_schema = {"app_name": "Name or executable of application to open"}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        app_name = input_data.get("app_name") or input_data.get("app") or input_data.get("name")
        if not app_name:
            raise ValueError("Application name ('app_name') is required.")

        finder = ApplicationFindTool()
        res = finder.run({"query": app_name})
        matches = res.get("matches", [])

        exec_cmd = None
        target_name = app_name

        if matches:
            first = matches[0]
            exec_cmd = first["exec"]
            target_name = first["name"]
        else:
            # Check direct binary path
            which_path = shutil.which(app_name)
            if which_path:
                exec_cmd = which_path

        if not exec_cmd:
            raise ValueError(f"Application '{app_name}' could not be found or resolved to an executable binary.")

        # Clean exec command flags (%u, %f, etc.)
        cleaned_cmd = exec_cmd.split("%")[0].strip()
        cmd_args = cleaned_cmd.split()

        proc = subprocess.Popen(
            cmd_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        return {
            "opened": True,
            "app_name": target_name,
            "executable": cleaned_cmd,
            "pid": proc.pid,
        }


class ApplicationIsRunningTool(Tool):
    """Checks if an application process is currently running."""

    name = "application_is_running"
    description = "Checks if an application binary is currently active."
    required_permission = PermissionLevel.LOW
    category = "applications"
    input_schema = {"app_name": "Name of application to check"}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from core.zetta.tools.system.process_tools import ProcessIsRunningTool
        app_name = input_data.get("app_name") or input_data.get("name") or ""
        proc_checker = ProcessIsRunningTool()
        return proc_checker.run({"name": app_name})


class ApplicationCloseTool(Tool):
    """Closes running application instances safely."""

    name = "application_close"
    description = "Gracefully closes running instances of an application. Requires confirmation."
    required_permission = PermissionLevel.HIGH
    category = "applications"
    requires_confirmation = True
    dangerous = True
    input_schema = {"app_name": "Name of application to close"}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from core.zetta.tools.system.process_tools import ProcessStopTool
        app_name = input_data.get("app_name") or input_data.get("name") or ""
        stopper = ProcessStopTool()
        return stopper.run({"name": app_name})
