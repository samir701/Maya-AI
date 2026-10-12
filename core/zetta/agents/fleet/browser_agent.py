"""Browser Agent in ZETTA Fleet."""

from typing import Optional
from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.browser import get_browser_manager
from core.zetta.tools.registry import get_tool_registry
from core.zetta.utils.logging import get_logger
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, PermissionLevel

logger = get_logger("agent_browser")


class BrowserAgent(BaseAgent):
    """Specialized agent for web navigation, element detection, and DOM extraction."""

    def __init__(
        self,
        name: str = "BrowserAgent",
        required_permission: PermissionLevel = PermissionLevel.MEDIUM,
        use_fake: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            description="Autonomous web browsing agent for navigation, DOM extraction, and web interaction.",
            capabilities=[AgentCapability.BROWSER],
            required_permission=required_permission,
        )
        self.browser_manager = get_browser_manager(use_fake=use_fake)
        self.tool_registry = get_tool_registry()

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        """Execute browser operations such as navigation or extraction."""
        tools_called = []
        try:
            target_url = task.metadata.get("url")
            if not target_url and "http" in task.description:
                words = task.description.split()
                for w in words:
                    if w.startswith("http://") or w.startswith("https://"):
                        target_url = w
                        break

            if not target_url:
                target_url = "https://example.com"

            # Execute navigation via tool registry to enforce security & audit logging
            nav_result = self.tool_registry.execute(
                "browser_navigate",
                input_data={"url": target_url},
                task_id=task.id,
            )
            tools_called.append("browser_navigate")

            # Extract page info
            page_result = self.tool_registry.execute(
                "browser_get_page",
                input_data={},
                task_id=task.id,
            )
            tools_called.append("browser_get_page")

            data = {
                "navigation": nav_result.data if nav_result.success else str(nav_result.error),
                "page": page_result.data if page_result.success else str(page_result.error),
                "url": target_url,
            }

            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=nav_result.success,
                data=data,
                steps_executed=len(tools_called),
                tools_called=tools_called,
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=False,
                error=ErrorInfo(code="BrowserExecutionError", message=str(e)),
                tools_called=tools_called,
            )
