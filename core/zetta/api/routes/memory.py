"""ZETTA API Routes - Memory Subsystem."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.zetta.memory.manager import get_memory_manager
from shared.types.enums import MemoryType, MemorySource, MemorySensitivity
from core.zetta.utils.logging import get_logger

logger = get_logger("api_memory")
router = APIRouter(prefix="/api/memory", tags=["memory"])


class AddMemoryRequest(BaseModel):
    content: str
    memory_type: str = "LONG_TERM"
    source: str = "USER_EXPLICIT"
    importance: float = 0.5
    confidence: float = 1.0
    tags: List[str] = []
    sensitivity: str = "NORMAL"


@router.get("/list")
def list_memories(
    memory_type: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """List stored memories with filtering by type or tag."""
    try:
        mm = get_memory_manager()
        m_type = None
        if memory_type:
            try:
                m_type = MemoryType(memory_type.upper())
            except ValueError:
                pass
        
        memories = mm.list_memories(memory_type=m_type, tag=tag, limit=limit)
        return {
            "status": "success",
            "count": len(memories),
            "memories": [m.to_dict() if hasattr(m, "to_dict") else vars(m) for m in memories],
        }
    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
def search_memories(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
) -> Dict[str, Any]:
    """Retrieve relevant memories using ranked semantic/lexical search."""
    try:
        mm = get_memory_manager()
        results = mm.retrieve_relevant(query=query, limit=limit)
        return {
            "status": "success",
            "query": query,
            "count": len(results),
            "results": [
                {
                    "memory": r.memory.to_dict() if hasattr(r.memory, "to_dict") else vars(r.memory),
                    "score": r.score,
                    "breakdown": getattr(r, "breakdown", {}),
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
def add_memory(req: AddMemoryRequest) -> Dict[str, Any]:
    """Store a new memory item."""
    try:
        mm = get_memory_manager()
        m_type = MemoryType.LONG_TERM
        try:
            m_type = MemoryType(req.memory_type.upper())
        except ValueError:
            pass

        m_source = MemorySource.USER_EXPLICIT
        try:
            m_source = MemorySource(req.source.upper())
        except ValueError:
            pass

        m_sens = MemorySensitivity.NORMAL
        try:
            m_sens = MemorySensitivity(req.sensitivity.upper())
        except ValueError:
            pass

        saved = mm.add_memory(
            content=req.content,
            memory_type=m_type,
            source=m_source,
            importance=req.importance,
            confidence=req.confidence,
            tags=req.tags,
            sensitivity=m_sens,
        )
        return {
            "status": "success",
            "memory": saved.to_dict() if hasattr(saved, "to_dict") else vars(saved),
        }
    except Exception as e:
        logger.error(f"Failed to create memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{memory_id}")
def delete_memory(memory_id: str) -> Dict[str, Any]:
    """Remove a memory by ID."""
    try:
        mm = get_memory_manager()
        deleted = mm.delete_memory(memory_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Memory not found or deletion failed")
        return {
            "status": "success",
            "deleted_id": memory_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete memory {memory_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
