"""ZETTA API Routes - Real-Time Voice Subsystem."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.zetta.voice.manager import VoiceManager
from core.zetta.utils.logging import get_logger

logger = get_logger("api_voice")
router = APIRouter(prefix="/api/voice", tags=["voice"])

_voice_manager: Optional[VoiceManager] = None


def get_voice() -> VoiceManager:
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceManager()
    return _voice_manager


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None


class VoiceSessionRequest(BaseModel):
    session_id: Optional[str] = None


@router.get("/status")
def get_voice_status() -> Dict[str, Any]:
    """Return voice subsystem status, readiness, active devices, and models."""
    try:
        vm = get_voice()
        return {
            "status": "ready",
            "details": vm.status(),
        }
    except Exception as e:
        logger.warning(f"Voice status retrieval error: {e}")
        return {
            "status": "degraded",
            "error": str(e),
            "details": {},
        }


@router.get("/capabilities")
def get_voice_capabilities() -> Dict[str, Any]:
    """List audio hardware, input/output devices, and provider details."""
    try:
        vm = get_voice()
        return {
            "status": "success",
            "capabilities": vm.capabilities(),
        }
    except Exception as e:
        logger.error(f"Voice capabilities error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/start")
def start_voice_session(req: VoiceSessionRequest) -> Dict[str, Any]:
    """Start an active voice session with VAD and mic listening."""
    try:
        vm = get_voice()
        session_id = vm.start_session(session_id=req.session_id)
        return {
            "status": "success",
            "session_id": session_id,
            "state": vm.controller.state.value if hasattr(vm, "controller") else "ACTIVE",
        }
    except Exception as e:
        logger.error(f"Failed to start voice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/stop")
def stop_voice_session() -> Dict[str, Any]:
    """Stop the current voice session and release audio capture."""
    try:
        vm = get_voice()
        stopped_id = vm.stop_session()
        return {
            "status": "success",
            "stopped_session_id": stopped_id,
        }
    except Exception as e:
        logger.error(f"Failed to stop voice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak")
def speak_text(req: SpeakRequest) -> Dict[str, Any]:
    """Synthesize text into speech and play via audio output provider."""
    try:
        vm = get_voice()
        success = vm.speak(text=req.text, voice=req.voice)
        return {
            "status": "success" if success else "failed",
            "spoken_text": req.text,
        }
    except Exception as e:
        logger.error(f"Voice synthesis/playback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
