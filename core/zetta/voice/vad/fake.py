"""Deterministic Fake Voice Activity Detector for Unit Testing."""

from typing import List, Optional
from core.zetta.voice.models.vad import (
    SpeechActivityState,
    VADResult,
)
from core.zetta.voice.vad.detector import VADDetector


class FakeVADDetector(VADDetector):
    """Deterministic VAD detector with scripted speech/silence outcomes."""

    def __init__(self, scripted_states: Optional[List[bool]] = None) -> None:
        self.scripted_states = list(scripted_states) if scripted_states is not None else [True, True, True, False, False]
        self._index = 0
        self.always_speech = False
        self.always_silence = False

    def reset(self) -> None:
        self._index = 0

    def process_chunk(self, chunk_data: bytes) -> VADResult:
        if self.always_speech:
            is_speech = True
        elif self.always_silence:
            is_speech = False
        elif self._index < len(self.scripted_states):
            is_speech = self.scripted_states[self._index]
            self._index += 1
        else:
            is_speech = False

        state = SpeechActivityState.SPEECH_ACTIVE if is_speech else SpeechActivityState.SILENCE
        return VADResult(
            is_speech=is_speech,
            energy=1000.0 if is_speech else 50.0,
            threshold=500.0,
            confidence=1.0,
            state=state,
        )
