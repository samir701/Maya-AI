"""Text-to-Speech (TTS) Data Models."""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from core.zetta.voice.models.audio import AudioData


@dataclass
class VoiceProfile:
    """Voice persona descriptor."""
    id: str
    name: str
    gender: str = "neutral"
    language: str = "en"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "gender": self.gender,
            "language": self.language,
        }


@dataclass
class SynthesisRequest:
    """Request payload for text-to-speech synthesis."""
    text: str
    voice: Optional[str] = None
    speed: float = 1.0
    pitch: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "voice": self.voice,
            "speed": self.speed,
            "pitch": self.pitch,
        }


@dataclass
class SynthesisResult:
    """Synthesized speech output."""
    audio: AudioData
    duration_ms: float = 0.0
    format: str = "wav"
    characters: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audio": self.audio.to_dict(),
            "duration_ms": round(self.duration_ms, 2),
            "format": self.format,
            "characters": self.characters,
        }
