"""Voice Activity Detection Models."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class SpeechActivityState(str, Enum):
    SILENCE = "SILENCE"
    SPEECH_POSSIBLE = "SPEECH_POSSIBLE"
    SPEECH_ACTIVE = "SPEECH_ACTIVE"
    SPEECH_ENDING = "SPEECH_ENDING"


@dataclass
class VADResult:
    """Result of Voice Activity Detection evaluation on an audio chunk."""
    is_speech: bool
    energy: float
    threshold: float
    confidence: float = 1.0
    state: SpeechActivityState = SpeechActivityState.SILENCE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_speech": self.is_speech,
            "energy": round(self.energy, 2),
            "threshold": round(self.threshold, 2),
            "confidence": round(self.confidence, 2),
            "state": self.state.value,
        }
