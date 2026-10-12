"""Unified Computer Agent connecting desktop, filesystem, terminal, clipboard, browser, and vision."""

from typing import Any, Dict, List, Optional
from core.zetta.accessibility import get_accessibility_manager
from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.browser import get_browser_manager
from core.zetta.tools.registry import get_tool_registry
from core.zetta.utils.logging import get_logger
from core.zetta.vision import get_vision_manager
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, PermissionLevel

logger = get_logger("agent_computer")


class UnifiedComputerAgent(BaseAgent):
    """Full PC Control agent orchestrating desktop, applications, filesystem,

    terminal, clipboard, vision, and browser capabilities into a unified operational interface.
    """

    def __init__(
        self,
        name: str = "UnifiedComputerAgent",
        required_permission: PermissionLevel = PermissionLevel.HIGH,
        use_fake: bool = False,
        confirmation_callback: Optional[Any] = None,
    ) -> None:
        super().__init__(
            name=name,
            description="Unified PC control agent coordinating desktop, applications, filesystem, terminal, clipboard, vision, and browser.",
            capabilities=[
                AgentCapability.COMPUTER,
                AgentCapability.GENERAL,
                AgentCapability.BROWSER,
                AgentCapability.VISION,
                AgentCapability.ACCESSIBILITY,
            ],
            required_permission=required_permission,
        )
        self.tool_registry = get_tool_registry()
        self.browser_manager = get_browser_manager(use_fake=use_fake)
        self.vision_manager = get_vision_manager(use_fake=use_fake)
        self.accessibility_manager = get_accessibility_manager()
        self.confirmation_callback = confirmation_callback

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        """Execute multi-subsystem computer operations."""
        tools_called: List[str] = []
        action_results: Dict[str, Any] = {}

        try:
            # 1. Execute any explicit sequence of sub-actions if provided in metadata
            actions: List[Dict[str, Any]] = task.metadata.get("actions", [])

            if not actions and task.required_tools:
                # Default to executing required tools in order
                actions = [{"tool": t, "input": {}} for t in task.required_tools]

            if not actions:
                # Default inspection action
                actions = [{"tool": "system_info", "input": {}}]

            for action in actions:
                tool_name = action.get("tool")
                input_data = action.get("input", {})

                if tool_name and self.tool_registry.get(tool_name):
                    res = self.tool_registry.execute(
                        tool_name,
                        input_data=input_data,
                        task_id=task.id,
                        confirmation_callback=self.confirmation_callback,
                    )
                    tools_called.append(tool_name)
                    action_results[tool_name] = res.data if res.success else str(res.error)

            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=True,
                data={
                    "actions_executed": len(actions),
                    "action_results": action_results,
                    "summary": f"Completed unified computer workflow with {len(tools_called)} actions",
                },
                steps_executed=max(1, len(tools_called)),
                tools_called=tools_called,
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=False,
                error=ErrorInfo(code="ComputerExecutionError", message=str(e)),
                tools_called=tools_called,
            )
