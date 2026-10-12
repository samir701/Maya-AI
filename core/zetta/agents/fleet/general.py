"""General Assistant Agent in ZETTA Fleet."""

from typing import Optional
from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.ai.brain import get_ai_brain
from core.zetta.tools.registry import get_tool_registry
from core.zetta.utils.logging import get_logger
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, PermissionLevel

logger = get_logger("agent_general")


class GeneralAssistantAgent(BaseAgent):
    """Primary conversational, reasoning, and coordination agent."""

    def __init__(
        self,
        name: str = "GeneralAssistantAgent",
        required_permission: PermissionLevel = PermissionLevel.LOW,
    ) -> None:
        super().__init__(
            name=name,
            description="Versatile assistant for conversational reasoning, intent analysis, and general tasks.",
            capabilities=[AgentCapability.GENERAL],
            required_permission=required_permission,
        )
        self.tool_registry = get_tool_registry()

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        """Execute general reasoning or dispatch tools."""
        tools_called = []
        try:
            # Execute requested tools if any are specified
            tool_outputs = {}
            for tool_name in task.required_tools:
                if self.tool_registry.get(tool_name):
                    res = self.tool_registry.execute(tool_name, input_data={}, task_id=task.id)
                    tools_called.append(tool_name)
                    tool_outputs[tool_name] = res.data if res.success else str(res.error)

            # Synthesize answer using AI brain if available
            brain = get_ai_brain()
            prompt = (
                f"Task: {task.name}\n"
                f"Description: {task.description}\n"
                f"Tool Outputs: {tool_outputs}\n"
                f"Provide a concise operational response."
            )
            response = brain.think(prompt=prompt)
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=True,
                data={"summary": response.text, "tool_outputs": tool_outputs},
                steps_executed=max(1, len(tools_called)),
                tools_called=tools_called,
            )
        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=False,
                error=ErrorInfo(code="GeneralExecutionError", message=str(e)),
                tools_called=tools_called,
            )
