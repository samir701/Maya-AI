"""ZETTA Autonomous Planner for Goal Decomposition and Execution Planning."""

import json
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.zetta.agents.planner.task_graph import TaskGraph
from core.zetta.events import Event, get_event_bus
from core.zetta.utils.logging import get_logger
from shared.types.contracts import SubTask, TaskPlan
from shared.types.enums import EventType, PlanStatus, TaskStatus

logger = get_logger("autonomous_planner")


class AutonomousPlanner:
    """Decomposes high-level user goals into structured DAG execution plans."""

    def __init__(self, brain: Optional[Any] = None) -> None:
        self._brain = brain
        self.event_bus = get_event_bus()

    def create_plan(
        self,
        goal: str,
        use_ai: bool = False,
        context_hints: Optional[Dict[str, Any]] = None,
    ) -> TaskPlan:
        """Create a validated TaskPlan from a user goal."""
        goal_clean = goal.strip()
        logger.info(f"Generating plan for goal: '{goal_clean}'")

        subtasks: List[SubTask] = []
        criteria: List[str] = []

        if use_ai and self._brain is not None:
            try:
                subtasks, criteria = self._plan_with_ai(goal_clean, context_hints)
            except Exception as e:
                logger.warning(f"AI planning failed ({e}). Falling back to deterministic planner.")
                subtasks, criteria = self._plan_deterministic(goal_clean)
        else:
            subtasks, criteria = self._plan_deterministic(goal_clean)

        plan = TaskPlan(
            goal=goal_clean,
            subtasks=subtasks,
            status=PlanStatus.PLANNED,
            verification_criteria=criteria,
            metadata={"planner": "autonomous_planner", "ai_augmented": use_ai},
        )

        # Validate DAG
        graph = TaskGraph(subtasks)
        if not graph.validate_dag():
            raise ValueError(f"Planner generated an invalid cyclic task graph for goal: '{goal_clean}'")

        logger.info(f"Created TaskPlan [ID: {plan.id}] with {len(subtasks)} subtasks.")

        self.event_bus.publish(
            Event(
                event_type=EventType.PLAN_CREATED,
                payload={"plan_id": plan.id, "goal": plan.goal, "subtask_count": len(subtasks)},
                task_id=plan.id,
            )
        )
        return plan

    def _plan_deterministic(self, goal: str) -> tuple[List[SubTask], List[str]]:
        """Fallback deterministic heuristic planning decomposing goals into structured tasks."""
        goal_lower = goal.lower()
        subtasks: List[SubTask] = []
        criteria: List[str] = []

        # 1. Coding / Test / Refactor workflows
        if re.search(r"\b(code|coding|refactor|bug|fix|unit test|implement|script)\b", goal_lower):
            s1 = SubTask(
                name="Inspect Project Workspace",
                description=f"Inspect workspace files and dependencies relevant to: {goal}",
                assigned_agent="CodingAgent",
                required_tools=["file_list", "file_read"],
            )
            s2 = SubTask(
                name="Apply Code Modifications",
                description=f"Generate or modify source code to accomplish: {goal}",
                assigned_agent="CodingAgent",
                dependencies=[s1.id],
                required_tools=["file_write", "file_create"],
            )
            s3 = SubTask(
                name="Execute Verification Tests",
                description="Run automated tests to verify code modifications",
                assigned_agent="CodingAgent",
                dependencies=[s2.id],
                required_tools=["terminal_execute"],
            )
            subtasks = [s1, s2, s3]
            criteria = ["All modified files pass syntax checks", "Automated tests exit code 0"]

        # 2. Research + Document workflows
        elif re.search(r"\b(research|investigate|study|analyze|document|report|summary)\b", goal_lower):
            s1 = SubTask(
                name="Gather Research Sources",
                description=f"Collect data points and inspect background for: {goal}",
                assigned_agent="ResearchAgent",
                required_tools=["browser_navigate", "file_read"],
            )
            s2 = SubTask(
                name="Synthesize Findings",
                description="Analyze collected data, extract key insights, and organize citations",
                assigned_agent="ResearchAgent",
                dependencies=[s1.id],
                required_tools=[],
            )
            s3 = SubTask(
                name="Compile Document Report",
                description="Format structured summary report and persist document",
                assigned_agent="DocumentAgent",
                dependencies=[s2.id],
                required_tools=["file_write"],
            )
            subtasks = [s1, s2, s3]
            criteria = ["Findings synthesized with source attribution", "Structured report created"]

        # 3. Web / Browser automation workflows
        elif re.search(r"\b(browse|browser|web|scrape|search online|navigate)\b", goal_lower):
            s1 = SubTask(
                name="Navigate Target Webpage",
                description=f"Open browser and navigate to target site for: {goal}",
                assigned_agent="BrowserAgent",
                required_tools=["browser_launch", "browser_navigate"],
            )
            s2 = SubTask(
                name="Extract Web Elements and Content",
                description="Detect page elements, text content, and structured information",
                assigned_agent="BrowserAgent",
                dependencies=[s1.id],
                required_tools=["browser_detect_elements", "browser_get_page"],
            )
            s3 = SubTask(
                name="Summarize Extracted Results",
                description="Process web data and present final structured summary",
                assigned_agent="GeneralAssistantAgent",
                dependencies=[s2.id],
                required_tools=[],
            )
            subtasks = [s1, s2, s3]
            criteria = ["Page navigated and content extracted successfully"]

        # 4. General / Default multi-step fallback
        else:
            s1 = SubTask(
                name="Analyze Requirements",
                description=f"Deconstruct objective and assess required tools: {goal}",
                assigned_agent="GeneralAssistantAgent",
                required_tools=["system_info"],
            )
            s2 = SubTask(
                name="Execute Core Operations",
                description=f"Perform operational steps for: {goal}",
                assigned_agent="GeneralAssistantAgent",
                dependencies=[s1.id],
                required_tools=[],
            )
            s3 = SubTask(
                name="Verify and Finalize Result",
                description="Confirm goal conditions are fully satisfied",
                assigned_agent="GeneralAssistantAgent",
                dependencies=[s2.id],
                required_tools=[],
            )
            subtasks = [s1, s2, s3]
            criteria = ["Core operation completed", "Verification criteria satisfied"]

        return subtasks, criteria

    def _plan_with_ai(self, goal: str, context_hints: Optional[Dict[str, Any]] = None) -> tuple[List[SubTask], List[str]]:
        """Use AI brain to decompose an arbitrary user goal into structured subtasks."""
        prompt = (
            f"Decompose the following user goal into a JSON plan with sequential subtasks.\n"
            f"Goal: {goal}\n"
            f"Context: {json.dumps(context_hints or {})}\n"
            f"Return JSON format:\n"
            f"{{\n"
            f'  "subtasks": [\n'
            f'    {{"name": "...", "description": "...", "assigned_agent": "...", "required_tools": []}}\n'
            f"  ],\n"
            f'  "verification_criteria": ["..."]\n'
            f"}}"
        )
        response = self._brain.think(prompt=prompt)
        raw_text = response.text.strip()

        # Parse JSON from response
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        data = json.loads(raw_text)
        raw_subtasks = data.get("subtasks", [])
        criteria = data.get("verification_criteria", ["All subtasks completed successfully"])

        subtasks: List[SubTask] = []
        prev_id: Optional[str] = None

        for item in raw_subtasks:
            st = SubTask(
                name=item.get("name", "Unnamed Subtask"),
                description=item.get("description", ""),
                assigned_agent=item.get("assigned_agent", "GeneralAssistantAgent"),
                required_tools=item.get("required_tools", []),
                dependencies=[prev_id] if prev_id else [],
            )
            subtasks.append(st)
            prev_id = st.id

        if not subtasks:
            return self._plan_deterministically(goal)

        return subtasks, criteria
