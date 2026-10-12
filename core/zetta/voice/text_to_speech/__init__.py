"""Text-to-Speech Module."""

from core.zetta.voice.text_to_speech.base import TTSProvider
from core.zetta.voice.text_to_speech.fake import FakeTTSProvider, generate_wav_sine_tone
from core.zetta.voice.text_to_speech.groq import GroqTTSProvider
from core.zetta.voice.text_to_speech.kokoro import KokoroTTSProvider
from core.zetta.voice.text_to_speech.local import LocalTTSProvider
from core.zetta.voice.text_to_speech.router import TTSRouter

__all__ = [
    "TTSProvider",
    "FakeTTSProvider",
    "GroqTTSProvider",
    "KokoroTTSProvider",
    "LocalTTSProvider",
    "TTSRouter",
    "generate_wav_sine_tone",
]
