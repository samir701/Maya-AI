"""Unit tests for Milestone 08.2 Autonomous Planner and Task Graph."""

import pytest
from core.zetta.agents.planner import AutonomousPlanner, TaskGraph
from core.zetta.events import get_event_bus
from core.zetta.utils.errors import ValidationError
from shared.types.contracts import SubTask, AIResponse
from shared.types.enums import EventType, PlanStatus


class MockBrain:
    """Mock AIBrain returning structured JSON plan."""

    def __init__(self, response_text: str):
        self.response_text = response_text

    def think(self, prompt: str, **kwargs) -> AIResponse:
        resp = AIResponse()
        # Mock choice
        from shared.types.contracts import AIChoice, AIMessage
        from shared.types.enums import AIRole
        resp.choices = [AIChoice(index=0, message=AIMessage(role=AIRole.ASSISTANT, content=self.response_text))]
        return resp


class TestAutonomousPlanner:
    """Test suite for AutonomousPlanner and TaskGraph."""

    def test_task_graph_linear_dependencies(self):
        s1 = SubTask(name="Step 1")
        s2 = SubTask(name="Step 2", dependencies=[s1.id])
        s3 = SubTask(name="Step 3", dependencies=[s2.id])

        graph = TaskGraph([s1, s2, s3])
        stages = graph.get_execution_stages()

        assert len(stages) == 3
        assert stages[0][0].name == "Step 1"
        assert stages[1][0].name == "Step 2"
        assert stages[2][0].name == "Step 3"

    def test_task_graph_parallel_branches(self):
        # s1 -> s2 and s3 (parallel) -> s4
        s1 = SubTask(name="Step 1")
        s2 = SubTask(name="Branch A", dependencies=[s1.id])
        s3 = SubTask(name="Branch B", dependencies=[s1.id])
        s4 = SubTask(name="Merge", dependencies=[s2.id, s3.id])

        graph = TaskGraph([s1, s2, s3, s4])
        stages = graph.get_execution_stages()

        assert len(stages) == 3
        assert len(stages[0]) == 1  # [s1]
        assert len(stages[1]) == 2  # [s2, s3] parallel
        assert len(stages[2]) == 1  # [s4]

    def test_task_graph_cycle_detection(self):
        # s1 -> s2 -> s1 (cycle)
        s1 = SubTask(name="Step 1")
        s2 = SubTask(name="Step 2", dependencies=[s1.id])
        s1.dependencies = [s2.id]

        with pytest.raises(ValidationError, match="dependency cycle detected"):
            TaskGraph([s1, s2])

    def test_task_graph_unknown_dependency(self):
        s1 = SubTask(name="Step 1", dependencies=["non-existent-id"])
        with pytest.raises(ValidationError, match="unknown task ID"):
            TaskGraph([s1])

    def test_task_graph_ready_tasks(self):
        s1 = SubTask(name="Step 1")
        s2 = SubTask(name="Step 2", dependencies=[s1.id])
        graph = TaskGraph([s1, s2])

        ready_init = graph.get_ready_tasks(set())
        assert len(ready_init) == 1
        assert ready_init[0].name == "Step 1"

        ready_after_s1 = graph.get_ready_tasks({s1.id})
        assert len(ready_after_s1) == 1
        assert ready_after_s1[0].name == "Step 2"

    def test_planner_coding_goal_decomposition(self):
        planner = AutonomousPlanner()
        events = []
        get_event_bus().subscribe(EventType.PLAN_CREATED, lambda e: events.append(e.event_type))

        plan = planner.create_plan("Fix bug in user authentication and run tests")

        assert plan.status == PlanStatus.PLANNED
        assert len(plan.subtasks) == 3
        assert plan.subtasks[0].assigned_agent == "CodingAgent"
        assert plan.subtasks[2].name == "Execute Verification Tests"
        assert EventType.PLAN_CREATED in events

    def test_planner_research_goal_decomposition(self):
        planner = AutonomousPlanner()
        plan = planner.create_plan("Research quantum computing breakthroughs and compile report")

        assert len(plan.subtasks) == 3
        assert plan.subtasks[0].assigned_agent == "ResearchAgent"
        assert plan.subtasks[2].assigned_agent == "DocumentAgent"
        assert len(plan.verification_criteria) >= 1

    def test_planner_browser_goal_decomposition(self):
        planner = AutonomousPlanner()
        plan = planner.create_plan("Browse news site and extract headlines")

        assert len(plan.subtasks) == 3
        assert plan.subtasks[0].assigned_agent == "BrowserAgent"

    def test_planner_general_goal_decomposition(self):
        planner = AutonomousPlanner()
        plan = planner.create_plan("Review system health and disk metrics")

        assert len(plan.subtasks) == 3
        assert plan.subtasks[0].assigned_agent == "GeneralAssistantAgent"

    def test_planner_ai_augmented_success(self):
        ai_json = (
            '{"subtasks": ['
            '  {"name": "AI Step 1", "description": "desc 1", "assigned_agent": "CodingAgent", "required_tools": ["file_read"]},'
            '  {"name": "AI Step 2", "description": "desc 2", "assigned_agent": "CodingAgent", "required_tools": ["file_write"]}'
            '], "verification_criteria": ["Criteria 1"]}'
        )
        mock_brain = MockBrain(response_text=f"```json\n{ai_json}\n```")
        planner = AutonomousPlanner(brain=mock_brain)

        plan = planner.create_plan("Custom AI goal", use_ai=True)

        assert len(plan.subtasks) == 2
        assert plan.subtasks[0].name == "AI Step 1"
        assert plan.subtasks[1].dependencies == [plan.subtasks[0].id]

    def test_planner_ai_fallback_on_invalid_json(self):
        mock_brain = MockBrain(response_text="Not valid json at all")
        planner = AutonomousPlanner(brain=mock_brain)

        plan = planner.create_plan("Refactor test suite", use_ai=True)
        # Should fallback to deterministic coding plan
        assert len(plan.subtasks) == 3
        assert plan.subtasks[0].assigned_agent == "CodingAgent"
