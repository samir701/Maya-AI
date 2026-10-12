"""Audio Capture and Playback Provider Abstract Base Classes."""

from abc import ABC, abstractmethod
from typing import List, Optional
from core.zetta.voice.models.audio import (
    AudioChunk,
    AudioData,
    AudioDevice,
    AudioFormat,
)


class AudioCaptureProvider(ABC):
    """Abstract interface for capturing audio from hardware or virtual inputs."""

    @abstractmethod
    def list_devices(self) -> List[AudioDevice]:
        """List all available audio input/capture devices."""
        ...

    @abstractmethod
    def start_capture(
        self,
        device_id: Optional[str] = None,
        audio_format: Optional[AudioFormat] = None,
    ) -> None:
        """Start capturing audio stream."""
        ...

    @abstractmethod
    def read_chunk(self, chunk_size: int = 1024) -> Optional[AudioChunk]:
        """Read the next audio chunk from active stream."""
        ...

    @abstractmethod
    def stop_capture(self) -> AudioData:
        """Stop capturing and return the complete accumulated AudioData."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider backend is operational."""
        ...


class AudioPlaybackProvider(ABC):
    """Abstract interface for audio playback to hardware or virtual outputs."""

    @abstractmethod
    def list_devices(self) -> List[AudioDevice]:
        """List all available audio output/playback devices."""
        ...

    @abstractmethod
    def play(self, audio: AudioData, device_id: Optional[str] = None) -> bool:
        """Play audio data through target output device."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop active audio playback immediately."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if playback provider backend is operational."""
        ...
