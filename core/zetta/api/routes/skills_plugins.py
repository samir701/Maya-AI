"""ZETTA API Routes - Skills and Plugins Catalog."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.zetta.skills.registry import get_skill_registry
from core.zetta.plugins.registry import get_plugin_registry
from core.zetta.plugins.manager import PluginManager
from core.zetta.utils.logging import get_logger

logger = get_logger("api_skills_plugins")
router = APIRouter(prefix="/api", tags=["skills_plugins"])

_plugin_manager: Optional[PluginManager] = None


def get_plugin_mgr() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


class PluginToggleRequest(BaseModel):
    enabled: bool
    user_role: str = "admin"


@router.get("/skills")
def list_skills() -> Dict[str, Any]:
    """List all registered skills with permission requirements and inputs."""
    try:
        sr = get_skill_registry()
        skills = sr.list_all()
        return {
            "status": "success",
            "count": len(skills),
            "skills": skills,
        }
    except Exception as e:
        logger.error(f"Failed to list skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plugins")
def list_plugins() -> Dict[str, Any]:
    """List all registered plugins with their lifecycle status."""
    try:
        pr = get_plugin_registry()
        plugins = pr.list_all()
        return {
            "status": "success",
            "count": len(plugins),
            "plugins": plugins,
        }
    except Exception as e:
        logger.error(f"Failed to list plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plugins/{name}/toggle")
def toggle_plugin(name: str, req: PluginToggleRequest) -> Dict[str, Any]:
    """Enable or disable a plugin safely."""
    try:
        pm = get_plugin_mgr()
        if req.enabled:
            pm.enable_plugin(name=name, user_role=req.user_role)
        else:
            pm.disable_plugin(name=name, user_role=req.user_role)

        plugin = pm.registry.get(name)
        status_val = plugin.status.value if plugin else "UNKNOWN"

        return {
            "status": "success",
            "plugin": name,
            "current_status": status_val,
        }
    except Exception as e:
        logger.error(f"Failed to toggle plugin {name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
