"""Unit tests for KokoroTTSProvider."""

import time
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from core.zetta.voice.models.tts import SynthesisRequest
from core.zetta.voice.text_to_speech.errors import (
    KokoroTimeoutError,
    KokoroUnavailableError,
)
from core.zetta.voice.text_to_speech.kokoro import KokoroTTSProvider


class TestKokoroTTS:
    """Test suite for Kokoro TTS resource safety, lazy loading, and concurrency."""

    def test_lazy_loading_not_loaded_at_startup(self):
        provider = KokoroTTSProvider(lazy_load=True)
        assert not provider.is_loaded
        assert provider._kokoro is None
        status = provider.status()
        assert status["loaded"] == "No"
        assert status["device"] == "CPU"
        assert status["voice"] == "af_heart"

    def test_missing_model_files_raises_unavailable(self):
        provider = KokoroTTSProvider(
            model_path="/tmp/non_existent_kokoro.onnx",
            voices_path="/tmp/non_existent_voices.json",
            lazy_load=True,
        )
        assert not provider.is_available()

        with pytest.raises(KokoroUnavailableError):
            provider.synthesize(SynthesisRequest(text="Hello world"))

    def test_first_request_loads_model_and_subsequent_reuses(self):
        provider = KokoroTTSProvider(lazy_load=True)

        mock_kokoro = MagicMock()
        fake_samples = np.zeros(24000, dtype=np.float32)
        mock_kokoro.create.return_value = (fake_samples, 24000)

        with patch.object(provider, "_ensure_model_loaded") as mock_ensure:
            def side_effect():
                provider._kokoro = mock_kokoro
                provider._is_loaded = True
            mock_ensure.side_effect = side_effect

            # First synthesis
            res1 = provider.synthesize(SynthesisRequest(text="First turn"))
            assert res1.audio.data.startswith(b"RIFF")
            assert mock_ensure.call_count == 1
            assert provider.is_loaded

            # Second synthesis should reuse loaded instance
            res2 = provider.synthesize(SynthesisRequest(text="Second turn"))
            assert res2.audio.data.startswith(b"RIFF")
            assert mock_ensure.call_count == 2  # _ensure_model_loaded called, but returns immediately when _is_loaded=True
            assert mock_kokoro.create.call_count == 2

    def test_text_chunking_under_max_limit(self):
        provider = KokoroTTSProvider(max_text_chars=50, lazy_load=True)

        long_text = "This is a sentence. This is another sentence that is quite long and needs chunking."
        chunks = provider._chunk_text(long_text)
        assert len(chunks) >= 2
        for c in chunks:
            assert len(c) <= 50

    def test_timeout_protection_raises_kokoro_timeout(self):
        provider = KokoroTTSProvider(timeout_seconds=0.1, lazy_load=True)

        def slow_chunk(*args, **kwargs):
            time.sleep(0.3)
            return (b"\x00" * 4800, 24000)

        with patch.object(provider, "_generate_chunk_audio", side_effect=slow_chunk):
            with patch.object(provider, "_ensure_model_loaded"):
                with pytest.raises(KokoroTimeoutError):
                    provider.synthesize(SynthesisRequest(text="Quick test that will time out"))

    def test_single_concurrency_lock(self):
        provider = KokoroTTSProvider(lazy_load=True)
        assert not provider._lock.locked()
        with provider._lock:
            assert provider._lock.locked()

    def test_status_reporting(self):
        provider = KokoroTTSProvider(voice="af_bella", device="cpu", lazy_load=True)
        status = provider.status()
        assert status["provider"] == "Kokoro"
        assert status["voice"] == "af_bella"
        assert status["device"] == "CPU"
        assert status["loaded"] == "No"

    def test_explicit_cpu_only_execution_provider(self):
        """Verify KOKORO_DEVICE=cpu explicitly configures CPUExecutionProvider with zero GPU requests."""
        provider = KokoroTTSProvider(device="cpu", lazy_load=True)
        assert provider.active_device == "CPU"
        assert provider.status()["device"] == "CPU"

        mock_kokoro = MagicMock()
        mock_mod = MagicMock()
        mock_mod.Kokoro.return_value = mock_kokoro
        with patch.dict("sys.modules", {"kokoro_onnx": mock_mod}):
            with patch("os.path.exists", return_value=True):
                provider._ensure_model_loaded()
                import os
                assert os.environ.get("ONNX_PROVIDER") == "CPUExecutionProvider"
                assert provider.active_device == "CPU"
                assert provider.is_loaded
