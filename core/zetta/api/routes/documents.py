"""ZETTA API Routes - Documents & Deep Research."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.zetta.agents.fleet.document_agent import DocumentAgent
from core.zetta.agents.fleet.research_agent import ResearchAgent
from shared.types.contracts import AgentContext, SubTask
from core.zetta.utils.logging import get_logger

logger = get_logger("api_documents")
router = APIRouter(prefix="/api/documents", tags=["documents"])

_research_history: List[Dict[str, Any]] = []
_document_history: List[Dict[str, Any]] = []


class ResearchRequest(BaseModel):
    query: str
    tools: List[str] = []


class DocumentGenerateRequest(BaseModel):
    title: str
    instructions: str
    output_filename: Optional[str] = None


@router.get("/list")
def list_documents() -> Dict[str, Any]:
    """List generated documents and research summaries."""
    return {
        "status": "success",
        "research_tasks": _research_history[-20:],
        "documents": _document_history[-20:],
    }


@router.post("/research")
def run_research(req: ResearchRequest) -> Dict[str, Any]:
    """Execute a structured investigation and synthesis using ResearchAgent."""
    try:
        agent = ResearchAgent()
        task = SubTask(
            name=f"Research: {req.query[:40]}",
            description=req.query,
            required_tools=req.tools,
        )
        ctx = AgentContext(session_id=str(uuid4()))
        res = agent.run(task, ctx)

        item = {
            "id": task.id,
            "query": req.query,
            "success": res.success,
            "data": res.data,
            "error": res.error.message if res.error else None,
            "tools_used": res.tools_used,
        }
        _research_history.append(item)

        return {
            "status": "success" if res.success else "failed",
            "result": item,
        }
    except Exception as e:
        logger.error(f"Research task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
def generate_document(req: DocumentGenerateRequest) -> Dict[str, Any]:
    """Generate a structured Markdown report using DocumentAgent."""
    try:
        agent = DocumentAgent()
        meta = {}
        if req.output_filename:
            meta["output_path"] = req.output_filename

        task = SubTask(
            name=req.title,
            description=req.instructions,
            metadata=meta,
            required_tools=["file_write"] if req.output_filename else [],
        )
        ctx = AgentContext(session_id=str(uuid4()))
        res = agent.run(task, ctx)

        item = {
            "id": task.id,
            "title": req.title,
            "success": res.success,
            "content": res.data.get("document", "") if res.data else "",
            "output_path": req.output_filename,
        }
        _document_history.append(item)

        return {
            "status": "success" if res.success else "failed",
            "document": item,
        }
    except Exception as e:
        logger.error(f"Document generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
