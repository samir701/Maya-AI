"""Pure Python Zero-Dependency Voice Activity Detector (VAD)."""

import math
import struct
from abc import ABC, abstractmethod
from typing import Optional
from core.zetta.voice.models.vad import (
    SpeechActivityState,
    VADResult,
)


class VADDetector(ABC):
    """Abstract interface for Voice Activity Detection."""

    @abstractmethod
    def process_chunk(self, chunk_data: bytes) -> VADResult:
        """Analyze an audio chunk and return speech detection state."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset internal detector state."""
        ...


class EnergyVADDetector(VADDetector):
    """Zero-dependency energy/RMS-based Voice Activity Detector for 16-bit PCM mono audio."""

    def __init__(
        self,
        energy_threshold: float = 500.0,
        speech_onset_chunks: int = 2,
        speech_hangover_chunks: int = 5,
    ) -> None:
        self.energy_threshold = energy_threshold
        self.speech_onset_chunks = speech_onset_chunks
        self.speech_hangover_chunks = speech_hangover_chunks

        self._state = SpeechActivityState.SILENCE
        self._consecutive_speech_chunks = 0
        self._consecutive_silence_chunks = 0

    @property
    def current_state(self) -> SpeechActivityState:
        return self._state

    def reset(self) -> None:
        self._state = SpeechActivityState.SILENCE
        self._consecutive_speech_chunks = 0
        self._consecutive_silence_chunks = 0

    def calculate_rms(self, pcm_bytes: bytes) -> float:
        """Calculate RMS amplitude of 16-bit signed PCM mono samples."""
        if not pcm_bytes:
            return 0.0
        count = len(pcm_bytes) // 2
        if count == 0:
            return 0.0
        try:
            samples = struct.unpack(f"<{count}h", pcm_bytes[:count * 2])
            sum_squares = sum(s * s for s in samples)
            return math.sqrt(sum_squares / count)
        except Exception:
            return 0.0

    def process_chunk(self, chunk_data: bytes) -> VADResult:
        energy = self.calculate_rms(chunk_data)
        above_threshold = energy >= self.energy_threshold

        if above_threshold:
            self._consecutive_speech_chunks += 1
            self._consecutive_silence_chunks = 0

            if self._state == SpeechActivityState.SILENCE:
                if self._consecutive_speech_chunks >= self.speech_onset_chunks:
                    self._state = SpeechActivityState.SPEECH_ACTIVE
                else:
                    self._state = SpeechActivityState.SPEECH_POSSIBLE
            elif self._state in (SpeechActivityState.SPEECH_POSSIBLE, SpeechActivityState.SPEECH_ENDING):
                self._state = SpeechActivityState.SPEECH_ACTIVE

        else:
            self._consecutive_silence_chunks += 1
            self._consecutive_speech_chunks = 0

            if self._state == SpeechActivityState.SPEECH_ACTIVE:
                self._state = SpeechActivityState.SPEECH_ENDING

            elif self._state == SpeechActivityState.SPEECH_ENDING:
                if self._consecutive_silence_chunks >= self.speech_hangover_chunks:
                    self._state = SpeechActivityState.SILENCE

            elif self._state == SpeechActivityState.SPEECH_POSSIBLE:
                self._state = SpeechActivityState.SILENCE

        is_speech = self._state in (SpeechActivityState.SPEECH_ACTIVE, SpeechActivityState.SPEECH_ENDING)
        confidence = min(1.0, energy / (self.energy_threshold * 2.0)) if above_threshold else 0.0

        return VADResult(
            is_speech=is_speech,
            energy=energy,
            threshold=self.energy_threshold,
            confidence=confidence,
            state=self._state,
        )
