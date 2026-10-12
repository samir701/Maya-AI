"""Local and Configurable Text-to-Speech (TTS) Provider."""

import io
import os
import shutil
import subprocess
import tempfile
import time
from typing import List, Optional
from core.zetta.utils.logging import get_logger
from core.zetta.voice.models.audio import AudioData, AudioFormat
from core.zetta.voice.models.tts import (
    SynthesisRequest,
    SynthesisResult,
    VoiceProfile,
)
from core.zetta.voice.text_to_speech.base import TTSProvider
from core.zetta.voice.text_to_speech.fake import generate_wav_sine_tone

logger = get_logger("local_tts")


class LocalTTSProvider(TTSProvider):
    """Local TTS provider utilizing standard Linux `espeak-ng`, `espeak`, or `flite`."""

    def __init__(self, voice: str = "en") -> None:
        self.default_voice = voice
        self._espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak") or shutil.which("flite")

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        start_time = time.time()
        text = request.text.strip()
        if not text:
            audio = AudioData(data=b"")
            return SynthesisResult(audio=audio, duration_ms=0.0, format="wav", characters=0)

        # 1. Try local Linux TTS binary if available
        if self._espeak_bin:
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_path = tmp_file.name

                cmd = [self._espeak_bin, "-w", tmp_path]
                if request.voice:
                    cmd.extend(["-v", request.voice])
                elif self.default_voice:
                    cmd.extend(["-v", self.default_voice])

                # Speed control (approx words per minute)
                speed_wpm = int(175 * request.speed)
                cmd.extend(["-s", str(speed_wpm)])
                cmd.append(text)

                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10.0)
                if proc.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    with open(tmp_path, "rb") as f:
                        wav_data = f.read()
                    os.remove(tmp_path)

                    elapsed_ms = (time.time() - start_time) * 1000.0
                    audio = AudioData(
                        data=wav_data,
                        format=AudioFormat(sample_rate=22050, channels=1, bit_depth=16, container="wav"),
                    )
                    return SynthesisResult(
                        audio=audio,
                        duration_ms=elapsed_ms,
                        format="wav",
                        characters=len(text),
                    )
            except Exception as e:
                logger.warning(f"Error invoking local TTS binary: {e}")

        # 2. Fallback: generate notification tone WAV bytes
        duration_sec = max(0.4, min(2.5, len(text) * 0.04))
        wav_bytes = generate_wav_sine_tone(
            duration_seconds=duration_sec,
            frequency=520.0,
            sample_rate=16000,
            amplitude=6000.0,
        )
        elapsed_ms = (time.time() - start_time) * 1000.0
        audio = AudioData(
            data=wav_bytes,
            format=AudioFormat(sample_rate=16000, channels=1, bit_depth=16, container="wav"),
        )
        return SynthesisResult(
            audio=audio,
            duration_ms=elapsed_ms,
            format="wav",
            characters=len(text),
        )

    def list_voices(self) -> List[VoiceProfile]:
        return [
            VoiceProfile(id="default", name="Default System Voice", gender="neutral", language="en"),
        ]

    def is_available(self) -> bool:
        return self._espeak_bin is not None
