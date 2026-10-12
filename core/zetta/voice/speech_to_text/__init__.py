"""Speech-to-Text Module."""

from core.zetta.voice.speech_to_text.base import STTProvider
from core.zetta.voice.speech_to_text.fake import FakeSTTProvider
from core.zetta.voice.speech_to_text.groq import GroqWhisperSTTProvider
from core.zetta.voice.speech_to_text.local import LocalSTTProvider

__all__ = [
    "STTProvider",
    "FakeSTTProvider",
    "GroqWhisperSTTProvider",
    "LocalSTTProvider",
]
