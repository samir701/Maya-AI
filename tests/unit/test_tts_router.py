"""Unit tests for TTSRouter and fallback orchestration."""

from unittest.mock import MagicMock
import pytest
from core.zetta.voice.models.audio import AudioData
from core.zetta.voice.models.tts import SynthesisRequest, SynthesisResult
from core.zetta.voice.text_to_speech.errors import (
    KokoroUnavailableError,
    TTSFallbackFailedError,
)
from core.zetta.voice.text_to_speech.fake import FakeTTSProvider
from core.zetta.voice.text_to_speech.router import TTSRouter


class TestTTSRouter:
    """Test suite for TTSRouter primary and fallback execution."""

    def test_primary_success_does_not_call_fallback(self):
        mock_primary = MagicMock()
        mock_fallback = MagicMock()

        expected_result = SynthesisResult(
            audio=AudioData(data=b"primary_audio"),
            duration_ms=100.0,
            format="wav",
            characters=10,
        )
        mock_primary.synthesize.return_value = expected_result

        router = TTSRouter(
            primary_provider=mock_primary,
            fallback_provider=mock_fallback,
            fallback_enabled=True,
        )

        req = SynthesisRequest(text="Hello primary")
        res = router.synthesize(req)

        assert res.audio.data == b"primary_audio"
        assert mock_primary.synthesize.called
        assert not mock_fallback.synthesize.called
        assert router.last_used_provider == mock_primary.__class__.__name__

    def test_primary_failure_triggers_fallback(self):
        mock_primary = MagicMock()
        mock_fallback = MagicMock()

        mock_primary.synthesize.side_effect = KokoroUnavailableError("Model missing")

        fallback_result = SynthesisResult(
            audio=AudioData(data=b"fallback_audio"),
            duration_ms=200.0,
            format="wav",
            characters=10,
        )
        mock_fallback.synthesize.return_value = fallback_result

        router = TTSRouter(
            primary_provider=mock_primary,
            fallback_provider=mock_fallback,
            fallback_enabled=True,
        )

        req = SynthesisRequest(text="Hello fallback")
        res = router.synthesize(req)

        assert res.audio.data == b"fallback_audio"
        assert mock_primary.synthesize.called
        assert mock_fallback.synthesize.called
        assert router.last_used_provider == mock_fallback.__class__.__name__
        status = router.status()
        assert status["fallback_count"] == 1

    def test_both_fail_raises_fallback_failed_error(self):
        mock_primary = MagicMock()
        mock_fallback = MagicMock()

        mock_primary.synthesize.side_effect = KokoroUnavailableError("Model missing")
        mock_fallback.synthesize.side_effect = RuntimeError("Groq quota exceeded")

        router = TTSRouter(
            primary_provider=mock_primary,
            fallback_provider=mock_fallback,
            fallback_enabled=True,
        )

        req = SynthesisRequest(text="Hello doomed")
        with pytest.raises(TTSFallbackFailedError):
            router.synthesize(req)

    def test_fallback_disabled_raises_primary_error(self):
        mock_primary = MagicMock()
        mock_fallback = MagicMock()

        mock_primary.synthesize.side_effect = KokoroUnavailableError("Primary broke")

        router = TTSRouter(
            primary_provider=mock_primary,
            fallback_provider=mock_fallback,
            fallback_enabled=False,
        )

        req = SynthesisRequest(text="No fallback")
        with pytest.raises(KokoroUnavailableError):
            router.synthesize(req)
        assert not mock_fallback.synthesize.called

    def test_fake_mode_routing(self):
        router = TTSRouter(configured_mode="fake")
        assert isinstance(router.primary, FakeTTSProvider)
        assert router.fallback is None

        req = SynthesisRequest(text="Offline voice turn")
        res = router.synthesize(req)
        assert res.audio.data.startswith(b"RIFF")
