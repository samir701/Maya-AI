"""ZETTA API Routes - Settings & Persona Management."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.zetta.config import get_settings
from core.zetta.personas.manager import get_persona_manager
from shared.types.contracts import PersonaConfig
from shared.types.enums import PersonaType
from core.zetta.utils.logging import get_logger

logger = get_logger("api_settings")
router = APIRouter(prefix="/api", tags=["settings"])


class SwitchPersonaRequest(BaseModel):
    persona_type: str


def _mask_secret(val: Optional[str]) -> Optional[str]:
    """Mask sensitive credentials so keys are never exposed in UI."""
    if not val:
        return None
    s = str(val).strip()
    if len(s) <= 8:
        return "********"
    return f"{s[:3]}...{s[-4:]}"


def _format_persona(p: PersonaConfig) -> Dict[str, Any]:
    return {
        "name": p.name,
        "type": p.persona_type.value if hasattr(p.persona_type, "value") else str(p.persona_type),
        "description": getattr(p, "description", p.communication_style),
        "communication_style": p.communication_style,
        "behavior_rules": p.behavior_rules,
        "max_permission": p.max_permission.value if hasattr(p.max_permission, "value") else str(p.max_permission),
    }


@router.get("/settings")
def get_system_settings() -> Dict[str, Any]:
    """Return system configuration with sensitive credentials masked."""
    try:
        s = get_settings()
        pm = get_persona_manager()
        active_persona = pm.get_active_persona()

        return {
            "status": "success",
            "environment": s.app.env,
            "version": s.app.version,
            "app_name": s.app.name,
            "active_persona": _format_persona(active_persona),
            "ai": {
                "default_provider": s.ai.default_provider,
                "default_model": s.ai.default_model,
                "has_openai_key": bool(s.ai.api_key),
                "openai_key_masked": _mask_secret(s.ai.api_key),
                "has_groq_key": bool(s.ai.groq_api_key),
                "groq_key_masked": _mask_secret(s.ai.groq_api_key),
                "temperature": s.ai.temperature,
                "max_tokens": s.ai.max_tokens,
            },
            "security": {
                "confirmation_threshold": s.security.confirmation_threshold,
                "sandbox_enabled": s.security.sandbox_enabled,
                "audit_enabled": getattr(s.security, "audit_enabled", True),
            },
            "voice": {
                "voice_enabled": s.voice.enabled,
                "stt_provider": s.voice.stt_provider,
                "tts_provider": s.voice.tts_provider,
                "default_voice": s.voice.kokoro_voice,
            },
            "memory": {
                "memory_enabled": s.memory.memory_enabled,
                "embedding_provider": s.memory.embedding_provider,
            },
            "browser": {
                "headless": s.browser.headless,
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/personas")
def list_personas() -> Dict[str, Any]:
    """List all available personas."""
    try:
        pm = get_persona_manager()
        active = pm.get_active_persona()
        personas = pm.list_personas()
        return {
            "status": "success",
            "active_persona": active.persona_type.value,
            "personas": [_format_persona(p) for p in personas],
        }
    except Exception as e:
        logger.error(f"Failed to list personas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings/persona")
def switch_persona(req: SwitchPersonaRequest) -> Dict[str, Any]:
    """Switch active persona."""
    try:
        pm = get_persona_manager()
        val = req.persona_type.lower()
        ptype = None
        for p in PersonaType:
            if p.value == val or p.name.lower() == val:
                ptype = p
                break

        if not ptype:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid persona type: '{req.persona_type}'. Available: {[p.value for p in PersonaType]}",
            )

        new_persona = pm.switch_persona(ptype)
        return {
            "status": "success",
            "active_persona": _format_persona(new_persona),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to switch persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))
