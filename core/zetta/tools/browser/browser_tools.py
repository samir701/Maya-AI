"""Browser Tools for ZETTA Phase 06."""

from typing import Any, Dict, Optional
from core.zetta.browser.manager import get_browser_manager
from core.zetta.tools.base.base_tool import Tool
from shared.types.enums import PermissionLevel


class BrowserStatusTool(Tool):
    """Tool to get status of installed browsers and active sessions."""
    name = "browser_status"
    description = "Discover available web browsers and check active browser sessions."
    required_permission = PermissionLevel.LOW
    category = "browser"

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        return bm.status()


class BrowserLaunchTool(Tool):
    """Tool to launch a browser session."""
    name = "browser_launch"
    description = "Launch and initialize a new browser session (headless or visible)."
    required_permission = PermissionLevel.MEDIUM
    category = "browser"
    input_schema = {
        "type": "object",
        "properties": {
            "browser_type": {"type": "string", "description": "Browser type (chrome, chromium, firefox, fake)"},
            "headless": {"type": "boolean", "default": True, "description": "Whether to run browser in headless mode"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        browser_type = input_data.get("browser_type")
        headless = input_data.get("headless", True)
        session = bm.launch(browser_type=browser_type, headless=headless)
        return session.to_dict()


class BrowserCloseTool(Tool):
    """Tool to close an active browser session."""
    name = "browser_close"
    description = "Close an active browser session and release associated resources."
    required_permission = PermissionLevel.MEDIUM
    category = "browser"
    input_schema = {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Optional session ID to close (defaults to active session)"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        session_id = input_data.get("session_id")
        closed = bm.close(session_id=session_id)
        return {"closed": closed, "session_id": session_id}


class BrowserNavigateTool(Tool):
    """Tool to navigate to a target URL."""
    name = "browser_navigate"
    description = "Navigate browser to a specified website URL."
    required_permission = PermissionLevel.MEDIUM
    category = "browser"
    input_schema = {
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {"type": "string", "description": "Web address to visit (e.g. https://example.com)"},
            "session_id": {"type": "string", "description": "Optional browser session ID"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        url = input_data.get("url", "")
        session_id = input_data.get("session_id")
        page_info = bm.navigate(url=url, session_id=session_id)
        return page_info.to_dict()


class BrowserGetPageTool(Tool):
    """Tool to retrieve active page information."""
    name = "browser_get_page"
    description = "Read current page URL, title, visible text summary, and element counts."
    required_permission = PermissionLevel.LOW
    category = "browser"
    input_schema = {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Optional browser session ID"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        session_id = input_data.get("session_id")
        page_info = bm.get_page_info(session_id=session_id)
        return page_info.to_dict()


class BrowserDetectElementsTool(Tool):
    """Tool to detect interactive elements on the current page."""
    name = "browser_detect_elements"
    description = "Detect clickable buttons, links, inputs, and forms on the current page."
    required_permission = PermissionLevel.LOW
    category = "browser"
    input_schema = {
        "type": "object",
        "properties": {
            "type": {"type": "string", "description": "Optional filter by element type (button, link, input, select, form)"},
            "session_id": {"type": "string", "description": "Optional browser session ID"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        filter_type = input_data.get("type")
        session_id = input_data.get("session_id")
        elements = bm.detect_elements(filter_type=filter_type, session_id=session_id)
        return {
            "count": len(elements),
            "filter_type": filter_type,
            "elements": [e.to_dict() for e in elements],
        }


class BrowserClickTool(Tool):
    """Tool to click an interactive element on the page."""
    name = "browser_click"
    description = "Click on a button, link, or element by its selector, element ID, or visible text."
    required_permission = PermissionLevel.MEDIUM
    category = "browser"
    input_schema = {
        "type": "object",
        "required": ["target"],
        "properties": {
            "target": {"type": "string", "description": "Element ID, CSS selector, or visible text to click"},
            "session_id": {"type": "string", "description": "Optional browser session ID"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        target = input_data.get("target", "")
        session_id = input_data.get("session_id")
        result = bm.click(target=target, session_id=session_id)
        return result.to_dict()


class BrowserTypeTool(Tool):
    """Tool to type text into an input field or textarea."""
    name = "browser_type"
    description = "Type text into a webpage input field, search box, or form textarea."
    required_permission = PermissionLevel.MEDIUM
    category = "browser"
    input_schema = {
        "type": "object",
        "required": ["target", "text"],
        "properties": {
            "target": {"type": "string", "description": "Input element ID, selector, or name"},
            "text": {"type": "string", "description": "Text content to type"},
            "clear_first": {"type": "boolean", "default": False, "description": "Clear existing field value first"},
            "session_id": {"type": "string", "description": "Optional browser session ID"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        target = input_data.get("target", "")
        text = input_data.get("text", "")
        clear_first = input_data.get("clear_first", False)
        session_id = input_data.get("session_id")
        result = bm.type_text(target=target, text=text, clear_first=clear_first, session_id=session_id)
        return result.to_dict()


class BrowserKeyboardTool(Tool):
    """Tool to send keyboard keys or shortcuts to the active webpage."""
    name = "browser_keyboard"
    description = "Send keyboard keys (Enter, Escape, Tab, Backspace, ArrowDown) to the active page."
    required_permission = PermissionLevel.MEDIUM
    category = "browser"
    input_schema = {
        "type": "object",
        "required": ["key"],
        "properties": {
            "key": {"type": "string", "description": "Key name to press (e.g. Enter, Tab, Escape)"},
            "session_id": {"type": "string", "description": "Optional browser session ID"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        key = input_data.get("key", "Enter")
        session_id = input_data.get("session_id")
        result = bm.send_keys(key=key, session_id=session_id)
        return result.to_dict()


class BrowserScrollTool(Tool):
    """Tool to scroll the current webpage."""
    name = "browser_scroll"
    description = "Scroll the active webpage up, down, to top, or to bottom."
    required_permission = PermissionLevel.LOW
    category = "browser"
    input_schema = {
        "type": "object",
        "properties": {
            "direction": {"type": "string", "default": "down", "description": "Scroll direction (up, down, top, bottom)"},
            "amount": {"type": "integer", "default": 300, "description": "Pixel scroll amount"},
            "session_id": {"type": "string", "description": "Optional browser session ID"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        direction = input_data.get("direction", "down")
        amount = int(input_data.get("amount", 300))
        session_id = input_data.get("session_id")
        result = bm.scroll(direction=direction, amount=amount, session_id=session_id)
        return result.to_dict()


class BrowserHistoryTool(Tool):
    """Tool to navigate browser history (back, forward, reload)."""
    name = "browser_history"
    description = "Navigate browser history: go back, go forward, or reload current page."
    required_permission = PermissionLevel.LOW
    category = "browser"
    input_schema = {
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {"type": "string", "description": "History action: back, forward, reload"},
            "session_id": {"type": "string", "description": "Optional browser session ID"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        action = input_data.get("action", "reload")
        session_id = input_data.get("session_id")
        page_info = bm.history(action=action, session_id=session_id)
        return page_info.to_dict()


class BrowserScreenshotTool(Tool):
    """Tool to capture a visual screenshot of the current webpage."""
    name = "browser_screenshot"
    description = "Capture a visual PNG screenshot of the active browser viewport."
    required_permission = PermissionLevel.LOW
    category = "browser"
    input_schema = {
        "type": "object",
        "properties": {
            "save": {"type": "boolean", "default": True, "description": "Whether to save image to runtime/captures/"},
            "session_id": {"type": "string", "description": "Optional browser session ID"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        bm = get_browser_manager()
        save = input_data.get("save", True)
        session_id = input_data.get("session_id")
        capture = bm.capture_screenshot(session_id=session_id, save_to_disk=save)
        # Omit raw byte array from main result to keep logs concise
        return {
            "url": capture["url"],
            "title": capture["title"],
            "bytes_length": capture["bytes_length"],
            "file_path": capture["file_path"],
        }
