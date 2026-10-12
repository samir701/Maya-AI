"""Deterministic Offline Fake Audio Capture & Playback Providers."""

import math
import struct
import time
from typing import List, Optional
from core.zetta.voice.audio.base import AudioCaptureProvider, AudioPlaybackProvider
from core.zetta.voice.models.audio import (
    AudioChunk,
    AudioData,
    AudioDevice,
    AudioFormat,
)


def generate_synthetic_pcm_sine(
    duration_seconds: float = 1.0,
    frequency: float = 440.0,
    sample_rate: int = 16000,
    amplitude: float = 8000.0,
) -> bytes:
    """Generate deterministic 16-bit signed PCM mono audio samples of a sine wave."""
    total_samples = int(duration_seconds * sample_rate)
    samples = []
    for i in range(total_samples):
        val = int(amplitude * math.sin(2.0 * math.pi * frequency * (i / sample_rate)))
        # clamp to 16-bit signed integer range
        val = max(-32768, min(32767, val))
        samples.append(val)
    return struct.pack(f"<{len(samples)}h", *samples)


class FakeAudioCaptureProvider(AudioCaptureProvider):
    """Deterministic, zero-hardware audio capture provider for testing."""

    def __init__(self, synthetic_duration: float = 1.0, simulate_speech: bool = True) -> None:
        self.synthetic_duration = synthetic_duration
        self.simulate_speech = simulate_speech
        self.format = AudioFormat()
        self.is_capturing = False
        self._chunks_read = 0
        self._accumulated_data = bytearray()
        self._total_chunks = 10
        self._mock_devices = [
            AudioDevice(
                id="fake_mic_default",
                name="Fake Microphone (Deterministic)",
                is_input=True,
                is_output=False,
                is_default=True,
                backend="fake",
            )
        ]

    def list_devices(self) -> List[AudioDevice]:
        return list(self._mock_devices)

    def start_capture(
        self,
        device_id: Optional[str] = None,
        audio_format: Optional[AudioFormat] = None,
    ) -> None:
        self.format = audio_format or AudioFormat()
        self.is_capturing = True
        self._chunks_read = 0
        self._accumulated_data = bytearray()

    def read_chunk(self, chunk_size: int = 1024) -> Optional[AudioChunk]:
        if not self.is_capturing:
            return None

        if self._chunks_read >= self._total_chunks:
            return None

        # Generate chunk
        chunk_duration = self.synthetic_duration / self._total_chunks
        amplitude = 8000.0 if self.simulate_speech else 50.0  # speech vs background noise
        chunk_bytes = generate_synthetic_pcm_sine(
            duration_seconds=chunk_duration,
            frequency=440.0,
            sample_rate=self.format.sample_rate,
            amplitude=amplitude,
        )

        chunk = AudioChunk(
            chunk_id=self._chunks_read,
            data=chunk_bytes,
            is_speech=self.simulate_speech,
            timestamp=time.time(),
        )
        chunk.energy = chunk.calculate_rms()

        self._accumulated_data.extend(chunk_bytes)
        self._chunks_read += 1
        return chunk

    def stop_capture(self) -> AudioData:
        self.is_capturing = False
        raw_bytes = bytes(self._accumulated_data)
        return AudioData(data=raw_bytes, format=self.format)

    def is_available(self) -> bool:
        return True


class FakeAudioPlaybackProvider(AudioPlaybackProvider):
    """Deterministic in-memory audio playback provider for testing."""

    def __init__(self) -> None:
        self.playback_history: List[AudioData] = []
        self.last_played_audio: Optional[AudioData] = None
        self.is_playing = False
        self._mock_devices = [
            AudioDevice(
                id="fake_speaker_default",
                name="Fake Speaker (Deterministic)",
                is_input=False,
                is_output=True,
                is_default=True,
                backend="fake",
            )
        ]

    def list_devices(self) -> List[AudioDevice]:
        return list(self._mock_devices)

    def play(self, audio: AudioData, device_id: Optional[str] = None) -> bool:
        self.is_playing = True
        self.last_played_audio = audio
        self.playback_history.append(audio)
        self.is_playing = False
        return True

    def stop(self) -> None:
        self.is_playing = False

    def is_available(self) -> bool:
        return True
