"""ZETTA API Routes - Vision & Screen Intelligence."""

import base64
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.zetta.vision.manager import VisionManager
from core.zetta.utils.logging import get_logger

logger = get_logger("api_vision")
router = APIRouter(prefix="/api/vision", tags=["vision"])

_vision_manager: Optional[VisionManager] = None
_last_capture = None


def get_vision() -> VisionManager:
    global _vision_manager
    if _vision_manager is None:
        _vision_manager = VisionManager()
    return _vision_manager


class CaptureRequest(BaseModel):
    display_id: Optional[str] = None


@router.get("/status")
def get_vision_status() -> Dict[str, Any]:
    """Inspect vision subsystem status and display availability."""
    try:
        vm = get_vision()
        displays = vm.get_all_displays()
        primary = vm.get_screen_info()
        return {
            "status": "ready",
            "primary_display": {
                "id": getattr(primary, "id", "primary"),
                "name": getattr(primary, "name", "Main Display"),
                "width": getattr(primary, "width", 1920),
                "height": getattr(primary, "height", 1080),
            },
            "displays": [
                {
                    "id": getattr(d, "id", str(idx)),
                    "name": getattr(d, "name", f"Display {idx}"),
                    "width": getattr(d, "width", 1920),
                    "height": getattr(d, "height", 1080),
                }
                for idx, d in enumerate(displays)
            ],
            "last_capture_id": _last_capture.id if _last_capture else None,
        }
    except Exception as e:
        logger.warning(f"Vision status check warning: {e}")
        return {
            "status": "degraded",
            "error": str(e),
            "displays": [],
            "last_capture_id": None,
        }


@router.post("/capture")
def capture_screen(req: CaptureRequest) -> Dict[str, Any]:
    """Capture a screen snapshot and return image data."""
    global _last_capture
    try:
        vm = get_vision()
        capture = vm.capture_screen(display_id=req.display_id)
        _last_capture = capture

        b64_img = ""
        if capture.image_data:
            b64_img = base64.b64encode(capture.image_data).decode("utf-8")

        return {
            "status": "success",
            "capture": {
                "id": capture.id,
                "width": capture.width,
                "height": capture.height,
                "timestamp": capture.timestamp,
                "format": capture.format,
                "image_data_url": f"data:image/{capture.format};base64,{b64_img}" if b64_img else None,
            }
        }
    except Exception as e:
        logger.error(f"Screen capture failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ocr")
def perform_ocr() -> Dict[str, Any]:
    """Run OCR on the latest screen capture."""
    global _last_capture
    vm = get_vision()
    if _last_capture is None:
        try:
            _last_capture = vm.capture_screen()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"No screen capture available: {e}")

    try:
        result = vm.perform_ocr(_last_capture)
        return {
            "status": "success",
            "text": result.text,
            "confidence": getattr(result, "confidence", 1.0),
            "regions_count": len(getattr(result, "regions", [])),
            "regions": [r.to_dict() if hasattr(r, "to_dict") else str(r) for r in getattr(result, "regions", [])][:30],
        }
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect")
def detect_ui_elements() -> Dict[str, Any]:
    """Detect UI elements on the latest screen capture."""
    global _last_capture
    vm = get_vision()
    if _last_capture is None:
        try:
            _last_capture = vm.capture_screen()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"No screen capture available: {e}")

    try:
        result = vm.detect_ui(_last_capture)
        elements = getattr(result, "elements", [])
        return {
            "status": "success",
            "elements_count": len(elements),
            "elements": [el.to_dict() if hasattr(el, "to_dict") else str(el) for el in elements][:50],
        }
    except Exception as e:
        logger.error(f"UI detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
