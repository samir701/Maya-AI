"""Shared Structural Contracts for ZETTA Architecture."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from shared.types.enums import (
    AIProviderType,
    AIRole,
    AgentCapability,
    AgentStatus,
    MemorySensitivity,
    MemorySource,
    MemoryType,
    PermissionLevel,
    PersonaType,
    PlanStatus,
    TaskStatus,
    VoiceAuthLevel,
)


@dataclass
class Permission:
    name: str
    level: PermissionLevel
    description: str = ""


@dataclass
class ExecutionContext:
    session_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = "default_user"
    environment: str = "development"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid4()))
    role: str = "user"  # system, user, assistant, tool
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    data: Optional[Any] = None
    error: Optional[ErrorInfo] = None
    execution_time_ms: float = 0.0


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.CREATED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[ErrorInfo] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Agent:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    role: str = ""
    capabilities: List[str] = field(default_factory=list)


# --- AI Core Contracts ---

@dataclass
class AIMessage:
    role: AIRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"role": self.role.value if isinstance(self.role, AIRole) else str(self.role), "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d


@dataclass
class AIRequest:
    messages: List[AIMessage]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    stream: bool = False
    stop: Optional[List[str]] = None
    response_format: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIChoice:
    index: int
    message: AIMessage
    finish_reason: Optional[str] = "stop"


@dataclass
class AIUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_ms: float = 0.0


@dataclass
class AIResponse:
    id: str = field(default_factory=lambda: f"res_{uuid4().hex[:12]}")
    provider: AIProviderType = AIProviderType.FAKE
    model: str = "default_model"
    choices: List[AIChoice] = field(default_factory=list)
    usage: AIUsage = field(default_factory=AIUsage)
    raw_response: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def text(self) -> str:
        """Helper to get primary choice text content."""
        if self.choices and self.choices[0].message:
            return self.choices[0].message.content
        return ""


@dataclass
class AIStreamChunk:
    id: str
    content: str
    finish_reason: Optional[str] = None
    is_final: bool = False


# --- Memory Architecture Contracts ---

@dataclass
class Memory:
    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    memory_type: MemoryType = MemoryType.SHORT_TERM
    source: MemorySource = MemorySource.CONVERSATION
    importance: float = 0.5  # 0.0 to 1.0
    confidence: float = 1.0  # 0.0 to 1.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    sensitivity: MemorySensitivity = MemorySensitivity.NORMAL
    embedding: Optional[List[float]] = None
    access_count: int = 0
    last_accessed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value if isinstance(self.memory_type, MemoryType) else str(self.memory_type),
            "source": self.source.value if isinstance(self.source, MemorySource) else str(self.source),
            "importance": self.importance,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "tags": self.tags,
            "metadata": self.metadata,
            "provenance": self.provenance,
            "sensitivity": self.sensitivity.value if isinstance(self.sensitivity, MemorySensitivity) else str(self.sensitivity),
            "embedding": self.embedding,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Memory":
        memory_type = MemoryType(d["memory_type"]) if d.get("memory_type") in MemoryType._value2member_map_ else MemoryType.SHORT_TERM
        source = MemorySource(d["source"]) if d.get("source") in MemorySource._value2member_map_ else MemorySource.CONVERSATION
        sensitivity = MemorySensitivity(d["sensitivity"]) if d.get("sensitivity") in MemorySensitivity._value2member_map_ else MemorySensitivity.NORMAL

        tags = d.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = [tags]

        metadata = d.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

        provenance = d.get("provenance", {})
        if isinstance(provenance, str):
            try:
                provenance = json.loads(provenance)
            except Exception:
                provenance = {}

        embedding = d.get("embedding")
        if isinstance(embedding, str):
            try:
                embedding = json.loads(embedding)
            except Exception:
                embedding = None

        return cls(
            id=d.get("id", str(uuid4())),
            content=d.get("content", ""),
            memory_type=memory_type,
            source=source,
            importance=float(d.get("importance", 0.5)),
            confidence=float(d.get("confidence", 1.0)),
            created_at=d.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=d.get("updated_at", datetime.now(timezone.utc).isoformat()),
            expires_at=d.get("expires_at"),
            tags=tags,
            metadata=metadata,
            provenance=provenance,
            sensitivity=sensitivity,
            embedding=embedding,
            access_count=int(d.get("access_count", 0)),
            last_accessed_at=d.get("last_accessed_at"),
        )


@dataclass
class MemoryQueryResult:
    memory: Memory
    score: float
    breakdown: Dict[str, float] = field(default_factory=dict)


# --- Phase 08 Autonomous Agent Contracts ---

@dataclass
class AgentContext:
    agent_id: str
    session_id: str = field(default_factory=lambda: str(uuid4()))
    task_id: Optional[str] = None
    permissions: PermissionLevel = PermissionLevel.MEDIUM
    capabilities: List[AgentCapability] = field(default_factory=list)
    working_dir: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    agent_id: str
    task_id: Optional[str]
    success: bool
    data: Any = None
    error: Optional[ErrorInfo] = None
    steps_executed: int = 0
    duration_ms: float = 0.0
    tools_called: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubTask:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    assigned_agent: Optional[str] = None
    required_tools: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.CREATED
    result: Optional[Any] = None
    error: Optional[ErrorInfo] = None
    retry_count: int = 0
    max_retries: int = 2
    timeout_seconds: float = 60.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskPlan:
    id: str = field(default_factory=lambda: str(uuid4()))
    goal: str = ""
    subtasks: List[SubTask] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    estimated_duration_ms: float = 0.0
    verification_criteria: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillMetadata:
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "ZETTA"
    required_permission: PermissionLevel = PermissionLevel.LOW
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class WorkflowDefinition:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonaConfig:
    persona_type: PersonaType = PersonaType.DEFAULT
    name: str = "ZETTA Default"
    behavior_rules: List[str] = field(default_factory=list)
    communication_style: str = "balanced, concise, professional"
    system_prompt: str = ""
    voice_profile: Dict[str, Any] = field(default_factory=dict)
    max_permission: PermissionLevel = PermissionLevel.HIGH

