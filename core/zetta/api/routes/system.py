"""System diagnostic and status routes."""

import time
from fastapi import APIRouter
from core.zetta.health import check_health
from core.zetta.tasks.manager import get_task_manager
from core.zetta.memory.manager import get_memory_manager
from core.zetta.agents.manager.registry import get_agent_registry
from core.zetta.config.settings import get_settings
from core.zetta.personas.manager import get_persona_manager

router = APIRouter(prefix="/api", tags=["System"])


def _task_summary(t):
    return {
        "id": t.id,
        "name": t.name,
        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
        "created_at": t.created_at,
    }


@router.get("/health")
def get_health(deep: bool = False):
    """Return complete system diagnostic health check.
    
    By default, performs a fast, observational, read-only status check with
    zero active side-effects (no screen captures, OCR, TTS, or task creation).
    """
    report = check_health(deep_probe=deep)
    status_str = "healthy" if report.status == "OK" else "degraded"
    return {
        "status": status_str,
        "raw_status": report.status,
        "timestamp": time.time(),
        "subsystems": report.checks,
        "checks": report.checks,
    }


@router.get("/status")
def get_system_status():
    """Return high-level operational overview for the Home Command Center."""
    settings = get_settings()
    task_mgr = get_task_manager()
    mem_mgr = get_memory_manager()
    agent_reg = get_agent_registry()
    persona_mgr = get_persona_manager()

    tasks = task_mgr.list_tasks()
    active_tasks = [t for t in tasks if (t.status.value if hasattr(t.status, "value") else str(t.status)) in ("CREATED", "PENDING", "RUNNING")]

    active_persona = persona_mgr.get_active_persona()
    reg_agents = agent_reg.list_agents()

    return {
        "employee_name": "ZETTA",
        "version": settings.app.version,
        "state": "ONLINE",
        "environment": settings.app.env,
        "active_agent": "GeneralAssistantAgent",
        "active_persona": active_persona.name,
        "persona_type": active_persona.persona_type.value,
        "agents_count": len(reg_agents),
        "registered_agents_count": len(reg_agents),
        "total_tasks_count": len(tasks),
        "active_tasks_count": len(active_tasks),
        "active_task": _task_summary(active_tasks[0]) if active_tasks else None,
        "memory_count": len(mem_mgr.repo.list(limit=100)),
        "ai_provider": settings.ai.default_provider,
        "ai_model": settings.ai.default_model,
    }
