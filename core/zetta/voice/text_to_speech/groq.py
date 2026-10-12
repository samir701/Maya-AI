"""Groq Cloud Text-to-Speech (TTS) Provider."""

import time
from typing import List, Optional
from core.zetta.config import get_settings
from core.zetta.integrations.groq.client import GroqClient
from core.zetta.integrations.groq.errors import GroqAPIKeyMissingError
from core.zetta.utils.logging import get_logger
from core.zetta.voice.models.audio import AudioData, AudioFormat
from core.zetta.voice.models.tts import (
    SynthesisRequest,
    SynthesisResult,
    VoiceProfile,
)
from core.zetta.voice.text_to_speech.base import TTSProvider

logger = get_logger("groq_tts")


class GroqTTSProvider(TTSProvider):
    """Cloud TTS fallback provider powered by Groq Speech (Orpheus)."""

    DEFAULT_VOICES = [
        VoiceProfile(id="autumn", name="Autumn", gender="female", language="en"),
        VoiceProfile(id="diana", name="Diana", gender="female", language="en"),
        VoiceProfile(id="hannah", name="Hannah", gender="female", language="en"),
        VoiceProfile(id="austin", name="Austin", gender="male", language="en"),
        VoiceProfile(id="daniel", name="Daniel", gender="male", language="en"),
        VoiceProfile(id="troy", name="Troy", gender="male", language="en"),
    ]

    def __init__(
        self,
        model: Optional[str] = None,
        voice: Optional[str] = None,
        client: Optional[GroqClient] = None,
    ) -> None:
        settings = get_settings()
        self.model = model or getattr(
            getattr(settings, "voice", None),
            "groq_tts_model",
            "canopylabs/orpheus-v1-english",
        )
        self.default_voice = voice or "autumn"
        self.client = client or GroqClient()

    def __repr__(self) -> str:
        return f"<GroqTTSProvider model='{self.model}' voice='{self.default_voice}'>"

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesize text into speech audio bytes using Groq Speech."""
        text = request.text.strip()
        if not text:
            return SynthesisResult(
                audio=AudioData(data=b""),
                duration_ms=0.0,
                format="wav",
                characters=0,
            )

        start_time = time.time()
        voice = request.voice or self.default_voice

        try:
            audio_bytes = self.client.synthesize_speech(
                text=text,
                model=self.model,
                voice=voice,
                response_format="wav",
            )
            elapsed_ms = (time.time() - start_time) * 1000.0

            audio = AudioData(
                data=audio_bytes,
                format=AudioFormat(
                    sample_rate=24000,
                    channels=1,
                    bit_depth=16,
                    container="wav",
                ),
            )

            logger.info(
                f"Groq TTS synthesized {len(text)} characters ({len(audio_bytes)} bytes) "
                f"in {elapsed_ms:.1f}ms."
            )

            return SynthesisResult(
                audio=audio,
                duration_ms=elapsed_ms,
                format="wav",
                characters=len(text),
            )

        except GroqAPIKeyMissingError as e:
            logger.warning(f"Groq TTS unavailable: {e}")
            raise e
        except Exception as e:
            logger.error(f"Groq TTS synthesis failed: {e}")
            raise e

    def list_voices(self) -> List[VoiceProfile]:
        return list(self.DEFAULT_VOICES)

    def is_available(self) -> bool:
        return self.client.is_configured()
