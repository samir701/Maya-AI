"""Groq Whisper Cloud Speech-to-Text (STT) Provider."""

import io
import time
import wave
from typing import Iterator, List, Optional
from core.zetta.config import get_settings
from core.zetta.integrations.groq.client import GroqClient
from core.zetta.integrations.groq.errors import GroqAPIKeyMissingError
from core.zetta.utils.logging import get_logger
from core.zetta.voice.models.audio import AudioChunk, AudioData
from core.zetta.voice.models.stt import (
    TranscriptionResult,
    TranscriptionSegment,
)
from core.zetta.voice.speech_to_text.base import STTProvider

logger = get_logger("groq_stt")


class GroqWhisperSTTProvider(STTProvider):
    """Cloud STT Provider powered by Groq Whisper Large V3 Turbo."""

    def __init__(
        self,
        model: Optional[str] = None,
        client: Optional[GroqClient] = None,
    ) -> None:
        settings = get_settings()
        self.model = model or getattr(settings.voice, "groq_stt_model", "whisper-large-v3-turbo")
        self.client = client or GroqClient()

    def _prepare_wav_bytes(self, audio: AudioData) -> bytes:
        """Ensure audio data has a valid WAV container header."""
        if audio.data.startswith(b"RIFF"):
            return audio.data

        # Wrap raw PCM into standard WAV container
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(audio.format.channels)
            wf.setsampwidth(audio.format.bit_depth // 8)
            wf.setframerate(audio.format.sample_rate)
            wf.writeframes(audio.data)
        return wav_buf.getvalue()

    def transcribe(self, audio: AudioData) -> TranscriptionResult:
        """Transcribe an AudioData container into text using Groq Whisper."""
        if not audio or not audio.data:
            return TranscriptionResult(
                text="",
                confidence=0.0,
                duration_ms=0.0,
                segments=[],
            )

        start_time = time.time()
        try:
            wav_bytes = self._prepare_wav_bytes(audio)
            response = self.client.transcribe_audio(
                audio_bytes=wav_bytes,
                filename="speech.wav",
                model=self.model,
                response_format="verbose_json",
            )

            full_text = response.get("text", "").strip()
            language = response.get("language", "en")
            raw_segments = response.get("segments", [])

            segments: List[TranscriptionSegment] = []
            if raw_segments:
                for seg in raw_segments:
                    segments.append(
                        TranscriptionSegment(
                            text=seg.get("text", "").strip(),
                            start_time=float(seg.get("start", 0.0)),
                            end_time=float(seg.get("end", audio.duration_seconds)),
                            confidence=float(seg.get("confidence", 0.95))
                            if "confidence" in seg
                            else 0.95,
                        )
                    )
            elif full_text:
                segments.append(
                    TranscriptionSegment(
                        text=full_text,
                        start_time=0.0,
                        end_time=audio.duration_seconds,
                        confidence=0.95,
                    )
                )

            elapsed_ms = (time.time() - start_time) * 1000.0
            logger.info(
                f"Groq Whisper transcribed audio ({len(audio.data)} bytes, "
                f"{elapsed_ms:.1f}ms): '{full_text[:40]}...'"
            )

            return TranscriptionResult(
                text=full_text,
                confidence=0.95 if full_text else 0.0,
                duration_ms=elapsed_ms,
                language=language,
                segments=segments,
                is_final=True,
            )

        except GroqAPIKeyMissingError as e:
            logger.warning(f"Groq STT unavailable: {e}")
            elapsed_ms = (time.time() - start_time) * 1000.0
            return TranscriptionResult(
                text="[Groq STT Error: GROQ_API_KEY is not configured]",
                confidence=0.0,
                duration_ms=elapsed_ms,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"Groq STT transcription failed: {e}")
            elapsed_ms = (time.time() - start_time) * 1000.0
            return TranscriptionResult(
                text="",
                confidence=0.0,
                duration_ms=elapsed_ms,
                error=str(e),
            )

    def transcribe_stream(
        self,
        chunk_stream: Iterator[AudioChunk],
    ) -> Iterator[TranscriptionResult]:
        """Transcribe an audio chunk stream by buffering chunks and transcribing."""
        accumulated = bytearray()
        for chunk in chunk_stream:
            accumulated.extend(chunk.data)

        audio = AudioData(data=bytes(accumulated))
        yield self.transcribe(audio)

    def is_available(self) -> bool:
        """Check if Groq STT provider is configured."""
        return self.client.is_configured()
