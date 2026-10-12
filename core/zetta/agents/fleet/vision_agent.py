"""Vision Agent in ZETTA Fleet."""

from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.tools.registry import get_tool_registry
from core.zetta.utils.logging import get_logger
from core.zetta.vision import get_vision_manager
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, PermissionLevel

logger = get_logger("agent_vision")


class VisionAgent(BaseAgent):
    """Specialized agent for screen capture, OCR, and visual element detection."""

    def __init__(
        self,
        name: str = "VisionAgent",
        required_permission: PermissionLevel = PermissionLevel.LOW,
        use_fake: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            description="Visual intelligence agent for screen observation, OCR reading, and UI element detection.",
            capabilities=[AgentCapability.VISION],
            required_permission=required_permission,
        )
        self.vision_manager = get_vision_manager(use_fake=use_fake)
        self.tool_registry = get_tool_registry()

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        """Execute screen inspection, OCR, or element detection."""
        tools_called = []
        try:
            # Capture screen information
            info_res = self.tool_registry.execute("vision_screen_info", input_data={}, task_id=task.id)
            tools_called.append("vision_screen_info")

            # Run OCR
            ocr_res = self.tool_registry.execute("vision_ocr", input_data={}, task_id=task.id)
            tools_called.append("vision_ocr")

            data = {
                "screen": info_res.data if info_res.success else None,
                "ocr": ocr_res.data if ocr_res.success else None,
            }

            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=True,
                data=data,
                steps_executed=len(tools_called),
                tools_called=tools_called,
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=False,
                error=ErrorInfo(code="VisionExecutionError", message=str(e)),
                tools_called=tools_called,
            )
