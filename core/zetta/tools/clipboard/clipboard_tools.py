"""Linux clipboard integration tools for ZETTA AI Employee."""

import shutil
import subprocess
from typing import Any, Dict
from core.zetta.tools.base.base_tool import Tool
from shared.types.enums import PermissionLevel

# In-memory clipboard buffer for graceful fallback when system CLI tools are missing
_IN_MEMORY_CLIPBOARD_BUFFER: str = ""


class ClipboardReadTool(Tool):
    """Reads current text content from the system clipboard."""

    name = "clipboard_read"
    description = "Reads text content from the system clipboard safely."
    required_permission = PermissionLevel.MEDIUM
    category = "clipboard"

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        global _IN_MEMORY_CLIPBOARD_BUFFER

        # Try xclip
        if shutil.which("xclip"):
            try:
                res = subprocess.run(["xclip", "-selection", "clipboard", "-o"], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    return {"text": res.stdout, "available": True, "backend": "xclip"}
            except Exception:
                pass

        # Try xsel
        if shutil.which("xsel"):
            try:
                res = subprocess.run(["xsel", "--clipboard", "--output"], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    return {"text": res.stdout, "available": True, "backend": "xsel"}
            except Exception:
                pass

        # Try wl-paste (Wayland)
        if shutil.which("wl-paste"):
            try:
                res = subprocess.run(["wl-paste"], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    return {"text": res.stdout, "available": True, "backend": "wl-paste"}
            except Exception:
                pass

        # Fallback to in-memory buffer
        return {
            "text": _IN_MEMORY_CLIPBOARD_BUFFER,
            "available": True,
            "backend": "in_memory_fallback",
        }


class ClipboardWriteTool(Tool):
    """Writes text content to the system clipboard."""

    name = "clipboard_write"
    description = "Writes text content to the system clipboard."
    required_permission = PermissionLevel.MEDIUM
    category = "clipboard"
    input_schema = {"text": "Text to write to clipboard"}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        global _IN_MEMORY_CLIPBOARD_BUFFER
        text = input_data.get("text", "")
        _IN_MEMORY_CLIPBOARD_BUFFER = text

        written_backend = "in_memory_fallback"
        success = True

        # Try xclip
        if shutil.which("xclip"):
            try:
                p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, text=True)
                p.communicate(input=text, timeout=3)
                if p.returncode == 0:
                    written_backend = "xclip"
            except Exception:
                pass

        # Try xsel
        elif shutil.which("xsel"):
            try:
                p = subprocess.Popen(["xsel", "--clipboard", "--input"], stdin=subprocess.PIPE, text=True)
                p.communicate(input=text, timeout=3)
                if p.returncode == 0:
                    written_backend = "xsel"
            except Exception:
                pass

        # Try wl-copy (Wayland)
        elif shutil.which("wl-copy"):
            try:
                p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, text=True)
                p.communicate(input=text, timeout=3)
                if p.returncode == 0:
                    written_backend = "wl-copy"
            except Exception:
                pass

        return {
            "written": success,
            "text_length": len(text),
            "backend": written_backend,
        }
