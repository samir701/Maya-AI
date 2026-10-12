"""Deterministic Fake Text-to-Speech (TTS) Provider for Testing."""

import io
import math
import struct
import time
import wave
from typing import List, Optional
from core.zetta.voice.models.audio import AudioData, AudioFormat
from core.zetta.voice.models.tts import (
    SynthesisRequest,
    SynthesisResult,
    VoiceProfile,
)
from core.zetta.voice.text_to_speech.base import TTSProvider


def generate_wav_sine_tone(
    duration_seconds: float = 0.5,
    frequency: float = 440.0,
    sample_rate: int = 16000,
    amplitude: float = 8000.0,
) -> bytes:
    """Generate in-memory WAV container bytes with a deterministic sinusoidal tone."""
    total_samples = int(duration_seconds * sample_rate)
    samples = []
    for i in range(total_samples):
        val = int(amplitude * math.sin(2.0 * math.pi * frequency * (i / sample_rate)))
        val = max(-32768, min(32767, val))
        samples.append(val)
    pcm_bytes = struct.pack(f"<{len(samples)}h", *samples)

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)

    return wav_buffer.getvalue()


class FakeTTSProvider(TTSProvider):
    """Deterministic offline TTS provider."""

    def __init__(self) -> None:
        self.synthesis_history: List[SynthesisRequest] = []
        self._voices = [
            VoiceProfile(id="fake_en_default", name="Fake Default Voice", gender="neutral", language="en"),
            VoiceProfile(id="fake_en_female", name="Fake Female Voice", gender="female", language="en"),
        ]

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        start_time = time.time()
        self.synthesis_history.append(request)

        # Scale audio duration deterministically based on character count: ~0.05s per character, min 0.3s, max 3.0s
        char_count = len(request.text)
        duration_sec = max(0.3, min(3.0, char_count * 0.05))

        # Modulate frequency slightly based on pitch
        freq = 440.0 * max(0.5, min(2.0, request.pitch))
        wav_bytes = generate_wav_sine_tone(
            duration_seconds=duration_sec,
            frequency=freq,
            sample_rate=16000,
            amplitude=8000.0 * max(0.2, min(1.0, request.speed)),
        )

        audio = AudioData(data=wav_bytes, format=AudioFormat(sample_rate=16000, channels=1, bit_depth=16, container="wav"))
        elapsed_ms = (time.time() - start_time) * 1000.0

        return SynthesisResult(
            audio=audio,
            duration_ms=elapsed_ms,
            format="wav",
            characters=char_count,
        )

    def list_voices(self) -> List[VoiceProfile]:
        return list(self._voices)

    def is_available(self) -> bool:
        return True
