"""Task Center routes managing system tasks."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.zetta.tasks.manager import get_task_manager
from shared.types.contracts import Task

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


def task_to_dict(t: Task) -> Dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
        "created_at": t.created_at,
        "started_at": t.started_at,
        "completed_at": t.completed_at,
        "result": t.result,
        "error": t.error.message if t.error else None,
        "metadata": t.metadata,
    }


class TaskCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    metadata: Optional[Dict[str, Any]] = None


@router.get("")
def list_tasks():
    """List all registered system tasks."""
    mgr = get_task_manager()
    tasks = mgr.list_tasks()
    return {
        "status": "success",
        "tasks": [task_to_dict(t) for t in tasks],
        "count": len(tasks),
    }


@router.post("")
def create_task(req: TaskCreateRequest):
    """Create a new task."""
    mgr = get_task_manager()
    task = mgr.create_task(name=req.name, metadata=req.metadata or {})
    return task_to_dict(task)


@router.get("/{task_id}")
def get_task(task_id: str):
    """Fetch task details."""
    mgr = get_task_manager()
    task = mgr.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_dict(task)


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str):
    """Cancel a running or pending task."""
    mgr = get_task_manager()
    success = mgr.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Unable to cancel task (already completed or not found)")
    return {"status": "CANCELLED", "task_id": task_id}
