"""Tool Intent Router connecting natural language/structured requests to ToolRegistry."""

import json
import re
from typing import Any, Dict, Optional
from core.zetta.tools.registry.registry import get_tool_registry
from shared.types.contracts import ToolResult

# Generic open <app_name> pattern — must be checked AFTER specific patterns
_OPEN_APP_PATTERN = re.compile(r"^(?:please\s+)?open\s+(?:up\s+)?(.+?)\s*(?:for\s+me|now)?$", re.I)


class ToolRouter:
    """Detects and routes tool invocation requests through ToolRegistry."""

    INTENT_PATTERNS = [
        # --- System Info ---
        (re.compile(r"what\s+is\s+my\s+(system|os)\s+(info|information|details)", re.I), "system_info", {}),
        (re.compile(r"show\s+(me\s+)?(my\s+)?system\s+info", re.I), "system_info", {}),
        (re.compile(r"(get|fetch|show)\s+(me\s+)?os\s+(info|details)", re.I), "system_info", {}),

        # --- Disk Usage ---
        (re.compile(r"what\s+is\s+my\s+(disk|storage)\s+usage", re.I), "system_disk_usage", {}),
        (re.compile(r"(check|show|get)\s+(my\s+)?(disk|storage)\s+(usage|space|info)", re.I), "system_disk_usage", {}),
        (re.compile(r"how\s+much\s+(disk|storage|space)\s+(is\s+)?(left|available|used|remaining)", re.I), "system_disk_usage", {}),

        # --- Memory Usage ---
        (re.compile(r"what\s+is\s+my\s+(memory|ram)\s+usage", re.I), "system_memory_usage", {}),
        (re.compile(r"(check|show|get)\s+(my\s+)?(memory|ram)\s+(usage|stats|info)", re.I), "system_memory_usage", {}),
        (re.compile(r"how\s+much\s+(memory|ram)\s+(is\s+)?(used|available|free|left)", re.I), "system_memory_usage", {}),

        # --- CPU Usage ---
        (re.compile(r"what\s+is\s+my\s+cpu\s+usage", re.I), "system_cpu_usage", {}),
        (re.compile(r"(check|show|get)\s+(my\s+)?cpu\s+(usage|load|stats|info)", re.I), "system_cpu_usage", {}),
        (re.compile(r"how\s+(is|much)\s+(is\s+)?the\s+cpu\s+(doing|loaded|used)", re.I), "system_cpu_usage", {}),

        # --- Uptime ---
        (re.compile(r"what\s+is\s+my\s+system\s+uptime", re.I), "system_uptime", {}),
        (re.compile(r"(show|get|check)\s+(me\s+)?(system\s+)?uptime", re.I), "system_uptime", {}),
        (re.compile(r"how\s+long\s+(has\s+)?(the\s+)?system\s+been\s+(up|running)", re.I), "system_uptime", {}),

        # --- Process List ---
        (re.compile(r"what\s+(processes|programs|apps)\s+are\s+running", re.I), "process_list", {}),
        (re.compile(r"(show|list|get)\s+(me\s+)?(running\s+)?(processes|programs|tasks)", re.I), "process_list", {}),

        # --- Application List ---
        (re.compile(r"list\s+(all\s+)?(installed\s+)?applications", re.I), "application_list", {}),
        (re.compile(r"what\s+applications?\s+(are|is)\s+(installed|available)", re.I), "application_list", {}),

        # --- Clipboard ---
        (re.compile(r"(read|get|show|what\s+is)\s+(my\s+)?clipboard", re.I), "clipboard_read", {}),

        # --- File List (Workspace) ---
        (re.compile(r"list\s+(my\s+)?zetta\s+workspace", re.I), "file_list", {}),
        (re.compile(r"(show|list)\s+(me\s+)?my\s+workspace\s+files", re.I), "file_list", {}),

        # --- Specific App Opens (highest priority, checked before generic catch-all) ---
        (re.compile(r"open\s+(vs\s*code|visual\s+studio\s+code)", re.I), "application_open", {"app_name": "code"}),
        (re.compile(r"open\s+(google\s+)?chrome", re.I), "application_open", {"app_name": "google-chrome"}),
        (re.compile(r"open\s+terminal", re.I), "application_open", {"app_name": "gnome-terminal"}),
        (re.compile(r"open\s+files?\s+(?:manager|browser)", re.I), "application_open", {"app_name": "nautilus"}),

        # --- Vision & Screen Understanding (Phase 05) ---
        (re.compile(r"(what|which)\s+(displays|screens|monitors)\s+(do\s+i\s+have|are\s+connected|are\s+available)", re.I), "vision_screen_info", {}),
        (re.compile(r"(show|get|display)\s+(me\s+)?(my\s+)?(screen|display|monitor)\s+info(rmation)?", re.I), "vision_screen_info", {}),
        (re.compile(r"what\s+is\s+my\s+screen\s+resolution", re.I), "vision_screen_info", {}),
        (re.compile(r"take\s+(a\s+)?screenshot", re.I), "vision_screen_capture", {}),
        (re.compile(r"capture\s+(my\s+|the\s+)?(screen|display|monitor)", re.I), "vision_screen_capture", {}),
        (re.compile(r"(screenshot|screencap)\s+(my\s+|the\s+)?(screen|display)?", re.I), "vision_screen_capture", {}),
        (re.compile(r"ocr\s+(the\s+|my\s+)?(screen|display|image)?", re.I), "vision_ocr", {}),
        (re.compile(r"read\s+(the\s+|my\s+)?(text\s+on\s+(the\s+|my\s+)?)?screen", re.I), "vision_ocr", {}),
        (re.compile(r"(extract|recognize|get)\s+text\s+from\s+(the\s+|my\s+)?screen", re.I), "vision_ocr", {}),
        (re.compile(r"detect\s+ui(\s+elements)?(\s+on\s+(the\s+|my\s+)?screen)?", re.I), "vision_detect_ui", {}),
        (re.compile(r"find\s+(the\s+)?(buttons|inputs|links|ui\s+elements)\s+on\s+(the\s+|my\s+)?screen", re.I), "vision_detect_ui", {}),
        (re.compile(r"analyze\s+(the\s+|my\s+)?screen", re.I), "vision_analyze_screen", {}),
        (re.compile(r"what\s+is\s+(currently\s+)?on\s+my\s+screen", re.I), "vision_analyze_screen", {}),
        (re.compile(r"describe\s+(what\s+is\s+on\s+)?(the\s+|my\s+)?screen", re.I), "vision_analyze_screen", {}),

        # --- Browser & Web Control (Phase 06) ---
        (re.compile(r"(what\s+browsers\s+are\s+installed|check\s+browser\s+status|browser\s+status)", re.I), "browser_status", {}),
        (re.compile(r"(launch|start)\s+(the\s+)?browser", re.I), "browser_launch", {}),
        (re.compile(r"(close|exit|quit)\s+(the\s+)?browser", re.I), "browser_close", {}),
        (re.compile(r"(?:navigate\s+to|browse\s+to|open\s+url|go\s+to|visit)\s+(https?://[^\s]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)", re.I), "browser_navigate", lambda m: {"url": m.group(1)}),
        (re.compile(r"(what\s+is\s+on\s+this\s+page|read\s+(the\s+|current\s+)?page|get\s+page\s+info|show\s+page\s+info)", re.I), "browser_get_page", {}),
        (re.compile(r"(?:find|detect)\s+(all\s+)?(elements|buttons|links|inputs)\s+on\s+(the\s+|this\s+)?page", re.I), "browser_detect_elements", {}),
        (re.compile(r"browser\s+detect(\s+elements)?", re.I), "browser_detect_elements", {}),
        (re.compile(r"click\s+(?:on\s+)?(?:button\s+|link\s+)?['\"]?([^'\"]+?)['\"]?$", re.I), "browser_click", lambda m: {"target": m.group(1).strip()}),
        (re.compile(r"type\s+['\"]?(.+?)['\"]?\s+into\s+['\"]?(.+?)['\"]?$", re.I), "browser_type", lambda m: {"text": m.group(1).strip(), "target": m.group(2).strip()}),
        (re.compile(r"scroll\s+(down|up|top|bottom|to\s+top|to\s+bottom)", re.I), "browser_scroll", lambda m: {"direction": m.group(1).replace("to ", "").strip()}),
        (re.compile(r"(?:browser\s+)?(go\s+back|browser\s+back|go\s+forward|browser\s+forward|reload\s+page|refresh\s+page)", re.I), "browser_history", lambda m: {"action": "back" if "back" in m.group(1).lower() else "forward" if "forward" in m.group(1).lower() else "reload"}),
        (re.compile(r"(screenshot|capture)\s+(the\s+|this\s+)?(web\s*page|browser|site)", re.I), "browser_screenshot", {}),

        # --- Real-Time Voice & Audio (Phase 07) ---
        (re.compile(r"(check\s+voice\s+status|voice\s+status|audio\s+status|what\s+audio\s+devices\s+are\s+available)", re.I), "voice_status", {}),
        (re.compile(r"(record\s+(a\s+)?(test\s+)?audio|test\s+(my\s+)?(mic|microphone)|capture\s+audio)", re.I), "voice_capture", {}),
        (re.compile(r"(transcribe\s+audio|speech\s+to\s+text)", re.I), "voice_transcribe", {}),
        (re.compile(r"(?:speak|say)\s+['\"]?(.+?)['\"]?$", re.I), "voice_synthesize", lambda m: {"text": m.group(1).strip()}),
        (re.compile(r"(start\s+(a\s+)?voice\s+session|voice\s+session)", re.I), "voice_session", {"action": "start"}),
    ]

    def parse_structured_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract structured JSON tool intent if present in text."""
        text = text.strip()
        try:
            if text.startswith("{") and text.endswith("}"):
                data = json.loads(text)
                if "tool" in data and isinstance(data["tool"], str):
                    return {
                        "tool": data["tool"],
                        "arguments": data.get("arguments", data.get("input", {})),
                    }
        except Exception:
            pass
        return None

    def detect_intent(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Detect intent from prompt text or structured JSON."""
        structured = self.parse_structured_intent(prompt)
        if structured:
            return structured

        prompt_clean = prompt.strip()

        # Check all specific patterns first
        for pattern, tool_name, args_spec in self.INTENT_PATTERNS:
            match = pattern.search(prompt_clean)
            if match:
                args = args_spec(match) if callable(args_spec) else dict(args_spec)
                return {"tool": tool_name, "arguments": args}

        # Generic catch-all: "open <app_name>"
        open_match = _OPEN_APP_PATTERN.match(prompt_clean)
        if open_match:
            app_name = open_match.group(1).strip()
            # Filter out ambiguous single words that are unlikely app names
            if app_name and len(app_name) >= 2 and app_name.lower() not in ("it", "that", "this", "the", "a", "an"):
                return {"tool": "application_open", "arguments": {"app_name": app_name}}

        return None

    def execute_intent(self, intent: Dict[str, Any]) -> ToolResult:
        """Pass tool intent through ToolRegistry."""
        registry = get_tool_registry()
        tool_name = intent["tool"]
        arguments = intent.get("arguments", {})
        return registry.execute(tool_name, arguments)
