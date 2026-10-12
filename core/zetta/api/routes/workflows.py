"""Autonomous Workflow & DAG Planning routes."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.zetta.agents.planner.planner import AutonomousPlanner
from core.zetta.agents.orchestrator.unified_workflow import UnifiedAutonomousWorkflow
from core.zetta.memory.manager import get_memory_manager
from core.zetta.security.manager import get_security_manager

router = APIRouter(prefix="/api/workflows", tags=["Workflows"])


class PlanRequest(BaseModel):
    goal: str
    use_ai: bool = False


class ExecuteGoalRequest(BaseModel):
    goal: str
    user_role: str = "user"
    persist_memory: bool = True


@router.post("/plan")
def create_plan(req: PlanRequest):
    """Decompose goal into structured TaskPlan DAG."""
    planner = AutonomousPlanner()
    try:
        plan = planner.create_plan(req.goal, use_ai=req.use_ai)
        return {
            "plan_id": plan.id,
            "goal": plan.goal,
            "status": plan.status.value,
            "verification_criteria": plan.verification_criteria,
            "subtasks": [
                {
                    "id": st.id,
                    "name": st.name,
                    "description": st.description,
                    "assigned_agent": st.assigned_agent,
                    "dependencies": st.dependencies,
                    "required_tools": st.required_tools,
                    "status": st.status.value,
                }
                for st in plan.subtasks
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/execute")
def execute_workflow(req: ExecuteGoalRequest):
    """Execute end-to-end autonomous multi-agent workflow."""
    workflow = UnifiedAutonomousWorkflow(
        memory_manager=get_memory_manager(),
        security_manager=get_security_manager(),
    )
    try:
        report = workflow.execute_goal(
            goal=req.goal,
            user_role=req.user_role,
            persist_memory=req.persist_memory,
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
