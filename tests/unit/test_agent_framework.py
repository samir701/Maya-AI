"""Unit tests for Milestone 08.1 Agent Framework."""

import pytest
from core.zetta.agents.base import BaseAgent
from core.zetta.agents.manager import AgentManager, AgentRegistry, get_agent_manager, reset_agent_manager
from core.zetta.events import get_event_bus
from core.zetta.security import get_security_manager
from core.zetta.utils.errors import AgentError, AuthorizationError
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, AgentStatus, EventType, PermissionLevel, TaskStatus


class DummySuccessAgent(BaseAgent):
    """Test agent that executes successfully."""

    def __init__(self, name="DummySuccess", required_permission=PermissionLevel.LOW):
        super().__init__(
            name=name,
            description="Agent for test success",
            capabilities=[AgentCapability.GENERAL, AgentCapability.CODING],
            required_permission=required_permission,
        )

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            task_id=task.id,
            success=True,
            data={"result": f"processed: {task.name}"},
            steps_executed=1,
            tools_called=["test_tool"],
        )


class DummyFailingAgent(BaseAgent):
    """Test agent that returns failure."""

    def __init__(self, name="DummyFail"):
        super().__init__(
            name=name,
            description="Agent for test failure",
            capabilities=[AgentCapability.RESEARCH],
            required_permission=PermissionLevel.LOW,
        )

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            task_id=task.id,
            success=False,
            error=ErrorInfo(code="ExpectedFailure", message="Intended test failure"),
        )


class DummyCrashingAgent(BaseAgent):
    """Test agent that raises an unhandled exception."""

    def __init__(self, name="DummyCrash"):
        super().__init__(
            name=name,
            description="Agent that throws exception",
            capabilities=[AgentCapability.VISION],
            required_permission=PermissionLevel.LOW,
        )

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        raise ValueError("Unexpected crash inside _run")


class TestAgentFramework:
    """Test suite for BaseAgent, AgentRegistry, and AgentManager."""

    def setup_method(self):
        reset_agent_manager()

    def test_base_agent_initialization(self):
        agent = DummySuccessAgent()
        assert agent.name == "DummySuccess"
        assert agent.status == AgentStatus.READY
        assert AgentCapability.CODING in agent.capabilities
        assert agent.required_permission == PermissionLevel.LOW
        assert agent.to_dict()["status"] == "READY"

    def test_base_agent_successful_execution(self):
        agent = DummySuccessAgent()
        task = SubTask(name="Build Feature", description="Test task execution")
        events_received = []

        bus = get_event_bus()
        bus.subscribe(EventType.AGENT_STARTED, lambda e: events_received.append(e.event_type))
        bus.subscribe(EventType.AGENT_COMPLETED, lambda e: events_received.append(e.event_type))

        result = agent.execute(task)

        assert result.success is True
        assert result.data == {"result": "processed: Build Feature"}
        assert agent.status == AgentStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED
        assert EventType.AGENT_STARTED in events_received
        assert EventType.AGENT_COMPLETED in events_received

    def test_base_agent_failed_execution(self):
        agent = DummyFailingAgent()
        task = SubTask(name="Do Research")
        result = agent.execute(task)

        assert result.success is False
        assert result.error.code == "ExpectedFailure"
        assert agent.status == AgentStatus.FAILED
        assert task.status == TaskStatus.FAILED

    def test_base_agent_exception_handled_gracefully(self):
        agent = DummyCrashingAgent()
        task = SubTask(name="Analyze Screen")
        result = agent.execute(task)

        assert result.success is False
        assert "Unexpected crash" in result.error.message
        assert agent.status == AgentStatus.FAILED
        assert task.status == TaskStatus.FAILED

    def test_base_agent_reset_lifecycle(self):
        agent = DummySuccessAgent()
        task = SubTask(name="First Run")
        agent.execute(task)
        assert agent.status == AgentStatus.COMPLETED

        agent.reset()
        assert agent.status == AgentStatus.READY
        assert agent.current_task is None

    def test_base_agent_pause_and_resume(self):
        agent = DummySuccessAgent()
        agent.status = AgentStatus.RUNNING

        assert agent.pause() is True
        assert agent.status == AgentStatus.PAUSED

        assert agent.resume() is True
        assert agent.status == AgentStatus.RUNNING

    def test_base_agent_cancel(self):
        agent = DummySuccessAgent()
        task = SubTask(name="Long Task")
        agent.current_task = task
        agent.status = AgentStatus.RUNNING

        assert agent.cancel() is True
        assert agent.status == AgentStatus.CANCELLED
        assert task.status == TaskStatus.CANCELLED

    def test_base_agent_invalid_transition_raises_error(self):
        agent = DummySuccessAgent()
        agent.status = AgentStatus.COMPLETED

        with pytest.raises(AgentError):
            agent._transition(AgentStatus.RUNNING)

    def test_security_permission_enforcement(self):
        # High permission agent when permission is restricted
        agent = DummySuccessAgent(name="HighSecAgent", required_permission=PermissionLevel.CRITICAL)
        sec_mgr = get_security_manager()
        # Temporarily restrict permission
        original_level = sec_mgr.permission_checker.current_level
        sec_mgr.permission_checker.current_level = PermissionLevel.LOW

        try:
            task = SubTask(name="Restricted Operation")
            with pytest.raises(AuthorizationError):
                agent.execute(task)
        finally:
            sec_mgr.permission_checker.current_level = original_level

    def test_agent_registry_operations(self):
        registry = AgentRegistry()
        agent1 = DummySuccessAgent(name="CoderAlpha")
        agent2 = DummyFailingAgent(name="ResearcherBeta")

        registry.register(agent1)
        registry.register(agent2)

        assert registry.has("CoderAlpha") is True
        assert registry.has(agent1.agent_id) is True
        assert registry.get("coderalpha") == agent1

        # Search by capability
        coding_agents = registry.find_by_capability(AgentCapability.CODING)
        assert len(coding_agents) == 1
        assert coding_agents[0].name == "CoderAlpha"

        # Search by permission
        low_perm = registry.find_by_permission(PermissionLevel.LOW)
        assert len(low_perm) == 2

        # Unregister
        assert registry.unregister("CoderAlpha") is True
        assert registry.has("CoderAlpha") is False

    def test_agent_manager_dispatch_and_status(self):
        manager = get_agent_manager()
        agent = DummySuccessAgent(name="GeneralWorker")
        manager.register_agent(agent)

        task = SubTask(name="Process Inbox")
        result = manager.dispatch_task("GeneralWorker", task)

        assert result.success is True
        assert result.data == {"result": "processed: Process Inbox"}

        status = manager.status()
        assert status["total_agents"] >= 1
        assert status["status"] == "OK"
