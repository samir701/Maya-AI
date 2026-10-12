"""Text-to-Speech (TTS) Provider Abstract Base Class."""

from abc import ABC, abstractmethod
from typing import List, Optional
from core.zetta.voice.models.tts import (
    SynthesisRequest,
    SynthesisResult,
    VoiceProfile,
)


class TTSProvider(ABC):
    """Abstract interface for speech synthesis providers."""

    @abstractmethod
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesize text into speech audio data."""
        ...

    @abstractmethod
    def list_voices(self) -> List[VoiceProfile]:
        """List available voices for this provider."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if TTS provider is operational."""
        ...
