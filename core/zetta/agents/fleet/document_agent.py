"""Document Agent in ZETTA Fleet."""

from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.ai.brain import get_ai_brain
from core.zetta.tools.registry import get_tool_registry
from core.zetta.utils.logging import get_logger
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, PermissionLevel

logger = get_logger("agent_document")


class DocumentAgent(BaseAgent):
    """Specialized agent for drafting, summarizing, formatting, and generating documents."""

    def __init__(
        self,
        name: str = "DocumentAgent",
        required_permission: PermissionLevel = PermissionLevel.LOW,
    ) -> None:
        super().__init__(
            name=name,
            description="Document specialist for compiling structured reports, summaries, and Markdown files.",
            capabilities=[AgentCapability.DOCUMENT],
            required_permission=required_permission,
        )
        self.tool_registry = get_tool_registry()

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        """Format and compile document content."""
        tools_called = []
        try:
            brain = get_ai_brain()
            prompt = (
                f"You are a technical document writer.\n"
                f"Task: {task.name}\n"
                f"Instructions: {task.description}\n"
                f"Metadata: {task.metadata}\n"
                f"Generate a well-structured Markdown document."
            )
            response = brain.think(prompt=prompt)
            doc_content = response.text

            # If an output path is provided in metadata, write using file_write tool
            output_path = task.metadata.get("output_path")
            if output_path and "file_write" in task.required_tools:
                write_res = self.tool_registry.execute(
                    "file_write",
                    input_data={"path": output_path, "content": doc_content},
                    task_id=task.id,
                )
                tools_called.append("file_write")

            data = {
                "document": doc_content,
                "length_chars": len(doc_content),
                "output_path": output_path,
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
                error=ErrorInfo(code="DocumentExecutionError", message=str(e)),
                tools_called=tools_called,
            )
