"""ZETTA Agent Orchestrator for Concurrent DAG Plan Execution."""

import concurrent.futures
import time
from typing import Any, Dict, List, Optional, Set
from core.zetta.agents.manager.manager import AgentManager, get_agent_manager
from core.zetta.agents.planner.task_graph import TaskGraph
from core.zetta.events import Event, get_event_bus
from core.zetta.security import get_security_manager
from core.zetta.utils.errors import AgentError, TimeoutError
from core.zetta.utils.logging import get_logger
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask, TaskPlan
from shared.types.enums import EventType, PlanStatus, TaskStatus

logger = get_logger("orchestrator")


class AgentOrchestrator:
    """Executes structured TaskPlans across specialized agents with safe concurrency,

    retries, cancellation, and verification.
    """

    def __init__(
        self,
        agent_manager: Optional[AgentManager] = None,
        max_workers: int = 4,
    ) -> None:
        self.agent_manager = agent_manager or get_agent_manager()
        self.max_workers = max(1, min(max_workers, 16))
        self.event_bus = get_event_bus()
        self.security_manager = get_security_manager()
        self._active_plans: Dict[str, TaskPlan] = {}
        self._cancelled_plans: Set[str] = set()

    def get_active_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """Retrieve an active or recently executed plan by ID."""
        return self._active_plans.get(plan_id)

    def cancel_plan(self, plan_id: str) -> bool:
        """Mark a plan for immediate cancellation."""
        if plan_id in self._active_plans:
            self._cancelled_plans.add(plan_id)
            plan = self._active_plans[plan_id]
            plan.status = PlanStatus.CANCELLED
            for st in plan.subtasks:
                if st.status in (TaskStatus.CREATED, TaskStatus.QUEUED, TaskStatus.RUNNING):
                    st.status = TaskStatus.CANCELLED
            self.event_bus.publish(
                Event(
                    event_type=EventType.PLAN_FAILED,
                    payload={"plan_id": plan_id, "reason": "User cancelled plan"},
                    task_id=plan_id,
                )
            )
            logger.info(f"Plan '{plan_id}' cancelled.")
            return True
        return False

    def execute_plan(
        self,
        plan: TaskPlan,
        context: Optional[AgentContext] = None,
    ) -> TaskPlan:
        """Execute all subtasks in a TaskPlan respecting DAG stages and concurrency."""
        plan.status = PlanStatus.EXECUTING
        self._active_plans[plan.id] = plan
        self._cancelled_plans.discard(plan.id)

        self.event_bus.publish(
            Event(
                event_type=EventType.PLAN_STARTED,
                payload={"plan_id": plan.id, "goal": plan.goal, "subtask_count": len(plan.subtasks)},
                task_id=plan.id,
            )
        )
        self.security_manager.audit_logger.log_event(
            action=f"plan_execute:{plan.id}",
            actor="orchestrator",
            resource=plan.id,
            status="STARTED",
            details={"goal": plan.goal},
        )

        start_time = time.perf_counter()
        graph = TaskGraph(plan.subtasks)
        stages = graph.get_execution_stages()

        overall_success = True

        for stage_idx, stage_tasks in enumerate(stages):
            # Check for cancellation between stages
            if plan.id in self._cancelled_plans:
                plan.status = PlanStatus.CANCELLED
                overall_success = False
                break

            stage_success = self._execute_stage(stage_tasks, context, plan)
            if not stage_success:
                overall_success = False
                break

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        plan.estimated_duration_ms = elapsed_ms
        plan.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if overall_success and plan.id not in self._cancelled_plans:
            plan.status = PlanStatus.COMPLETED
            self.event_bus.publish(
                Event(
                    event_type=EventType.PLAN_COMPLETED,
                    payload={"plan_id": plan.id, "duration_ms": elapsed_ms},
                    task_id=plan.id,
                )
            )
            self.security_manager.audit_logger.log_event(
                action=f"plan_execute:{plan.id}",
                actor="orchestrator",
                resource=plan.id,
                status="COMPLETED",
                details={"duration_ms": elapsed_ms},
            )
        else:
            if plan.status != PlanStatus.CANCELLED:
                plan.status = PlanStatus.FAILED
            self.event_bus.publish(
                Event(
                    event_type=EventType.PLAN_FAILED,
                    payload={"plan_id": plan.id, "status": plan.status.value},
                    task_id=plan.id,
                )
            )
            self.security_manager.audit_logger.log_event(
                action=f"plan_execute:{plan.id}",
                actor="orchestrator",
                resource=plan.id,
                status="FAILED",
                details={"status": plan.status.value},
            )

        return plan

    def _execute_stage(
        self,
        stage_tasks: List[SubTask],
        context: Optional[AgentContext],
        plan: TaskPlan,
    ) -> bool:
        """Execute an independent stage of parallel subtasks concurrently."""
        if len(stage_tasks) == 1:
            return self._execute_subtask_with_retry(stage_tasks[0], context, plan)

        # Parallel execution with bounded thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_workers, len(stage_tasks))) as executor:
            future_to_task = {
                executor.submit(self._execute_subtask_with_retry, task, context, plan): task
                for task in stage_tasks
            }
            all_succeeded = True
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    success = future.result()
                    if not success:
                        all_succeeded = False
                except Exception as e:
                    logger.error(f"Execution error in subtask '{task.name}': {e}")
                    task.status = TaskStatus.FAILED
                    task.error = ErrorInfo(code="SubtaskExecutionError", message=str(e))
                    all_succeeded = False

            return all_succeeded

    def _execute_subtask_with_retry(
        self,
        subtask: SubTask,
        context: Optional[AgentContext],
        plan: TaskPlan,
    ) -> bool:
        """Execute a subtask with bounded retries and timeout enforcement."""
        while subtask.retry_count <= subtask.max_retries:
            if plan.id in self._cancelled_plans:
                subtask.status = TaskStatus.CANCELLED
                return False

            success = self._run_single_subtask(subtask, context, plan)
            if success:
                return True

            subtask.retry_count += 1
            if subtask.retry_count <= subtask.max_retries:
                logger.warning(
                    f"Subtask '{subtask.name}' failed. Retrying ({subtask.retry_count}/{subtask.max_retries})..."
                )
                time.sleep(0.1)

        return False

    def _run_single_subtask(
        self,
        subtask: SubTask,
        context: Optional[AgentContext],
        plan: TaskPlan,
    ) -> bool:
        """Dispatch a single subtask to its assigned agent."""
        agent_name = subtask.assigned_agent or "GeneralAssistantAgent"
        if not self.agent_manager.registry.has(agent_name):
            # Attempt to find fallback agent
            fallback_agent = self.agent_manager.registry.get("generalassistantagent") if self.agent_manager.registry.has("generalassistantagent") else None
            if not fallback_agent:
                agents = list(self.agent_manager.registry._agents_by_id.values())
                fallback_agent = agents[0] if agents else None

            if not fallback_agent:
                subtask.status = TaskStatus.FAILED
                subtask.error = ErrorInfo(
                    code="AgentNotFound",
                    message=f"No agent '{agent_name}' or fallback registered in AgentRegistry.",
                )
                return False
            agent = fallback_agent
        else:
            agent = self.agent_manager.get_agent(agent_name)

        self.event_bus.publish(
            Event(
                event_type=EventType.SUBTASK_STARTED,
                payload={"subtask_id": subtask.id, "name": subtask.name, "agent": agent.name},
                task_id=plan.id,
            )
        )

        try:
            # Enforce timeout if requested
            if subtask.timeout_seconds > 0:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as single_executor:
                    future = single_executor.submit(agent.execute, subtask, context)
                    try:
                        result: AgentResult = future.result(timeout=subtask.timeout_seconds)
                    except concurrent.futures.TimeoutError:
                        agent.cancel()
                        subtask.status = TaskStatus.FAILED
                        subtask.error = ErrorInfo(
                            code="SubtaskTimeout",
                            message=f"Subtask '{subtask.name}' exceeded timeout of {subtask.timeout_seconds}s.",
                        )
                        self.event_bus.publish(
                            Event(
                                event_type=EventType.SUBTASK_FAILED,
                                payload={"subtask_id": subtask.id, "error": subtask.error.message},
                                task_id=plan.id,
                            )
                        )
                        return False
            else:
                result = agent.execute(subtask, context)

            if result.success:
                subtask.status = TaskStatus.COMPLETED
                subtask.result = result.data
                self.event_bus.publish(
                    Event(
                        event_type=EventType.SUBTASK_COMPLETED,
                        payload={"subtask_id": subtask.id, "duration_ms": result.duration_ms},
                        task_id=plan.id,
                    )
                )
                return True
            else:
                subtask.status = TaskStatus.FAILED
                subtask.error = result.error
                self.event_bus.publish(
                    Event(
                        event_type=EventType.SUBTASK_FAILED,
                        payload={
                            "subtask_id": subtask.id,
                            "error": result.error.message if result.error else "Unknown error",
                        },
                        task_id=plan.id,
                    )
                )
                return False

        except Exception as e:
            subtask.status = TaskStatus.FAILED
            subtask.error = ErrorInfo(code=self.__class__.__name__, message=str(e))
            self.event_bus.publish(
                Event(
                    event_type=EventType.SUBTASK_FAILED,
                    payload={"subtask_id": subtask.id, "error": str(e)},
                    task_id=plan.id,
                )
            )
            return False
