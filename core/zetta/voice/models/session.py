"""Voice Session and Conversation Turn Models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class VoiceSessionState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass
class VoiceTurn:
    """A single interactive voice turn between user and system."""
    turn_id: str = field(default_factory=lambda: f"turn_{uuid4().hex[:8]}")
    user_transcript: str = ""
    assistant_response: str = ""
    tools_executed: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "user_transcript": self.user_transcript,
            "assistant_response": self.assistant_response,
            "tools_executed": self.tools_executed,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class VoiceSession:
    """Active or persisted voice conversation session."""
    session_id: str = field(default_factory=lambda: f"voice_session_{uuid4().hex[:8]}")
    state: VoiceSessionState = VoiceSessionState.IDLE
    turns: List[VoiceTurn] = field(default_factory=list)
    audio_device: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_turn(self, turn: VoiceTurn) -> None:
        self.turns.append(turn)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "turn_count": len(self.turns),
            "turns": [t.to_dict() for t in self.turns],
            "audio_device": self.audio_device,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
