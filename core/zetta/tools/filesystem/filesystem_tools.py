"""Controlled local filesystem operations for ZETTA AI Employee."""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.zetta.config import get_settings
from core.zetta.security.sandbox.sandbox import SandboxPolicy
from core.zetta.tools.base.base_tool import Tool
from shared.types.enums import PermissionLevel


def _get_sandbox() -> SandboxPolicy:
    return SandboxPolicy(enabled=get_settings().security.sandbox_enabled)


class FileListTool(Tool):
    """Lists files and subdirectories in a directory path."""

    name = "file_list"
    description = "Lists contents of a target directory within allowed workspace boundaries."
    required_permission = PermissionLevel.LOW
    category = "filesystem"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        settings = get_settings()
        target = input_data.get("path") or str(settings.root_path)

        sandbox = _get_sandbox()
        sandbox.assert_path_safe(target, allow_outside_workspace=False)

        path_obj = Path(target).resolve()
        if not path_obj.exists():
            raise FileNotFoundError(f"Directory '{target}' does not exist.")
        if not path_obj.is_dir():
            raise NotADirectoryError(f"Path '{target}' is not a directory.")

        entries: List[Dict[str, Any]] = []
        for item in path_obj.iterdir():
            try:
                st = item.stat()
                entries.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size_bytes": st.st_size if item.is_file() else 0,
                    "modified_time": st.st_mtime,
                })
            except Exception:
                pass

        entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {
            "directory": str(path_obj),
            "count": len(entries),
            "entries": entries,
        }


class FileExistsTool(Tool):
    """Checks if a file or directory exists at path."""

    name = "file_exists"
    description = "Checks existence and basic metadata of a file or directory path."
    required_permission = PermissionLevel.LOW
    category = "filesystem"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        target = input_data.get("path")
        if not target:
            raise ValueError("Path argument is required.")

        sandbox = _get_sandbox()
        is_safe = sandbox.validate_execution_path(target, allow_outside_workspace=True)
        if not is_safe:
            return {"path": target, "exists": False, "safe": False}

        path_obj = Path(target)
        exists = path_obj.exists()

        info = {
            "path": str(path_obj.resolve()) if exists else target,
            "exists": exists,
            "is_file": path_obj.is_file() if exists else False,
            "is_dir": path_obj.is_dir() if exists else False,
            "size_bytes": path_obj.stat().st_size if (exists and path_obj.is_file()) else 0,
        }
        return info


