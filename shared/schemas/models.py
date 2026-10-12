"""Shared Pydantic Schemas for ZETTA Validation."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from shared.types.enums import MemorySensitivity, MemorySource, MemoryType, PermissionLevel, TaskStatus


class EventSchema(BaseModel):
    id: str
    event_type: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "core.zetta"
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class ToolMetadataSchema(BaseModel):
    name: str
    description: str
    required_permission: PermissionLevel = PermissionLevel.LOW
    parameters: Dict[str, Any] = Field(default_factory=dict)


class TaskSchema(BaseModel):
    id: str
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.CREATED
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemorySchema(BaseModel):
    id: str
    content: str
    memory_type: MemoryType = MemoryType.SHORT_TERM
    source: MemorySource = MemorySource.CONVERSATION
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    sensitivity: MemorySensitivity = MemorySensitivity.NORMAL
    access_count: int = 0
    last_accessed_at: Optional[str] = None
