"""Unit tests for Phase 08 Core Architecture and Contracts."""

import pytest
from shared.types.enums import (
    AgentCapability,
    AgentStatus,
    EventType,
    PermissionLevel,
    PersonaType,
    PlanStatus,
    TaskStatus,
    VoiceAuthLevel,
)
from shared.types.contracts import (
    AgentContext,
    AgentResult,
    ErrorInfo,
    PersonaConfig,
    SkillMetadata,
    SubTask,
    TaskPlan,
    WorkflowDefinition,
)


class TestPhase08Architecture:
    """Validate Phase 08 core enums, contracts, and lifecycle status definitions."""

    def test_agent_status_lifecycle_values(self):
        expected_statuses = {"CREATED", "READY", "RUNNING", "WAITING", "COMPLETED", "FAILED", "CANCELLED", "PAUSED"}
        actual = {s.value for s in AgentStatus}
        assert expected_statuses.issubset(actual)

    def test_agent_capabilities(self):
        expected = {
            "general", "coding", "browser", "research", "document",
            "computer", "vision", "voice", "accessibility", "autonomous"
        }
        actual = {c.value for c in AgentCapability}
        assert expected.issubset(actual)

    def test_plan_status_values(self):
        expected = {"DRAFT", "PLANNED", "EXECUTING", "COMPLETED", "FAILED", "CANCELLED"}
        actual = {s.value for s in PlanStatus}
        assert expected.issubset(actual)

    def test_persona_types(self):
        expected = {"default", "professional", "creative"}
        actual = {p.value for p in PersonaType}
        assert expected.issubset(actual)

    def test_voice_auth_levels(self):
        expected = {"AUTHORIZED", "UNKNOWN", "RESTRICTED"}
        actual = {v.value for v in VoiceAuthLevel}
        assert expected.issubset(actual)

    def test_agent_events_registered(self):
        assert EventType.PLAN_CREATED.value == "PLAN_CREATED"
        assert EventType.PLAN_COMPLETED.value == "PLAN_COMPLETED"
        assert EventType.SUBTASK_STARTED.value == "SUBTASK_STARTED"
        assert EventType.SKILL_LOADED.value == "SKILL_LOADED"
        assert EventType.WORKFLOW_STARTED.value == "WORKFLOW_STARTED"

    def test_agent_context_instantiation(self):
        ctx = AgentContext(
            agent_id="test-agent-1",
            permissions=PermissionLevel.MEDIUM,
            capabilities=[AgentCapability.GENERAL, AgentCapability.CODING],
        )
        assert ctx.agent_id == "test-agent-1"
        assert ctx.permissions == PermissionLevel.MEDIUM
        assert AgentCapability.CODING in ctx.capabilities
        assert ctx.session_id is not None

    def test_agent_result_contract(self):
        res = AgentResult(
            agent_id="agent-007",
            task_id="task-123",
            success=True,
            data={"summary": "done"},
            steps_executed=3,
            duration_ms=45.2,
            tools_called=["file_read", "terminal_execute"],
        )
        assert res.success is True
        assert res.steps_executed == 3
        assert len(res.tools_called) == 2

    def test_subtask_and_task_plan(self):
        sub1 = SubTask(
            name="Inspect Workspace",
            description="Check repository layout",
            assigned_agent="CodingAgent",
            required_tools=["file_list"],
        )
        sub2 = SubTask(
            name="Run Tests",
            description="Execute test suite",
            assigned_agent="CodingAgent",
            dependencies=[sub1.id],
            required_tools=["terminal_execute"],
        )
        plan = TaskPlan(
            goal="Refactor project and verify",
            subtasks=[sub1, sub2],
            verification_criteria=["pytest exits 0"],
        )
        assert plan.status == PlanStatus.DRAFT
        assert len(plan.subtasks) == 2
        assert sub2.dependencies == [sub1.id]

    def test_skill_and_workflow_definitions(self):
        skill = SkillMetadata(
            name="git-sync",
            description="Synchronize git repository",
            required_permission=PermissionLevel.MEDIUM,
            inputs={"branch": "str"},
        )
        assert skill.name == "git-sync"
        assert skill.required_permission == PermissionLevel.MEDIUM

        wf = WorkflowDefinition(
            name="morning-brief",
            steps=[{"action": "browser.navigate", "url": "https://news.ycombinator.com"}],
        )
        assert wf.name == "morning-brief"
        assert len(wf.steps) == 1

    def test_persona_config(self):
        persona = PersonaConfig(
            persona_type=PersonaType.PROFESSIONAL,
            name="ZETTA Enterprise",
            behavior_rules=["Be concise", "Cite data points"],
            max_permission=PermissionLevel.HIGH,
        )
        assert persona.persona_type == PersonaType.PROFESSIONAL
        assert len(persona.behavior_rules) == 2
