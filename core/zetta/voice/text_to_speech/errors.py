"""Kokoro & Speech Synthesis Error Types."""

from core.zetta.utils.errors import IntegrationError, TimeoutError


class KokoroError(IntegrationError):
    """Base error for Kokoro TTS engine."""
    def __init__(self, message: str, code: str = "KOKORO_ERROR") -> None:
        super().__init__(message)
        self.code = code


class KokoroUnavailableError(KokoroError):
    """Raised when Kokoro backend or model weights are missing."""
    def __init__(self, message: str = "Kokoro TTS engine or model weights not available.") -> None:
        super().__init__(message, code="KOKORO_UNAVAILABLE")


class KokoroLoadFailedError(KokoroError):
    """Raised when loading Kokoro model fails."""
    def __init__(self, message: str = "Failed to load Kokoro TTS model.") -> None:
        super().__init__(message, code="KOKORO_LOAD_FAILED")


class KokoroInferenceError(KokoroError):
    """Raised when Kokoro speech synthesis fails."""
    def __init__(self, message: str = "Kokoro speech synthesis inference failed.") -> None:
        super().__init__(message, code="KOKORO_INFERENCE_FAILED")


class KokoroTimeoutError(TimeoutError):
    """Raised when Kokoro speech synthesis exceeds configured timeout."""
    def __init__(self, message: str = "Kokoro TTS generation timed out.") -> None:
        super().__init__(message)
        self.code = "KOKORO_TIMEOUT"


class KokoroUnsupportedDeviceError(KokoroError):
    """Raised when requested acceleration device is not supported."""
    def __init__(self, message: str = "Selected device is not supported for Kokoro.") -> None:
        super().__init__(message, code="KOKORO_UNSUPPORTED_DEVICE")


class TTSFallbackFailedError(IntegrationError):
    """Raised when both primary and fallback TTS fail."""
    def __init__(self, message: str = "TTS generation failed on both primary and fallback providers.") -> None:
        super().__init__(message)
        self.code = "TTS_FALLBACK_FAILED"
