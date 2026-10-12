"""Research Agent in ZETTA Fleet."""

from typing import Any, Dict, List
from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.ai.brain import get_ai_brain
from core.zetta.tools.registry import get_tool_registry
from core.zetta.utils.logging import get_logger
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, PermissionLevel

logger = get_logger("agent_research")


class ResearchAgent(BaseAgent):
    """Specialized agent for data collection, multi-source synthesis, and citation."""

    def __init__(
        self,
        name: str = "ResearchAgent",
        required_permission: PermissionLevel = PermissionLevel.LOW,
    ) -> None:
        super().__init__(
            name=name,
            description="Deep investigation agent for source gathering, structured extraction, and synthesis.",
            capabilities=[AgentCapability.RESEARCH],
            required_permission=required_permission,
        )
        self.tool_registry = get_tool_registry()

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        """Collect source evidence and synthesize structured findings."""
        tools_called = []
        try:
            sources: List[Dict[str, Any]] = []

            # If specific tools are requested, execute them
            for tool_name in task.required_tools:
                if self.tool_registry.get(tool_name):
                    res = self.tool_registry.execute(tool_name, input_data={}, task_id=task.id)
                    tools_called.append(tool_name)
                    if res.success:
                        sources.append({"source": tool_name, "content": res.data})

            brain = get_ai_brain()
            prompt = (
                f"You are a thorough research analyst.\n"
                f"Objective: {task.name}\n"
                f"Details: {task.description}\n"
                f"Gathered Evidence: {sources}\n"
                f"Synthesize key insights with citations and summary bullets."
            )
            response = brain.think(prompt=prompt)

            data = {
                "findings": response.text,
                "sources_consulted": [s["source"] for s in sources],
                "citation_count": len(sources),
            }

            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=True,
                data=data,
                steps_executed=max(1, len(tools_called)),
                tools_called=tools_called,
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=False,
                error=ErrorInfo(code="ResearchExecutionError", message=str(e)),
                tools_called=tools_called,
            )