class FileReadTool(Tool):
    """Reads content from a text file within size limits."""

    name = "file_read"
    description = "Reads text content from a file safely within size and sandbox bounds."
    required_permission = PermissionLevel.MEDIUM
    category = "filesystem"
    input_schema = {"path": "File path to read", "max_bytes": "Optional max bytes to read (default 1048576)"}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        target = input_data.get("path")
        if not target:
            raise ValueError("File path argument is required.")

        sandbox = _get_sandbox()
        sandbox.assert_path_safe(target, allow_outside_workspace=False)

        path_obj = Path(target).resolve()
        if not path_obj.exists():
            raise FileNotFoundError(f"File '{target}' does not exist.")
        if path_obj.is_dir():
            raise IsADirectoryError(f"Target '{target}' is a directory, not a readable file.")

        max_bytes = input_data.get("max_bytes", 1024 * 1024)  # Default 1MB
        st = path_obj.stat()

        if st.st_size > max_bytes:
            # Read truncated portion
            with open(path_obj, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_bytes)
            truncated = True
        else:
            with open(path_obj, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            truncated = False

        return {
            "path": str(path_obj),
            "size_bytes": st.st_size,
            "read_bytes": len(content.encode("utf-8")),
            "truncated": truncated,
            "content": content,
        }


class FileSearchTool(Tool):
    """Searches for files matching a filename pattern or content query."""

    name = "file_search"
    description = "Searches for matching files in a directory tree."
    required_permission = PermissionLevel.MEDIUM
    category = "filesystem"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        settings = get_settings()
        root_path = input_data.get("path") or str(settings.root_path)
        pattern = input_data.get("pattern") or input_data.get("query") or "*"
        max_results = input_data.get("max_results", 50)

        sandbox = _get_sandbox()
        sandbox.assert_path_safe(root_path, allow_outside_workspace=False)

        root_obj = Path(root_path).resolve()
        matches = []

        for p in root_obj.rglob(pattern):
            if len(matches) >= max_results:
                break
            if sandbox.validate_execution_path(str(p), allow_outside_workspace=False):
                matches.append({
                    "name": p.name,
                    "path": str(p),
                    "is_dir": p.is_dir(),
                    "size_bytes": p.stat().st_size if p.is_file() else 0,
                })

        return {
            "root_path": str(root_obj),
            "pattern": pattern,
            "count": len(matches),
            "matches": matches,
        }


class DirectoryCreateTool(Tool):
    """Creates a new directory path safely."""

    name = "directory_create"
    description = "Creates a directory path safely within workspace boundaries."
    required_permission = PermissionLevel.MEDIUM
    category = "filesystem"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        target = input_data.get("path")
        if not target:
            raise ValueError("Directory path argument is required.")

        sandbox = _get_sandbox()
        sandbox.assert_path_safe(target, allow_outside_workspace=False)

        path_obj = Path(target).resolve()
        path_obj.mkdir(parents=True, exist_ok=True)

        return {
            "created": True,
            "path": str(path_obj),
        }


class FileCreateTool(Tool):
    """Creates a new empty or initial file."""

    name = "file_create"
    description = "Creates a new file with initial text content within workspace bounds."
    required_permission = PermissionLevel.MEDIUM
    category = "filesystem"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        target = input_data.get("path")
        content = input_data.get("content", "")
        if not target:
            raise ValueError("File path argument is required.")

        sandbox = _get_sandbox()
        sandbox.assert_path_safe(target, allow_outside_workspace=False)

        path_obj = Path(target).resolve()
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(path_obj, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "created": True,
            "path": str(path_obj),
            "size_bytes": len(content.encode("utf-8")),
        }


class FileWriteTool(Tool):
    """Writes or appends text content to a file safely."""

    name = "file_write"
    description = "Writes text content to a file. Requires confirmation if overwriting."
    required_permission = PermissionLevel.HIGH
    category = "filesystem"
    requires_confirmation = True

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        target = input_data.get("path")
        content = input_data.get("content", "")
        append = input_data.get("append", False)

        if not target:
            raise ValueError("File path argument is required.")

        sandbox = _get_sandbox()
        sandbox.assert_path_safe(target, allow_outside_workspace=False)

        path_obj = Path(target).resolve()
        path_obj.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if append else "w"
        with open(path_obj, mode, encoding="utf-8") as f:
            f.write(content)

        return {
            "written": True,
            "path": str(path_obj),
            "mode": mode,
            "bytes_written": len(content.encode("utf-8")),
        }


class FileCopyTool(Tool):
    """Copies a file or directory from source to destination."""

    name = "file_copy"
    description = "Copies a file or directory tree within workspace boundaries."
    required_permission = PermissionLevel.HIGH
    category = "filesystem"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        src = input_data.get("src_path") or input_data.get("source")
        dest = input_data.get("dest_path") or input_data.get("destination")
        if not src or not dest:
            raise ValueError("Both 'src_path' and 'dest_path' are required.")

        sandbox = _get_sandbox()
        sandbox.assert_path_safe(src, allow_outside_workspace=False)
        sandbox.assert_path_safe(dest, allow_outside_workspace=False)

        src_obj = Path(src).resolve()
        dest_obj = Path(dest).resolve()

        if not src_obj.exists():
            raise FileNotFoundError(f"Source path '{src}' does not exist.")

        if src_obj.is_dir():
            shutil.copytree(src_obj, dest_obj, dirs_exist_ok=True)
        else:
            dest_obj.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_obj, dest_obj)

        return {
            "copied": True,
            "src_path": str(src_obj),
            "dest_path": str(dest_obj),
        }


class FileMoveTool(Tool):
    """Moves a file or directory from source to destination."""

    name = "file_move"
    description = "Moves a file or directory within workspace boundaries."
    required_permission = PermissionLevel.HIGH
    category = "filesystem"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        src = input_data.get("src_path") or input_data.get("source")
        dest = input_data.get("dest_path") or input_data.get("destination")
        if not src or not dest:
            raise ValueError("Both 'src_path' and 'dest_path' are required.")

        sandbox = _get_sandbox()
        sandbox.assert_path_safe(src, allow_outside_workspace=False)
        sandbox.assert_path_safe(dest, allow_outside_workspace=False)

        src_obj = Path(src).resolve()
        dest_obj = Path(dest).resolve()

        if not src_obj.exists():
            raise FileNotFoundError(f"Source path '{src}' does not exist.")

        dest_obj.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_obj), str(dest_obj))

        return {
            "moved": True,
            "src_path": str(src_obj),
            "dest_path": str(dest_obj),
        }


class FileDeleteTool(Tool):
    """Deletes a file or directory safely."""

    name = "file_delete"
    description = "Deletes a file or directory within workspace. Requires confirmation."
    required_permission = PermissionLevel.CRITICAL
    category = "filesystem"
    requires_confirmation = True
    dangerous = True

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        target = input_data.get("path")
        if not target:
            raise ValueError("Path argument is required for file deletion.")

        sandbox = _get_sandbox()
        sandbox.assert_path_safe(target, allow_outside_workspace=False)

        path_obj = Path(target).resolve()
        if not path_obj.exists():
            return {"deleted": False, "path": str(path_obj), "message": "Path does not exist."}

        if path_obj.is_dir():
            shutil.rmtree(path_obj)
        else:
            path_obj.unlink()

        return {
            "deleted": True,
            "path": str(path_obj),
        }
