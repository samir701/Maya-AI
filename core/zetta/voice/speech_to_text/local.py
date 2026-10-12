"""Local and Configurable Speech-to-Text (STT) Provider."""

import json
import os
import shutil
import subprocess
import tempfile
import time
from typing import Iterator, Optional
from core.zetta.utils.logging import get_logger
from core.zetta.voice.models.audio import AudioChunk, AudioData
from core.zetta.voice.models.stt import (
    TranscriptionResult,
    TranscriptionSegment,
)
from core.zetta.voice.speech_to_text.base import STTProvider

logger = get_logger("local_stt")


class LocalSTTProvider(STTProvider):
    """Local STT provider utilizing local whisper CLI or standard external whisper binaries."""

    def __init__(self, model_name: str = "base", endpoint_url: Optional[str] = None) -> None:
        self.model_name = model_name
        self.endpoint_url = endpoint_url
        self._whisper_bin = shutil.which("whisper") or shutil.which("whisper-cli")

    def transcribe(self, audio: AudioData) -> TranscriptionResult:
        if not audio.data:
            return TranscriptionResult(text="", confidence=0.0, duration_ms=0.0, segments=[])

        start_time = time.time()

        # If whisper CLI is available
        if self._whisper_bin:
            try:
                # Write audio data to temporary WAV file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    # Prepend WAV header if raw PCM
                    if not audio.data.startswith(b"RIFF"):
                        import wave
                        with wave.open(tmp_path, "wb") as wf:
                            wf.setnchannels(audio.format.channels)
                            wf.setsampwidth(audio.format.bit_depth // 8)
                            wf.setframerate(audio.format.sample_rate)
                            wf.writeframes(audio.data)
                    else:
                        tmp_file.write(audio.data)

                cmd = [
                    self._whisper_bin,
                    tmp_path,
                    "--model", self.model_name,
                    "--output_format", "json",
                    "--output_dir", tempfile.gettempdir(),
                ]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30.0)

                json_output_path = tmp_path.replace(".wav", ".json")
                text = ""
                if os.path.exists(json_output_path):
                    with open(json_output_path, "r") as f:
                        data = json.load(f)
                        text = data.get("text", "").strip()
                    os.remove(json_output_path)

                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

                elapsed_ms = (time.time() - start_time) * 1000.0
                return TranscriptionResult(
                    text=text,
                    confidence=0.9,
                    duration_ms=elapsed_ms,
                    language="en",
                    segments=[TranscriptionSegment(text=text, start_time=0.0, end_time=audio.duration_seconds)],
                )
            except Exception as e:
                logger.warning(f"Error executing whisper STT: {e}")

        # Fallback when whisper CLI is not installed
        elapsed_ms = (time.time() - start_time) * 1000.0
        return TranscriptionResult(
            text="[Local STT unavailable: whisper binary not found]",
            confidence=0.0,
            duration_ms=elapsed_ms,
            error="Local STT provider requires 'whisper' CLI or configured endpoint.",
        )

    def transcribe_stream(
        self,
        chunk_stream: Iterator[AudioChunk],
    ) -> Iterator[TranscriptionResult]:
        accumulated = bytearray()
        for chunk in chunk_stream:
            accumulated.extend(chunk.data)

        audio = AudioData(data=bytes(accumulated))
        yield self.transcribe(audio)

    def is_available(self) -> bool:
        return self._whisper_bin is not None or self.endpoint_url is not None
