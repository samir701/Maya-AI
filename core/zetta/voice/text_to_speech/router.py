"""ZETTA Text-to-Speech (TTS) Routing and Fallback Orchestration."""

import time
from typing import Any, Dict, List, Optional
from core.zetta.config import get_settings
from core.zetta.utils.logging import get_logger
from core.zetta.voice.models.tts import (
    SynthesisRequest,
    SynthesisResult,
    VoiceProfile,
)
from core.zetta.voice.text_to_speech.base import TTSProvider
from core.zetta.voice.text_to_speech.errors import TTSFallbackFailedError
from core.zetta.voice.text_to_speech.fake import FakeTTSProvider
from core.zetta.voice.text_to_speech.groq import GroqTTSProvider
from core.zetta.voice.text_to_speech.kokoro import KokoroTTSProvider

logger = get_logger("tts_router")


class TTSRouter(TTSProvider):
    """Orchestrates TTS request routing between primary (Kokoro) and fallback (Groq Orpheus) engines."""

    def __init__(
        self,
        primary_provider: Optional[TTSProvider] = None,
        fallback_provider: Optional[TTSProvider] = None,
        fallback_enabled: Optional[bool] = None,
        configured_mode: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        v_cfg = getattr(settings, "voice", None)

        self.configured_mode = (
            configured_mode
            or getattr(v_cfg, "tts_provider", "fake")
        ).lower()

        self.fallback_enabled = (
            fallback_enabled
            if fallback_enabled is not None
            else getattr(v_cfg, "tts_fallback_enabled", True)
        )

        # 1. Initialize Primary Provider
        if primary_provider:
            self.primary = primary_provider
        elif self.configured_mode == "fake":
            self.primary = FakeTTSProvider()
        elif self.configured_mode == "groq":
            self.primary = GroqTTSProvider()
        elif self.configured_mode == "kokoro":
            self.primary = KokoroTTSProvider()
        else:
            # Default or local
            self.primary = KokoroTTSProvider()

        # 2. Initialize Fallback Provider
        if fallback_provider:
            self.fallback = fallback_provider
        elif self.fallback_enabled and self.configured_mode == "kokoro":
            self.fallback = GroqTTSProvider()
        else:
            self.fallback = None

        self._fallback_count = 0
        self._last_fallback_time: Optional[float] = None
        self._last_used_provider = self.primary.__class__.__name__

    def __repr__(self) -> str:
        fb_name = self.fallback.__class__.__name__ if self.fallback else "None"
        return f"<TTSRouter primary={self.primary.__class__.__name__} fallback={fb_name} fallback_enabled={self.fallback_enabled}>"

    @property
    def last_used_provider(self) -> str:
        return self._last_used_provider

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesize text into speech audio with automatic fallback on failure."""
        try:
            result = self.primary.synthesize(request)
            self._last_used_provider = self.primary.__class__.__name__
            return result
        except Exception as primary_error:
            logger.warning(
                f"Primary TTS provider '{self.primary.__class__.__name__}' failed: {primary_error}"
            )

            # Check if fallback is eligible and configured
            if self.fallback_enabled and self.fallback is not None:
                logger.info(
                    f"Falling back to secondary TTS provider '{self.fallback.__class__.__name__}'..."
                )
                try:
                    result = self.fallback.synthesize(request)
                    self._fallback_count += 1
                    self._last_fallback_time = time.time()
                    self._last_used_provider = self.fallback.__class__.__name__
                    return result
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback TTS provider '{self.fallback.__class__.__name__}' also failed: {fallback_error}"
                    )
                    raise TTSFallbackFailedError(
                        f"Primary TTS failed ({primary_error}) and fallback TTS failed ({fallback_error})"
                    )

            # No fallback available or enabled
            raise primary_error

    def list_voices(self) -> List[VoiceProfile]:
        """Return available voices from primary provider."""
        return self.primary.list_voices()

    def is_available(self) -> bool:
        """Check if at least one engine is operational."""
        if self.primary.is_available():
            return True
        if self.fallback_enabled and self.fallback and self.fallback.is_available():
            return True
        return False

    def status(self) -> Dict[str, Any]:
        """Return routing telemetry and sub-provider status."""
        primary_status = (
            self.primary.status()
            if hasattr(self.primary, "status")
            else {"provider": self.primary.__class__.__name__, "available": self.primary.is_available()}
        )
        return {
            "mode": self.configured_mode,
            "primary": primary_status,
            "fallback_enabled": self.fallback_enabled,
            "fallback_provider": self.fallback.__class__.__name__ if self.fallback else "None",
            "fallback_count": self._fallback_count,
            "last_used_provider": self._last_used_provider,
        }
