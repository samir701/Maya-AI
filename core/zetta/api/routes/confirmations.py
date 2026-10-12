"""ZETTA API Routes - Security Confirmations Subsystem."""

import time
from typing import Any, Dict, List, Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.zetta.events import Event, EventBus, get_event_bus
from core.zetta.security.manager import get_security_manager
from core.zetta.utils.logging import get_logger
from shared.types.enums import EventType, PermissionLevel

logger = get_logger("api_confirmations")
router = APIRouter(prefix="/api/confirmations", tags=["confirmations"])

_pending_confirmations: Dict[str, Dict[str, Any]] = {}
_history: List[Dict[str, Any]] = []
_event_subscribed = False


def _on_confirmation_event(event: Event) -> None:
    """Capture confirmation events published across ZETTA."""
    if event.event_type in (EventType.CONFIRMATION_REQUESTED, EventType.USER_CONFIRMATION_REQUIRED):
        cid = event.payload.get("confirmation_id") or str(uuid4())
        _pending_confirmations[cid] = {
            "id": cid,
            "action": event.payload.get("action", "Sensitive Operation"),
            "description": event.payload.get("description", "A high-risk action requires your explicit approval."),
            "required_permission": event.payload.get("required_permission", "HIGH"),
            "target": event.payload.get("target", "system"),
            "metadata": event.payload.get("metadata", {}),
            "timestamp": time.time(),
            "status": "PENDING",
        }
        logger.info(f"Captured pending confirmation: {cid}")


def ensure_subscription():
    global _event_subscribed
    if not _event_subscribed:
        eb = get_event_bus()
        eb.subscribe(EventType.CONFIRMATION_REQUESTED, _on_confirmation_event)
        eb.subscribe(EventType.USER_CONFIRMATION_REQUIRED, _on_confirmation_event)
        _event_subscribed = True


class ResolveRequest(BaseModel):
    approved: bool
    user_role: str = "user"
    reason: Optional[str] = None


class RequestConfirmationPayload(BaseModel):
    action: str
    description: str
    required_permission: str = "HIGH"
    target: str = "system"
    metadata: Dict[str, Any] = {}


@router.get("")
def list_confirmations() -> Dict[str, Any]:
    """List pending confirmations and recent confirmation history."""
    ensure_subscription()
    return {
        "status": "success",
        "pending": list(_pending_confirmations.values()),
        "pending_count": len(_pending_confirmations),
        "history": _history[-20:],
    }


@router.post("/request")
def create_confirmation_request(req: RequestConfirmationPayload) -> Dict[str, Any]:
    """Submit a confirmation request into the security pipeline."""
    ensure_subscription()
    cid = str(uuid4())
    item = {
        "id": cid,
        "action": req.action,
        "description": req.description,
        "required_permission": req.required_permission,
        "target": req.target,
        "metadata": req.metadata,
        "timestamp": time.time(),
        "status": "PENDING",
    }
    _pending_confirmations[cid] = item

    eb = get_event_bus()
    eb.publish(
        Event(
            event_type=EventType.CONFIRMATION_REQUESTED,
            payload={
                "confirmation_id": cid,
                "action": req.action,
                "description": req.description,
                "required_permission": req.required_permission,
                "target": req.target,
                "metadata": req.metadata,
            },
        )
    )

    return {
        "status": "success",
        "confirmation": item,
    }


@router.post("/{confirmation_id}/resolve")
def resolve_confirmation(confirmation_id: str, req: ResolveRequest) -> Dict[str, Any]:
    """Approve or reject a pending security confirmation."""
    ensure_subscription()
    if confirmation_id not in _pending_confirmations:
        raise HTTPException(status_code=404, detail="Confirmation request not found or already resolved.")

    item = _pending_confirmations.pop(confirmation_id)
    item["status"] = "APPROVED" if req.approved else "REJECTED"
    item["resolved_at"] = time.time()
    item["resolved_by"] = req.user_role
    item["resolution_reason"] = req.reason
    _history.append(item)

    # Audit via SecurityManager
    sec = get_security_manager()
    sec.audit.log_event(
        action=f"confirm_{item['action']}",
        actor=req.user_role,
        resource=f"confirmation:{confirmation_id}",
        status=item["status"],
        details={"approved": req.approved, "reason": req.reason},
    )

    # Publish resolution event
    eb = get_event_bus()
    eb.publish(
        Event(
            event_type=EventType.TOOL_COMPLETED if req.approved else EventType.TOOL_FAILED,
            payload={
                "confirmation_id": confirmation_id,
                "approved": req.approved,
                "action": item["action"],
            },
        )
    )

    return {
        "status": "success",
        "confirmation_id": confirmation_id,
        "resolution": item["status"],
    }
