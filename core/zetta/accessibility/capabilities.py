"""ZETTA 25 Advanced Accessibility and UI Capabilities."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class AccessibilityCapabilityType(str, Enum):
    # Element interaction (1-5)
    FIND_ELEMENT = "find_element"
    READ_ELEMENT = "read_element"
    CLICK_ELEMENT = "click_element"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"

    # Input & typing (6-8)
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    HOTKEY = "hotkey"

    # Navigation & scrolling (9-11)
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"
    SCROLL_TO = "scroll_to"

    # Selection & clipboard (12-14)
    SELECT_TEXT = "select_text"
    COPY_SELECTION = "copy_selection"
    PASTE_CLIPBOARD = "paste_clipboard"

    # Window management (15-18)
    SWITCH_WINDOW = "switch_window"
    CLOSE_WINDOW = "close_window"
    MINIMIZE_WINDOW = "minimize_window"
    MAXIMIZE_WINDOW = "maximize_window"

    # Application control (19-20)
    SWITCH_APPLICATION = "switch_application"
    LAUNCH_APPLICATION = "launch_application"

    # Dialog interaction (21-22)
    CONFIRM_DIALOG = "confirm_dialog"
    DISMISS_DIALOG = "dismiss_dialog"

    # Multimodal Vision & OCR Bridge (23-25)
    READ_SCREEN_OCR = "read_screen_ocr"
    INSPECT_ACTIVE_UI = "inspect_active_ui"
    DESCRIBE_ACCESSIBILITY_TREE = "describe_accessibility_tree"


@dataclass
class AccessibilityActionResult:
    action: AccessibilityCapabilityType
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    details: Dict[str, Any] = None
