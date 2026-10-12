"""Agent Center routes displaying registered fleet and specialized agents."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.zetta.agents.fleet import register_default_fleet
from core.zetta.agents.manager.registry import get_agent_registry
from core.zetta.agents.manager.manager import get_agent_manager
from shared.types.contracts import SubTask
from shared.types.enums import AgentCapability, PermissionLevel

router = APIRouter(prefix="/api/agents", tags=["Agents"])


class AgentRunRequest(BaseModel):
    agent_name: str
    task_name: str
    task_description: Optional[str] = ""
    metadata: Optional[Dict[str, Any]] = None


@router.get("")
def list_agents():
    """List fleet agents, distinguishing Registered Fleet from Specialized/Composite Agents."""
    reg = get_agent_registry()
    if len(reg.list_agents()) == 0:
        register_default_fleet(reg)

    fleet = reg.list_agents()

    # Define specialized/composite capabilities catalog
    specialized = [
        {
            "name": "CodingAgent",
            "type": "Specialized Engineering Agent",
            "status": "ON_DEMAND",
            "capabilities": ["coding", "general"],
            "required_permission": "HIGH",
            "description": "Software engineering agent with workspace boundary validation, file modification, testing, and self-repair.",
            "is_registered": reg.has("CodingAgent"),
        },
        {
            "name": "UnifiedComputerAgent",
            "type": "Composite PC Control Agent",
            "status": "ON_DEMAND",
            "capabilities": ["computer", "general", "browser", "vision", "accessibility"],
            "required_permission": "HIGH",
            "description": "Full PC control agent coordinating desktop, applications, filesystem, terminal, clipboard, vision, and browser.",
            "is_registered": reg.has("UnifiedComputerAgent"),
        },
        {
            "name": "AccessibilityAgent",
            "type": "Specialized Accessibility Agent",
            "status": "ON_DEMAND",
            "capabilities": ["accessibility", "vision"],
            "required_permission": "MEDIUM",
            "description": "UI accessibility automation agent implementing 25 composable desktop element interactions.",
            "is_registered": reg.has("AccessibilityAgent"),
        },
        {
            "name": "HermesAutonomousAgent",
            "type": "Autonomous Runtime Agent",
            "status": "ON_DEMAND",
            "capabilities": ["general"],
            "required_permission": "MEDIUM",
            "description": "Long-running autonomous execution agent with checkpoint snapshots, background progress, and state recovery.",
            "is_registered": reg.has("HermesAutonomousAgent"),
        },
    ]

    return {
        "status": "success",
        "fleet": fleet,
        "fleet_count": len(fleet),
        "registered_fleet_count": len(fleet),
        "registered_fleet": fleet,
        "specialized": specialized,
        "specialized_count": len(specialized),
        "specialized_agents_count": len(specialized),
        "specialized_agents": specialized,
    }


@router.get("/{name}")
def get_agent_details(name: str):
    """Get metadata for a specific agent."""
    reg = get_agent_registry()
    if not reg.has(name):
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found in active registry.")
    agent = reg.get(name)
    return agent.to_dict()


@router.post("/run")
def run_agent_task(req: AgentRunRequest):
    """Execute a task directly with a registered agent."""
    mgr = get_agent_manager()
    task = SubTask(
        name=req.task_name,
        description=req.task_description or req.task_name,
        metadata=req.metadata or {},
    )
    try:
        result = mgr.execute_agent(req.agent_name, task)
        return {
            "success": result.success,
            "agent_id": result.agent_id,
            "data": result.data,
            "tools_called": result.tools_called,
            "error": result.error.message if result.error else None,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
