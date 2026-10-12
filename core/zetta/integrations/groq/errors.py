"""Groq Integration Error Types."""

from core.zetta.utils.errors import AuthenticationError, IntegrationError, RateLimitError, TimeoutError


class GroqAPIKeyMissingError(AuthenticationError):
    """Raised when GROQ_API_KEY is not configured."""
    def __init__(self, message: str = "GROQ_API_KEY is not set in environment or configuration.") -> None:
        super().__init__(message)
        self.code = "GROQ_API_KEY_MISSING"


class GroqAuthError(AuthenticationError):
    """Raised when Groq API authentication fails (401/403)."""
    def __init__(self, message: str = "Groq authentication failed. Verify GROQ_API_KEY.") -> None:
        super().__init__(message)
        self.code = "GROQ_AUTH_FAILED"


class GroqRateLimitError(RateLimitError):
    """Raised when Groq API rate limit or quota is exceeded (429)."""
    def __init__(self, message: str = "Groq rate limit exceeded.") -> None:
        super().__init__(message)
        self.code = "GROQ_RATE_LIMITED"


class GroqTimeoutError(TimeoutError):
    """Raised when Groq API request times out."""
    def __init__(self, message: str = "Groq request timed out.") -> None:
        super().__init__(message)
        self.code = "GROQ_TIMEOUT"


class GroqNetworkError(IntegrationError):
    """Raised when Groq API network connection fails."""
    def __init__(self, message: str = "Groq network connection failed.") -> None:
        super().__init__(message)
        self.code = "GROQ_NETWORK_ERROR"
