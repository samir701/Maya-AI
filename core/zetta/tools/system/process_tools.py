"""Controlled process inspection and management tools for ZETTA AI Employee."""

import os
import signal
import subprocess
from typing import Any, Dict, List
from core.zetta.tools.base.base_tool import Tool
from shared.types.enums import PermissionLevel


class ProcessListTool(Tool):
    """Lists currently running processes on Linux."""

    name = "process_list"
    description = "Retrieves a list of active running processes with PID, command name, and user."
    required_permission = PermissionLevel.LOW
    category = "system"

    def run(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        limit = input_data.get("limit", 50)
        processes: List[Dict[str, Any]] = []

        try:
            # Run ps aux for portable process listing without external C-extension dependencies
            cmd = ["ps", "-eo", "pid,user,comm,args", "--sort=-rss"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                lines = res.stdout.strip().splitlines()
                header = lines[0] if lines else ""
                for line in lines[1: limit + 1]:
                    parts = line.strip().split(maxsplit=3)
                    if len(parts) >= 3:
                        pid_str, user, comm = parts[0], parts[1], parts[2]
                        args = parts[3] if len(parts) > 3 else comm
                        if pid_str.isdigit():
                            processes.append({
                                "pid": int(pid_str),
                                "user": user,
                                "name": comm,
                                "command": args,
                            })
        except Exception:
            pass

        return processes


class ProcessGetTool(Tool):
    """Retrieves details of a specific process by PID or name."""

    name = "process_get"
    description = "Fetches process details matching a PID or process name."
    required_permission = PermissionLevel.LOW
    category = "system"
    input_schema = {"pid": "Optional process ID", "name": "Optional process name"}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        target_pid = input_data.get("pid")
        target_name = input_data.get("name")

        proc_list_tool = ProcessListTool()
        all_procs = proc_list_tool.run({"limit": 500})

        matches = []
        for p in all_procs:
            if target_pid and p["pid"] == int(target_pid):
                matches.append(p)
            elif target_name and target_name.lower() in p["name"].lower():
                matches.append(p)

        if not matches:
            return {"found": False, "query": input_data, "matches": []}

        return {"found": True, "count": len(matches), "matches": matches}


class ProcessIsRunningTool(Tool):
    """Checks if a process specified by PID or name is currently running."""

    name = "process_is_running"
    description = "Checks whether a process specified by name or PID is running."
    required_permission = PermissionLevel.LOW
    category = "system"
    input_schema = {"name": "Process name", "pid": "Optional process ID"}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        get_tool = ProcessGetTool()
        res = get_tool.run(input_data)
        is_running = res.get("found", False)
        return {
            "is_running": is_running,
            "match_count": len(res.get("matches", [])),
            "matches": res.get("matches", []),
        }


class ProcessStartTool(Tool):
    """Starts a process asynchronously in the background."""

    name = "process_start"
    description = "Starts a specified executable or command as a background process."
    required_permission = PermissionLevel.HIGH
    category = "system"
    input_schema = {"command": "Command line or binary to run", "args": "Optional list of arguments"}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        command = input_data.get("command")
        if not command:
            raise ValueError("Command is required to start a process.")

        args = input_data.get("args", [])
        full_cmd = [command] + args if isinstance(args, list) else [command]

        proc = subprocess.Popen(full_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {
            "started": True,
            "pid": proc.pid,
            "command": full_cmd,
        }


class ProcessStopTool(Tool):
    """Stops a running process by PID or name safely."""

    name = "process_stop"
    description = "Terminates a process by PID or process name. Requires confirmation."
    required_permission = PermissionLevel.HIGH
    category = "system"
    requires_confirmation = True
    dangerous = True
    input_schema = {"pid": "Process ID to stop", "name": "Optional process name"}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pid = input_data.get("pid")
        name = input_data.get("name")

        if pid is None and not name:
            raise ValueError("Either 'pid' or 'name' must be provided to stop a process.")

        target_pids: List[int] = []
        if pid is not None:
            target_pids.append(int(pid))
        elif name:
            get_tool = ProcessGetTool()
            res = get_tool.run({"name": name})
            for m in res.get("matches", []):
                target_pids.append(m["pid"])

        # Prevent killing critical system PIDs (0, 1, 2)
        target_pids = [p for p in target_pids if p > 2 and p != os.getpid()]

        if not target_pids:
            return {"stopped": False, "message": "No matching non-critical target processes found.", "pids": []}

        stopped_pids = []
        for p in target_pids:
            try:
                os.kill(p, signal.SIGTERM)
                stopped_pids.append(p)
            except Exception as e:
                pass

        return {
            "stopped": True if stopped_pids else False,
            "pids": stopped_pids,
            "message": f"Successfully stopped {len(stopped_pids)} process(es).",
        }
