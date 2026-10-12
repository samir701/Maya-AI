"""Speech-to-Text (STT) Data Models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TranscriptionSegment:
    """Timed speech segment within a transcript."""
    text: str
    start_time: float
    end_time: float
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "start_time": round(self.start_time, 2),
            "end_time": round(self.end_time, 2),
            "confidence": round(self.confidence, 2),
        }


@dataclass
class TranscriptionResult:
    """Complete output of a speech recognition operation."""
    text: str
    confidence: float = 1.0
    duration_ms: float = 0.0
    language: str = "en"
    segments: List[TranscriptionSegment] = field(default_factory=list)
    is_final: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 2),
            "duration_ms": round(self.duration_ms, 2),
            "language": self.language,
            "segments": [s.to_dict() for s in self.segments],
            "is_final": self.is_final,
            "error": self.error,
        }
