"""Vision Tools for ZETTA Phase 05."""

from typing import Any, Dict, Optional
from core.zetta.tools.base.base_tool import Tool
from core.zetta.vision.manager import get_vision_manager
from shared.types.enums import PermissionLevel


class VisionScreenInfoTool(Tool):
    """Tool to get information about available displays and primary screen."""
    name = "vision_screen_info"
    description = "Retrieve information about available displays and screen dimensions."
    required_permission = PermissionLevel.LOW
    category = "vision"

    def run(self, input_data: Dict[str, Any]) -> Any:
        vm = get_vision_manager()
        return {
            "displays": [d.to_dict() for d in vm.get_all_displays()],
            "primary": vm.get_screen_info().to_dict(),
        }


class VisionScreenCaptureTool(Tool):
    """Tool to capture a screenshot of the screen."""
    name = "vision_screen_capture"
    description = "Capture a screenshot of the primary display or a specific display."
    required_permission = PermissionLevel.MEDIUM
    category = "vision"
    input_schema = {
        "type": "object",
        "properties": {
            "display_id": {"type": "string", "description": "Optional display ID/name to capture"},
            "save_to_disk": {"type": "boolean", "default": False, "description": "Whether to save capture to disk (default False, keeps in memory)"},
            "task_id": {"type": "string", "description": "Optional task ID requesting screen access"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        from core.zetta.security.screen_access import get_screen_access_manager, ScreenAccessDeniedError
        sam = get_screen_access_manager()
        task_id = input_data.get("task_id")
        save_to_disk = bool(input_data.get("save_to_disk", False))

        if not sam.is_authorized(task_id=task_id):
            authorized = sam.request_interactive_authorization(
                task_id=task_id,
                reason=f"Tool '{self.name}' requested screen capture",
            )
            if not authorized:
                raise ScreenAccessDeniedError("Screen access denied: user authorization required.")

        vm = get_vision_manager()
        display_id = input_data.get("display_id")
        capture = vm.capture_screen(display_id=display_id, save_to_disk=save_to_disk, task_id=task_id)
        return capture.to_dict()


class VisionOCRTool(Tool):
    """Tool to perform OCR on a screen capture."""
    name = "vision_ocr"
    description = "Perform optical character recognition (OCR) on a screenshot."
    required_permission = PermissionLevel.MEDIUM
    category = "vision"
    input_schema = {
        "type": "object",
        "properties": {
            "display_id": {"type": "string", "description": "Display to capture and OCR"},
            "save_to_disk": {"type": "boolean", "default": False, "description": "Whether to save capture to disk (default False)"},
            "task_id": {"type": "string", "description": "Optional task ID requesting screen access"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        from core.zetta.security.screen_access import get_screen_access_manager, ScreenAccessDeniedError
        sam = get_screen_access_manager()
        task_id = input_data.get("task_id")
        save_to_disk = bool(input_data.get("save_to_disk", False))

        if not sam.is_authorized(task_id=task_id):
            authorized = sam.request_interactive_authorization(
                task_id=task_id,
                reason=f"Tool '{self.name}' requested screen capture for OCR",
            )
            if not authorized:
                raise ScreenAccessDeniedError("Screen access denied: user authorization required.")

        vm = get_vision_manager()
        display_id = input_data.get("display_id")
        capture = vm.capture_screen(display_id=display_id, save_to_disk=save_to_disk, task_id=task_id)
        result = vm.perform_ocr(capture)
        return result.to_dict()


class VisionDetectUITool(Tool):
    """Tool to detect UI elements on the screen."""
    name = "vision_detect_ui"
    description = "Detect UI elements (buttons, inputs, links) on the screen."
    required_permission = PermissionLevel.MEDIUM
    category = "vision"
    input_schema = {
        "type": "object",
        "properties": {
            "display_id": {"type": "string", "description": "Display to capture and analyze"},
            "save_to_disk": {"type": "boolean", "default": False, "description": "Whether to save capture to disk (default False)"},
            "task_id": {"type": "string", "description": "Optional task ID requesting screen access"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        from core.zetta.security.screen_access import get_screen_access_manager, ScreenAccessDeniedError
        sam = get_screen_access_manager()
        task_id = input_data.get("task_id")
        save_to_disk = bool(input_data.get("save_to_disk", False))

        if not sam.is_authorized(task_id=task_id):
            authorized = sam.request_interactive_authorization(
                task_id=task_id,
                reason=f"Tool '{self.name}' requested screen capture for UI detection",
            )
            if not authorized:
                raise ScreenAccessDeniedError("Screen access denied: user authorization required.")

        vm = get_vision_manager()
        display_id = input_data.get("display_id")
        capture = vm.capture_screen(display_id=display_id, save_to_disk=save_to_disk, task_id=task_id)
        result = vm.detect_ui(capture)
        return result.to_dict()


class VisionAnalyzeScreenTool(Tool):
    """Tool to perform full vision analysis of the screen."""
    name = "vision_analyze_screen"
    description = "Perform a complete analysis of the screen (Capture + OCR + UI Detection + Analysis)."
    required_permission = PermissionLevel.MEDIUM
    category = "vision"
    input_schema = {
        "type": "object",
        "properties": {
            "display_id": {"type": "string", "description": "Display to analyze"},
            "ocr": {"type": "boolean", "default": True},
            "ui": {"type": "boolean", "default": True},
            "save_to_disk": {"type": "boolean", "default": False, "description": "Whether to save capture to disk (default False)"},
            "task_id": {"type": "string", "description": "Optional task ID requesting screen access"},
        }
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        from core.zetta.security.screen_access import get_screen_access_manager, ScreenAccessDeniedError
        sam = get_screen_access_manager()
        task_id = input_data.get("task_id")
        save_to_disk = bool(input_data.get("save_to_disk", False))

        if not sam.is_authorized(task_id=task_id):
            authorized = sam.request_interactive_authorization(
                task_id=task_id,
                reason=f"Tool '{self.name}' requested screen capture for full screen analysis",
            )
            if not authorized:
                raise ScreenAccessDeniedError("Screen access denied: user authorization required.")

        vm = get_vision_manager()
        display_id = input_data.get("display_id")
        run_ocr = input_data.get("ocr", True)
        run_ui = input_data.get("ui", True)

        analysis = vm.analyze_screen(
            display_id=display_id,
            run_ocr=run_ocr,
            run_ui_detection=run_ui,
            save_to_disk=save_to_disk,
            task_id=task_id,
        )
        return analysis.to_dict()
