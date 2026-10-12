"""Deterministic Fake Speech-to-Text (STT) Provider for Testing."""

from typing import Iterator, List, Optional
from core.zetta.voice.models.audio import AudioChunk, AudioData
from core.zetta.voice.models.stt import (
    TranscriptionResult,
    TranscriptionSegment,
)
from core.zetta.voice.speech_to_text.base import STTProvider


class FakeSTTProvider(STTProvider):
    """Deterministic offline STT provider."""

    def __init__(self, default_text: str = "Hello ZETTA confirm voice initialization") -> None:
        self.default_text = default_text
        self.next_transcription: Optional[str] = None
        self.transcription_history: List[str] = []

    def set_next_transcription(self, text: str) -> None:
        """Queue the next transcription response."""
        self.next_transcription = text

    def transcribe(self, audio: AudioData) -> TranscriptionResult:
        if not audio.data:
            return TranscriptionResult(
                text="",
                confidence=0.0,
                duration_ms=0.0,
                segments=[],
            )

        text = self.next_transcription if self.next_transcription is not None else self.default_text
        self.next_transcription = None  # Reset one-shot
        self.transcription_history.append(text)

        duration_ms = audio.duration_seconds * 1000.0 if audio.duration_seconds > 0 else 500.0

        segment = TranscriptionSegment(
            text=text,
            start_time=0.0,
            end_time=audio.duration_seconds,
            confidence=0.98,
        )

        return TranscriptionResult(
            text=text,
            confidence=0.98,
            duration_ms=duration_ms,
            language="en",
            segments=[segment],
            is_final=True,
        )

    def transcribe_stream(
        self,
        chunk_stream: Iterator[AudioChunk],
    ) -> Iterator[TranscriptionResult]:
        total_chunks = 0
        for _ in chunk_stream:
            total_chunks += 1

        text = self.next_transcription if self.next_transcription is not None else self.default_text
        self.next_transcription = None
        self.transcription_history.append(text)

        yield TranscriptionResult(
            text=text,
            confidence=0.95,
            duration_ms=total_chunks * 64.0,
            language="en",
            segments=[TranscriptionSegment(text=text, start_time=0.0, end_time=1.0)],
            is_final=True,
        )

    def is_available(self) -> bool:
        return True
