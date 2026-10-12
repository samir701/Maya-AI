"""Live external integration tests for Groq and Kokoro Real Voice Stack.

Only executed when RUN_EXTERNAL_TESTS=true and GROQ_API_KEY is provided.
Normal automated CI/tests skip these completely.
"""

import os
import pytest
from core.zetta.ai.providers.groq_provider import GroqAIProvider
from core.zetta.integrations.groq.client import GroqClient
from core.zetta.voice.models.audio import AudioData, AudioFormat
from core.zetta.voice.models.tts import SynthesisRequest
from core.zetta.voice.speech_to_text.groq import GroqWhisperSTTProvider
from core.zetta.voice.text_to_speech.groq import GroqTTSProvider
from core.zetta.voice.text_to_speech.kokoro import KokoroTTSProvider
from shared.types import AIMessage, AIRequest, AIRole

RUN_EXTERNAL = os.getenv("RUN_EXTERNAL_TESTS", "false").lower() == "true"
HAS_GROQ_KEY = bool(os.getenv("GROQ_API_KEY"))


@pytest.mark.skipif(not (RUN_EXTERNAL and HAS_GROQ_KEY), reason="External real provider tests require RUN_EXTERNAL_TESTS=true and GROQ_API_KEY")
class TestRealVoiceStackLive:
    """Live external test suite against real Groq Cloud APIs and local Kokoro engine."""

    def test_live_groq_llm_generation(self):
        provider = GroqAIProvider()
        req = AIRequest(messages=[AIMessage(role=AIRole.USER, content="Reply with one word: 'READY'")])
        resp = provider.generate(req)
        assert len(resp.text) > 0

    def test_live_groq_whisper_stt(self):
        provider = GroqWhisperSTTProvider()
        # 16kHz mono silence
        silence_pcm = b"\x00\x00" * 8000  # 0.5s
        audio = AudioData(data=silence_pcm, format=AudioFormat(sample_rate=16000, channels=1, bit_depth=16))
        res = provider.transcribe(audio)
        assert res is not None

    def test_live_groq_tts_synthesis(self):
        provider = GroqTTSProvider()
        try:
            res = provider.synthesize(SynthesisRequest(text="Live test of Groq Orpheus speech synthesis."))
            assert res.audio.data.startswith(b"RIFF")
        except Exception as e:
            if "model_terms_required" in str(e):
                pytest.skip("Groq Orpheus TTS model terms need to be accepted on console.groq.com")
            raise

    def test_live_kokoro_local_synthesis_if_models_present(self):
        provider = KokoroTTSProvider(lazy_load=True)
        if not provider.is_available():
            pytest.skip("Kokoro model weights not downloaded locally in data/models/kokoro/")

        res = provider.synthesize(SynthesisRequest(text="Hello from local Kokoro neural text to speech."))
        assert res.audio.data.startswith(b"RIFF")
