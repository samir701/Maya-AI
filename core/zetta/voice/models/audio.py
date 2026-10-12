"""Audio Data Models for ZETTA Voice Subsystem."""

import math
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class AudioFormat:
    """Audio specification parameters."""
    sample_rate: int = 16000  # 16kHz standard for speech
    channels: int = 1         # Mono
    bit_depth: int = 16       # 16-bit PCM
    encoding: str = "pcm_s16le"
    container: str = "wav"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
            "encoding": self.encoding,
            "container": self.container,
        }


@dataclass
class AudioDevice:
    """Physical or virtual audio input/output device descriptor."""
    id: str
    name: str
    card_index: Optional[int] = None
    device_index: Optional[int] = None
    is_input: bool = True
    is_output: bool = False
    is_default: bool = False
    backend: str = "alsa"  # "alsa", "pulse", "pipewire", "fake"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "card_index": self.card_index,
            "device_index": self.device_index,
            "is_input": self.is_input,
            "is_output": self.is_output,
            "is_default": self.is_default,
            "backend": self.backend,
        }


@dataclass
class AudioChunk:
    """A streaming chunk of raw audio samples with energy telemetry."""
    chunk_id: int
    data: bytes
    is_speech: bool = False
    energy: float = 0.0
    timestamp: float = 0.0

    @property
    def num_samples(self) -> int:
        return len(self.data) // 2

    def calculate_rms(self) -> float:
        """Calculate Root-Mean-Square (RMS) amplitude for 16-bit PCM mono samples."""
        if not self.data:
            return 0.0
        count = len(self.data) // 2
        if count == 0:
            return 0.0
        try:
            samples = struct.unpack(f"<{count}h", self.data[:count * 2])
            sum_squares = sum(s * s for s in samples)
            return math.sqrt(sum_squares / count)
        except Exception:
            return 0.0


@dataclass
class AudioData:
    """Container for recorded or synthesized audio with privacy protections."""
    data: bytes
    format: AudioFormat = field(default_factory=AudioFormat)
    duration_seconds: float = 0.0
    num_samples: int = 0
    rms_energy: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if self.data and not self.num_samples:
            bytes_per_sample = self.format.bit_depth // 8
            if bytes_per_sample > 0 and self.format.channels > 0:
                self.num_samples = len(self.data) // (bytes_per_sample * self.format.channels)
                if self.format.sample_rate > 0:
                    self.duration_seconds = self.num_samples / self.format.sample_rate

        if self.data and self.rms_energy == 0.0:
            count = len(self.data) // 2
            if count > 0:
                try:
                    samples = struct.unpack(f"<{count}h", self.data[:count * 2])
                    sum_squares = sum(s * s for s in samples)
                    self.rms_energy = math.sqrt(sum_squares / count)
                except Exception:
                    self.rms_energy = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Privacy-enforced metadata dictionary omitting raw audio binary bytes."""
        return {
            "bytes_length": len(self.data),
            "format": self.format.to_dict(),
            "duration_seconds": round(self.duration_seconds, 3),
            "num_samples": self.num_samples,
            "rms_energy": round(self.rms_energy, 2),
            "timestamp": self.timestamp,
        }
