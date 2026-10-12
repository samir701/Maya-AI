"""Interactive chat endpoints for ZETTA conversational interface."""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.zetta.interaction.manager import InteractionManager
from core.zetta.interaction.session import get_session_manager
from core.zetta.personas.manager import get_persona_manager

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class MessageRequest(BaseModel):
    session_id: str
    message: str
    use_real_ai: bool = False


class SessionCreateRequest(BaseModel):
    name: Optional[str] = "Default Session"


@router.get("/sessions")
def list_sessions():
    """List all interactive sessions."""
    sess_mgr = get_session_manager()
    sessions = list(sess_mgr.active_sessions.values())
    return [
        {
            "session_id": s.session_id,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "message_count": len(s.messages),
            "metadata": s.metadata,
        }
        for s in sessions
    ]


@router.post("/sessions")
def create_session(req: SessionCreateRequest):
    """Create a new conversational session."""
    sess_mgr = get_session_manager()
    session = sess_mgr.create_session(metadata={"name": req.name})
    return session.to_dict()


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Fetch session history."""
    sess_mgr = get_session_manager()
    session = sess_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@router.post("/message")
def send_message(req: MessageRequest):
    """Process conversational user message through InteractionManager."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    sess_mgr = get_session_manager()
    session = sess_mgr.get_session(req.session_id)
    if not session:
        session = sess_mgr.create_session(session_id=req.session_id)

    manager = InteractionManager()
    persona = get_persona_manager().get_active_persona()

    try:
        response_text = manager.process_user_message(
            session_id=session.session_id,
            user_input=req.message,
            system_prompt=persona.system_prompt,
        )
        return {
            "status": "success",
            "session_id": session.session_id,
            "response": response_text,
            "persona": persona.name,
        }
    except Exception as e:
        return {
            "status": "error",
            "session_id": session.session_id,
            "response": f"Encountered error: {str(e)}",
            "error": str(e),
        }
