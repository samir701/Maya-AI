"""ZETTA Tool Registry and Executor."""

from typing import Any, Callable, Dict, List, Optional
from core.zetta.events import Event, get_event_bus
from core.zetta.security import get_security_manager
from core.zetta.tools.base.base_tool import Tool
from core.zetta.utils.errors.exceptions import AuthorizationError, ToolError
from core.zetta.utils.logging import get_logger
from shared.types.contracts import ErrorInfo, ToolResult
from shared.types.enums import EventType

logger = get_logger("tool_registry")


class ToolRegistry:
    """Central registry managing tool registration and security-gated execution."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Discover and register all Phase 04 standard system, application, filesystem, terminal, and clipboard tools."""
        try:
            from core.zetta.tools.system import (
                SystemInfoTool, SystemUptimeTool, SystemDiskUsageTool,
                SystemMemoryUsageTool, SystemCpuUsageTool, SystemOsInfoTool,
                ProcessListTool, ProcessGetTool, ProcessIsRunningTool,
                ProcessStartTool, ProcessStopTool
            )
            from core.zetta.tools.applications import (
                ApplicationListTool, ApplicationFindTool, ApplicationOpenTool,
                ApplicationIsRunningTool, ApplicationCloseTool
            )
            from core.zetta.tools.filesystem import (
                FileListTool, FileExistsTool, FileReadTool, FileSearchTool,
                DirectoryCreateTool, FileCreateTool, FileWriteTool,
                FileCopyTool, FileMoveTool, FileDeleteTool
            )
            from core.zetta.tools.terminal import TerminalExecuteTool
            from core.zetta.tools.clipboard import ClipboardReadTool, ClipboardWriteTool
            from core.zetta.tools.vision import (
                VisionScreenInfoTool, VisionScreenCaptureTool, VisionOCRTool,
                VisionDetectUITool, VisionAnalyzeScreenTool
            )
            from core.zetta.tools.browser import (
                BrowserStatusTool, BrowserLaunchTool, BrowserCloseTool,
                BrowserNavigateTool, BrowserGetPageTool, BrowserDetectElementsTool,
                BrowserClickTool, BrowserTypeTool, BrowserKeyboardTool,
                BrowserScrollTool, BrowserHistoryTool, BrowserScreenshotTool
            )
            from core.zetta.tools.voice import (
                VoiceStatusTool, VoiceCaptureTool, VoiceTranscribeTool,
                VoiceSynthesizeTool, VoiceSessionTool
            )

            default_tools = [
                SystemInfoTool(), SystemUptimeTool(), SystemDiskUsageTool(),
                SystemMemoryUsageTool(), SystemCpuUsageTool(), SystemOsInfoTool(),
                ProcessListTool(), ProcessGetTool(), ProcessIsRunningTool(),
                ProcessStartTool(), ProcessStopTool(),
                ApplicationListTool(), ApplicationFindTool(), ApplicationOpenTool(),
                ApplicationIsRunningTool(), ApplicationCloseTool(),
                FileListTool(), FileExistsTool(), FileReadTool(), FileSearchTool(),
                DirectoryCreateTool(), FileCreateTool(), FileWriteTool(),
                FileCopyTool(), FileMoveTool(), FileDeleteTool(),
                TerminalExecuteTool(),
                ClipboardReadTool(), ClipboardWriteTool(),
                VisionScreenInfoTool(), VisionScreenCaptureTool(), VisionOCRTool(),
                VisionDetectUITool(), VisionAnalyzeScreenTool(),
                BrowserStatusTool(), BrowserLaunchTool(), BrowserCloseTool(),
                BrowserNavigateTool(), BrowserGetPageTool(), BrowserDetectElementsTool(),
                BrowserClickTool(), BrowserTypeTool(), BrowserKeyboardTool(),
                BrowserScrollTool(), BrowserHistoryTool(), BrowserScreenshotTool(),
                VoiceStatusTool(), VoiceCaptureTool(), VoiceTranscribeTool(),
                VoiceSynthesizeTool(), VoiceSessionTool(),
            ]

            for t in default_tools:
                self._tools[t.name] = t
        except Exception as e:
            logger.warning(f"Error during default tool registration: {e}")

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        if tool.name in self._tools:
            if type(self._tools[tool.name]) is type(tool):
                logger.debug(f"Tool '{tool.name}' already registered; updating registration idempotently.")
                self._tools[tool.name] = tool
                return
            logger.warning(f"Overwriting existing tool registration: '{tool.name}'")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool '{tool.name}' [Permission: {tool.required_permission.value}]")

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name."""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool '{name}'")
            return True
        return False


    def get(self, name: str) -> Tool:
        """Retrieve tool by name."""
        if name not in self._tools:
            raise ToolError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_tools(self) -> List[Dict[str, Any]]:
        """List metadata of all registered tools."""
        return [tool.get_metadata() for tool in self._tools.values()]

    def execute(
        self,
        name: str,
        input_data: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        confirmation_callback: Optional[Callable[[str], bool]] = None,
    ) -> ToolResult:
        """Execute registered tool with security checks, confirmation, audit logging, and event bus notifications."""
        input_data = input_data or {}
        tool = self.get(name)
        security_manager = get_security_manager()
        event_bus = get_event_bus()

        # 1. Permission check
        if not security_manager.check_tool_permission(tool.required_permission):
            err_msg = f"Cannot execute tool '{name}': Required permission level '{tool.required_permission.value}' exceeds current grant."
            security_manager.audit_logger.log_event(
                action=f"tool_execute:{name}",
                actor="system",
                resource=name,
                status="REJECTED_PERMISSION",
                details={"input": input_data, "permission": tool.required_permission.value},
            )
            raise AuthorizationError(err_msg)

        # 2. Confirmation check
        requires_conf = tool.requires_confirmation or tool.dangerous or security_manager.requires_user_confirmation(tool.required_permission)
        if requires_conf:
            event_bus.publish(
                Event(
                    event_type=EventType.USER_CONFIRMATION_REQUIRED,
                    payload={"tool_name": name, "input": input_data, "permission": tool.required_permission.value},
                    task_id=task_id,
                )
            )

            confirmed = False
            if confirmation_callback:
                confirmed = confirmation_callback(f"Confirm execution of tool '{name}' [Permission: {tool.required_permission.value}]?")
            else:
                try:
                    from core.zetta.interaction.confirmation import ConfirmationInterface
                    confirmed = ConfirmationInterface().request_confirmation(
                        f"Confirm execution of high-risk tool '{name}'?",
                        level=tool.required_permission,
                    )
                except Exception:
                    confirmed = False

            if not confirmed:
                security_manager.audit_logger.log_event(
                    action=f"tool_execute:{name}",
                    actor="user",
                    resource=name,
                    status="CANCELLED_CONFIRMATION",
                    details={"input": input_data},
                )
                return ToolResult(
                    tool_name=name,
                    success=False,
                    error=ErrorInfo(
                        code="ConfirmationRejected",
                        message=f"Tool execution for '{name}' was cancelled by user.",
                        details={"input": input_data},
                    ),
                    execution_time_ms=0.0,
                )

        # 3. Publish TOOL_STARTED & Audit
        event_bus.publish(
            Event(
                event_type=EventType.TOOL_STARTED,
                payload={"tool_name": name, "input": input_data},
                task_id=task_id,
            )
        )
        security_manager.audit_logger.log_event(
            action=f"tool_execute:{name}",
            actor="system",
            resource=name,
            status="STARTED",
            details={"input": input_data},
        )

        # 4. Execute tool
        result = tool.execute(input_data)

        # 5. Publish TOOL_COMPLETED / TOOL_FAILED & Audit
        if result.success:
            event_bus.publish(
                Event(
                    event_type=EventType.TOOL_COMPLETED,
                    payload={"tool_name": name, "execution_time_ms": result.execution_time_ms},
                    task_id=task_id,
                )
            )
            security_manager.audit_logger.log_event(
                action=f"tool_execute:{name}",
                actor="system",
                resource=name,
                status="COMPLETED",
                details={"execution_time_ms": result.execution_time_ms},
            )
        else:
            event_bus.publish(
                Event(
                    event_type=EventType.TOOL_FAILED,
                    payload={
                        "tool_name": name,
                        "error": result.error.message if result.error else "Unknown error",
                    },
                    task_id=task_id,
                )
            )
            security_manager.audit_logger.log_event(
                action=f"tool_execute:{name}",
                actor="system",
                resource=name,
                status="FAILED",
                details={"error": result.error.message if result.error else "Unknown error"},
            )

        return result


_tool_registry_instance: ToolRegistry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _tool_registry_instance

