"""Speech-to-Text (STT) Provider Abstract Base Class."""

from abc import ABC, abstractmethod
from typing import Iterator, Optional
from core.zetta.voice.models.audio import AudioChunk, AudioData
from core.zetta.voice.models.stt import TranscriptionResult


class STTProvider(ABC):
    """Abstract interface for speech recognition providers."""

    @abstractmethod
    def transcribe(self, audio: AudioData) -> TranscriptionResult:
        """Transcribe an AudioData container into text."""
        ...

    @abstractmethod
    def transcribe_stream(
        self,
        chunk_stream: Iterator[AudioChunk],
    ) -> Iterator[TranscriptionResult]:
        """Transcribe an audio chunk stream in real-time."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if STT provider is initialized and ready."""
        ...
