"""Base Abstract Tool Class for ZETTA."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict
from shared.types.contracts import ErrorInfo, ToolResult
from shared.types.enums import PermissionLevel


class Tool(ABC):
    """Abstract Base Class for all ZETTA tools."""

    name: str
    description: str
    required_permission: PermissionLevel = PermissionLevel.LOW
    category: str = "general"
    requires_confirmation: bool = False
    dangerous: bool = False
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}

    @abstractmethod
    def run(self, input_data: Dict[str, Any]) -> Any:
        """Core tool logic implementation."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Return standardized tool metadata dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "required_permission": self.required_permission.value,
            "requires_confirmation": self.requires_confirmation,
            "dangerous": self.dangerous,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }

    def execute(self, input_data: Dict[str, Any]) -> ToolResult:
        """Standardized wrapper executing the tool with error handling and timing metrics."""
        start_time = time.perf_counter()
        try:
            result_data = self.run(input_data or {})
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                tool_name=self.name,
                success=True,
                data=result_data,
                execution_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            error_info = ErrorInfo(
                code=e.__class__.__name__,
                message=str(e),
                details={"input": input_data},
            )
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=error_info,
                execution_time_ms=elapsed_ms,
            )

