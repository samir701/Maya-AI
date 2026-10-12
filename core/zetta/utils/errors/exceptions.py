"""Standardized ZETTA Exception Hierarchy."""

from typing import Any, Dict, Optional


class ZettaError(Exception):
    """Base exception for all ZETTA errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize error information to a dictionary."""
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} | Details: {self.details}"
        return f"[{self.code}] {self.message}"


class ConfigurationError(ZettaError):
    """Raised when configuration validation or loading fails."""
    pass


class AuthenticationError(ZettaError):
    """Raised when authentication credentials or checks fail."""
    pass


class AuthorizationError(ZettaError):
    """Raised when authorization checks fail or permissions are denied."""
    pass


class ValidationError(ZettaError):
    """Raised when data or schema validation fails."""
    pass


class ToolError(ZettaError):
    """Raised when tool execution, registration, or lookup fails."""
    pass


class AgentError(ZettaError):
    """Raised when agent execution or lifecycle management fails."""
    pass


class TaskError(ZettaError):
    """Raised when task creation, queueing, execution, or transition fails."""
    pass


class BrowserError(ZettaError):
    """Raised when browser automation driver or action fails."""
    pass


class IntegrationError(ZettaError):
    """Raised when external service integration fails."""
    pass


class RateLimitError(IntegrationError):
    """Raised when an external API rate limit or quota is exceeded."""
    pass


class TimeoutError(IntegrationError):
    """Raised when an operation or request exceeds configured timeout."""
    pass


class SecurityError(ZettaError):
    """Raised when security sandboxing or safety confirmation fails."""
    pass


class SandboxError(SecurityError):
    """Raised when an operation violates sandbox policies or system path boundaries."""
    pass


class NotFoundError(ZettaError):
    """Raised when a requested resource, skill, agent, or tool is not found."""
    pass


class RegistrationError(ZettaError):
    """Raised when registering a component fails."""
    pass


class ExecutionError(ZettaError):
    """Raised when executing a workflow, skill, or operation fails."""
    pass


