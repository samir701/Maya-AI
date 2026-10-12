"""ZETTA Base Agent Interface and Lifecycle State Machine."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.zetta.events import Event, get_event_bus
from core.zetta.security import get_security_manager
from core.zetta.utils.errors import AgentError, AuthorizationError
from core.zetta.utils.logging import get_logger
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, AgentStatus, EventType, PermissionLevel, TaskStatus

logger = get_logger("agent_base")


class BaseAgent(ABC):
    """Abstract base class for all specialized and autonomous agents in ZETTA.

    Provides a validated lifecycle state machine, security permission enforcement,
    event publication, execution instrumentation, and cancellation/pause semantics.
    """

    def __init__(
        self,
        name: str,
        description: str,
        capabilities: Optional[List[AgentCapability]] = None,
        required_permission: PermissionLevel = PermissionLevel.MEDIUM,
        agent_id: Optional[str] = None,
    ) -> None:
        self.agent_id = agent_id or f"{name.lower().replace(' ', '_')}_{uuid4().hex[:8]}"
        self.name = name
        self.description = description
        self.capabilities = capabilities or [AgentCapability.GENERAL]
        self.required_permission = required_permission
        self.status = AgentStatus.READY
        self.context: Optional[AgentContext] = None
        self.current_task: Optional[SubTask] = None
        self._is_cancelled = False
        self._is_paused = False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id='{self.agent_id}' name='{self.name}' status='{self.status.value}'>"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize agent state and metadata to a dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "required_permission": self.required_permission.value,
            "status": self.status.value,
            "current_task_id": self.current_task.id if self.current_task else None,
            "is_paused": self._is_paused,
            "is_cancelled": self._is_cancelled,
        }

    def _transition(self, new_status: AgentStatus) -> None:
        """Validate and apply a lifecycle state transition."""
        valid_transitions = {
            AgentStatus.CREATED: {AgentStatus.READY},
            AgentStatus.READY: {AgentStatus.RUNNING, AgentStatus.PAUSED, AgentStatus.CANCELLED, AgentStatus.FAILED},
            AgentStatus.RUNNING: {AgentStatus.WAITING, AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.PAUSED, AgentStatus.CANCELLED},
            AgentStatus.WAITING: {AgentStatus.RUNNING, AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED},
            AgentStatus.PAUSED: {AgentStatus.RUNNING, AgentStatus.READY, AgentStatus.CANCELLED},
            AgentStatus.COMPLETED: {AgentStatus.READY},
            AgentStatus.FAILED: {AgentStatus.READY},
            AgentStatus.CANCELLED: {AgentStatus.READY},
        }

        allowed = valid_transitions.get(self.status, set())
        if new_status not in allowed:
            raise AgentError(
                f"Invalid agent status transition for '{self.name}': cannot transition from {self.status.value} to {new_status.value}."
            )
        old_status = self.status
        self.status = new_status
        logger.debug(f"Agent '{self.name}' transitioned from {old_status.value} to {new_status.value}")

    def execute(self, task: SubTask, context: Optional[AgentContext] = None) -> AgentResult:
        """Execute a subtask with security validation, event publication, and timing."""
        security_manager = getattr(self, "security_manager", None) or get_security_manager()
        event_bus = get_event_bus()

        # 0. Auto-reset if in terminal state
        if self.status in (AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED):
            self.reset()

        # 1. Security permission check
        if not security_manager.check_tool_permission(self.required_permission):
            err_msg = (
                f"Agent '{self.name}' execution denied: Required permission "
                f"'{self.required_permission.value}' exceeds current security grant."
            )
            security_manager.audit_logger.log_event(
                action=f"agent_execute:{self.name}",
                actor="system",
                resource=self.agent_id,
                status="REJECTED_PERMISSION",
                details={"permission": self.required_permission.value, "task_id": task.id},
            )
            self._transition(AgentStatus.FAILED)
            raise AuthorizationError(err_msg)

        # 2. Setup context & task
        self.context = context or AgentContext(
            agent_id=self.agent_id,
            task_id=task.id,
            permissions=self.required_permission,
            capabilities=self.capabilities,
        )
        self.current_task = task
        if not self._is_cancelled:
            self._is_cancelled = False
        self._is_paused = False

        self._transition(AgentStatus.RUNNING)
        task.status = TaskStatus.RUNNING

        # 3. Publish AGENT_STARTED
        event_bus.publish(
            Event(
                event_type=EventType.AGENT_STARTED,
                payload={"agent_id": self.agent_id, "name": self.name, "task_id": task.id},
                task_id=task.id,
            )
        )
        security_manager.audit_logger.log_event(
            action=f"agent_execute:{self.name}",
            actor="system",
            resource=self.agent_id,
            status="STARTED",
            details={"task_name": task.name, "task_id": task.id},
        )

        start_time = time.perf_counter()
        try:
            # 4. Check for pre-cancellation
            if self._is_cancelled:
                self._transition(AgentStatus.CANCELLED)
                task.status = TaskStatus.CANCELLED
                return AgentResult(
                    agent_id=self.agent_id,
                    task_id=task.id,
                    success=False,
                    error=ErrorInfo(code="AgentCancelled", message="Agent execution was cancelled before start."),
                )

            # 5. Invoke concrete agent logic
            result = self._run(task=task, context=self.context)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            result.duration_ms = elapsed_ms

            # 6. Apply outcome
            if result.success:
                self._transition(AgentStatus.COMPLETED)
                task.status = TaskStatus.COMPLETED
                task.result = result.data
                event_bus.publish(
                    Event(
                        event_type=EventType.AGENT_COMPLETED,
                        payload={"agent_id": self.agent_id, "duration_ms": elapsed_ms},
                        task_id=task.id,
                    )
                )
                security_manager.audit_logger.log_event(
                    action=f"agent_execute:{self.name}",
                    actor="system",
                    resource=self.agent_id,
                    status="COMPLETED",
                    details={"duration_ms": elapsed_ms},
                )
            else:
                self._transition(AgentStatus.FAILED)
                task.status = TaskStatus.FAILED
                task.error = result.error
                event_bus.publish(
                    Event(
                        event_type=EventType.AGENT_FAILED,
                        payload={
                            "agent_id": self.agent_id,
                            "error": result.error.message if result.error else "Unknown error",
                        },
                        task_id=task.id,
                    )
                )
                security_manager.audit_logger.log_event(
                    action=f"agent_execute:{self.name}",
                    actor="system",
                    resource=self.agent_id,
                    status="FAILED",
                    details={"error": result.error.message if result.error else "Unknown error"},
                )

            return result

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            self._transition(AgentStatus.FAILED)
            task.status = TaskStatus.FAILED
            err = ErrorInfo(code=self.__class__.__name__, message=str(e))
            task.error = err

            event_bus.publish(
                Event(
                    event_type=EventType.AGENT_FAILED,
                    payload={"agent_id": self.agent_id, "error": str(e)},
                    task_id=task.id,
                )
            )
            security_manager.audit_logger.log_event(
                action=f"agent_execute:{self.name}",
                actor="system",
                resource=self.agent_id,
                status="ERROR",
                details={"error": str(e)},
            )
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=False,
                error=err,
                duration_ms=elapsed_ms,
            )

    @abstractmethod
    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        """Concrete agent execution logic implemented by specialized agents."""
        raise NotImplementedError

    def pause(self) -> bool:
        """Pause agent execution if running."""
        if self.status == AgentStatus.RUNNING:
            self._is_paused = True
            self._transition(AgentStatus.PAUSED)
            get_event_bus().publish(
                Event(
                    event_type=EventType.AGENT_PAUSED,
                    payload={"agent_id": self.agent_id, "name": self.name},
                    task_id=self.current_task.id if self.current_task else None,
                )
            )
            return True
        return False

    def resume(self) -> bool:
        """Resume paused agent execution."""
        if self.status == AgentStatus.PAUSED:
            self._is_paused = False
            self._transition(AgentStatus.RUNNING)
            get_event_bus().publish(
                Event(
                    event_type=EventType.AGENT_RESUMED,
                    payload={"agent_id": self.agent_id, "name": self.name},
                    task_id=self.current_task.id if self.current_task else None,
                )
            )
            return True
        return False

    def cancel(self) -> bool:
        """Cancel agent execution."""
        if self.status in (AgentStatus.RUNNING, AgentStatus.PAUSED, AgentStatus.WAITING, AgentStatus.READY):
            self._is_cancelled = True
            self._transition(AgentStatus.CANCELLED)
            if self.current_task:
                self.current_task.status = TaskStatus.CANCELLED
            get_event_bus().publish(
                Event(
                    event_type=EventType.AGENT_CANCELLED,
                    payload={"agent_id": self.agent_id, "name": self.name},
                    task_id=self.current_task.id if self.current_task else None,
                )
            )
            return True
        return False

    def reset(self) -> None:
        """Reset agent to READY state for reuse."""
        if self.status in (AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED):
            self._transition(AgentStatus.READY)
        self._is_cancelled = False
        self._is_paused = False
        self.current_task = None
        self.context = None
