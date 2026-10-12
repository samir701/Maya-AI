"""Accessibility Agent in ZETTA Fleet."""

from typing import Optional
from core.zetta.accessibility.capabilities import AccessibilityCapabilityType
from core.zetta.accessibility.manager import AccessibilityManager, get_accessibility_manager
from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.utils.logging import get_logger
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, PermissionLevel

logger = get_logger("agent_accessibility")


class AccessibilityAgent(BaseAgent):
    """Specialized agent leveraging 25 composable UI automation and assistive capabilities."""

    def __init__(
        self,
        name: str = "AccessibilityAgent",
        required_permission: PermissionLevel = PermissionLevel.MEDIUM,
        accessibility_manager: Optional[AccessibilityManager] = None,
    ) -> None:
        super().__init__(
            name=name,
            description="Assistive UI interaction agent for desktop elements, OCR screen reading, keyboard/mouse automation, and window control.",
            capabilities=[AgentCapability.ACCESSIBILITY, AgentCapability.VISION],
            required_permission=required_permission,
        )
        self.accessibility_manager = accessibility_manager or get_accessibility_manager()

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        """Execute an accessibility operation specified in the task."""
        action_name = task.metadata.get("action", "inspect_active_ui")
        try:
            action_type = AccessibilityCapabilityType(action_name)
        except ValueError:
            action_type = AccessibilityCapabilityType.INSPECT_ACTIVE_UI

        params = task.metadata.get("params", {})
        action_res = self.accessibility_manager.execute_action(action_type, params=params)

        return AgentResult(
            agent_id=self.agent_id,
            task_id=task.id,
            success=action_res.success,
            data={"action": action_type.value, "result": action_res.data},
            error=ErrorInfo(code="AccessibilityActionFailed", message=action_res.error) if action_res.error else None,
            steps_executed=1,
            tools_called=[action_type.value],
        )
