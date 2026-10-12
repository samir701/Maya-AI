"""Computer Control & Accessibility routes."""

import base64
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.zetta.accessibility import get_accessibility_manager
from core.zetta.vision import get_vision_manager

router = APIRouter(prefix="/api/computer", tags=["Computer"])


class ComputerActionRequest(BaseModel):
    action: str  # click, double_click, type_text, press_key, switch_window, etc.
    parameters: Optional[Dict[str, Any]] = None


@router.get("/status")
def get_computer_status():
    """Get active desktop information and accessibility readiness."""
    vm = get_vision_manager()
    am = get_accessibility_manager()
    try:
        displays = vm.get_all_displays()
        disp_data = [d.to_dict() if hasattr(d, "to_dict") else vars(d) for d in displays]
    except Exception:
        disp_data = []

    active_win = "Desktop Workspace"
    try:
        from core.zetta.accessibility.capabilities import AccessibilityCapabilityType
        res = am.execute_action(AccessibilityCapabilityType.INSPECT_ACTIVE_UI)
        if res.success:
            active_win = "Active Desktop Session"
    except Exception:
        pass

    return {
        "displays": disp_data,
        "active_window": active_win,
        "accessibility_tools_count": 25,
        "status": "READY",
    }


@router.get("/screenshot")
def get_screenshot(use_fake: bool = False, save_to_disk: bool = False, task_id: Optional[str] = None):
    """Capture screen and return base64 encoded PNG image. Memory-only by default."""
    vm = get_vision_manager(use_fake=use_fake)
    try:
        capture = vm.capture_screen(save_to_disk=save_to_disk, task_id=task_id)
        b64_img = base64.b64encode(capture.image_data).decode("utf-8")
        return {
            "success": True,
            "width": capture.width,
            "height": capture.height,
            "source_display": capture.source_display,
            "duration_ms": capture.duration_ms,
            "file_path": capture.file_path,
            "image_base64": f"data:image/png;base64,{b64_img}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


class ScreenAccessGrantRequest(BaseModel):
    scope: str = "ALLOW_SESSION"
    task_id: Optional[str] = None
    reason: str = "User authorized via API"


@router.get("/screen-access")
def get_screen_access():
    """Retrieve current screen observation authorization status."""
    from core.zetta.security.screen_access import get_screen_access_manager
    sam = get_screen_access_manager()
    return sam.get_status()


@router.post("/screen-access/grant")
def grant_screen_access(req: ScreenAccessGrantRequest):
    """Grant screen access under a specific scope."""
    from core.zetta.security.screen_access import get_screen_access_manager, ScreenAccessScope
    sam = get_screen_access_manager()
    try:
        scope_enum = ScreenAccessScope(req.scope.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scope '{req.scope}'. Supported: {[s.value for s in ScreenAccessScope]}",
        )
    sam.grant_access(scope=scope_enum, task_id=req.task_id, reason=req.reason)
    return {"success": True, "status": sam.get_status()}


@router.post("/screen-access/revoke")
def revoke_screen_access(reason: str = "Revoked via API"):
    """Revoke all screen observation authorizations immediately."""
    from core.zetta.security.screen_access import get_screen_access_manager
    sam = get_screen_access_manager()
    sam.revoke_access(reason=reason)
    return {"success": True, "status": sam.get_status()}


@router.post("/action")
def execute_computer_action(req: ComputerActionRequest):
    """Execute one of the 25 composable accessibility/computer actions."""
    from core.zetta.accessibility.capabilities import AccessibilityCapabilityType
    am = get_accessibility_manager()
    try:
        cap = AccessibilityCapabilityType(req.action.lower())
        res = am.execute_action(cap, req.parameters or {})
        return {
            "success": res.success,
            "action": res.action.value,
            "data": res.data,
            "error": res.error,
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported accessibility action: {req.action}. Available: {[c.value for c in AccessibilityCapabilityType]}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

