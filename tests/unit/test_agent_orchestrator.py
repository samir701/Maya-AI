"""Unit tests for Milestone 08.3 Agent Orchestrator."""

import time
import pytest
from core.zetta.agents.base import BaseAgent
from core.zetta.agents.manager import AgentManager, AgentRegistry, reset_agent_manager
from core.zetta.agents.orchestrator import AgentOrchestrator
from core.zetta.events import get_event_bus
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask, TaskPlan
from shared.types.enums import AgentCapability, EventType, PermissionLevel, PlanStatus, TaskStatus


class FastAgent(BaseAgent):
    """Agent that executes promptly."""

    def __init__(self, name="FastWorker"):
        super().__init__(name=name, description="Fast worker", capabilities=[AgentCapability.GENERAL], required_permission=PermissionLevel.LOW)

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            task_id=task.id,
            success=True,
            data={"done": task.name},
        )


class FlakyAgent(BaseAgent):
    """Agent that fails on first attempt and succeeds on retry."""

    def __init__(self, name="FlakyWorker"):
        super().__init__(name=name, description="Flaky worker", capabilities=[AgentCapability.GENERAL], required_permission=PermissionLevel.LOW)
        self.attempts = 0

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        self.attempts += 1
        if self.attempts == 1:
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=False,
                error=ErrorInfo(code="TransientError", message="First attempt failed"),
            )
        return AgentResult(
            agent_id=self.agent_id,
            task_id=task.id,
            success=True,
            data={"recovered": True},
        )


class SlowAgent(BaseAgent):
    """Agent that simulates a long-running/hanging operation."""

    def __init__(self, name="SlowWorker"):
        super().__init__(name=name, description="Slow worker", capabilities=[AgentCapability.GENERAL], required_permission=PermissionLevel.LOW)

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        time.sleep(1.0)
        return AgentResult(agent_id=self.agent_id, task_id=task.id, success=True)


class TestAgentOrchestrator:
    """Test suite for AgentOrchestrator."""

    def setup_method(self):
        reset_agent_manager()
        self.registry = AgentRegistry()
        self.manager = AgentManager(registry=self.registry)
        self.orchestrator = AgentOrchestrator(agent_manager=self.manager, max_workers=4)

    def test_orchestrate_linear_plan(self):
        self.manager.register_agent(FastAgent())

        s1 = SubTask(name="Step 1", assigned_agent="FastWorker")
        s2 = SubTask(name="Step 2", assigned_agent="FastWorker", dependencies=[s1.id])
        plan = TaskPlan(goal="Linear Execution", subtasks=[s1, s2])

        events = []
        bus = get_event_bus()
        bus.subscribe(EventType.PLAN_STARTED, lambda e: events.append(e.event_type))
        bus.subscribe(EventType.PLAN_COMPLETED, lambda e: events.append(e.event_type))

        executed = self.orchestrator.execute_plan(plan)

        assert executed.status == PlanStatus.COMPLETED
        assert s1.status == TaskStatus.COMPLETED
        assert s2.status == TaskStatus.COMPLETED
        assert EventType.PLAN_STARTED in events
        assert EventType.PLAN_COMPLETED in events

    def test_orchestrate_parallel_stage(self):
        self.manager.register_agent(FastAgent())

        s1 = SubTask(name="Root", assigned_agent="FastWorker")
        s2 = SubTask(name="Parallel A", assigned_agent="FastWorker", dependencies=[s1.id])
        s3 = SubTask(name="Parallel B", assigned_agent="FastWorker", dependencies=[s1.id])
        s4 = SubTask(name="Merge", assigned_agent="FastWorker", dependencies=[s2.id, s3.id])

        plan = TaskPlan(goal="Parallel DAG", subtasks=[s1, s2, s3, s4])
        executed = self.orchestrator.execute_plan(plan)

        assert executed.status == PlanStatus.COMPLETED
        assert all(st.status == TaskStatus.COMPLETED for st in [s1, s2, s3, s4])

    def test_orchestrator_retry_recovery(self):
        flaky = FlakyAgent()
        self.manager.register_agent(flaky)

        s1 = SubTask(name="Retry Task", assigned_agent="FlakyWorker", max_retries=2)
        plan = TaskPlan(goal="Retry Test", subtasks=[s1])

        executed = self.orchestrator.execute_plan(plan)

        assert executed.status == PlanStatus.COMPLETED
        assert s1.status == TaskStatus.COMPLETED
        assert s1.retry_count == 1
        assert s1.result == {"recovered": True}

    def test_orchestrator_timeout_enforcement(self):
        self.manager.register_agent(SlowAgent())

        # Subtask with 0.1s timeout while agent sleeps 1.0s
        s1 = SubTask(name="Slow Task", assigned_agent="SlowWorker", timeout_seconds=0.1, max_retries=0)
        plan = TaskPlan(goal="Timeout Test", subtasks=[s1])

        executed = self.orchestrator.execute_plan(plan)

        assert executed.status == PlanStatus.FAILED
        assert s1.status == TaskStatus.FAILED
        assert "exceeded timeout" in s1.error.message

    def test_orchestrator_plan_cancellation(self):
        self.manager.register_agent(FastAgent())

        s1 = SubTask(name="Step 1", assigned_agent="FastWorker")
        s2 = SubTask(name="Step 2", assigned_agent="FastWorker", dependencies=[s1.id])
        plan = TaskPlan(goal="Cancel Test", subtasks=[s1, s2])

        self.orchestrator._active_plans[plan.id] = plan
        cancelled = self.orchestrator.cancel_plan(plan.id)

        assert cancelled is True
        assert plan.status == PlanStatus.CANCELLED
        assert s1.status == TaskStatus.CANCELLED
