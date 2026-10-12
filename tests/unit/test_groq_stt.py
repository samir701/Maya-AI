"""Unit tests for GroqWhisperSTTProvider."""

from unittest.mock import MagicMock
import pytest
from core.zetta.integrations.groq.errors import GroqAPIKeyMissingError
from core.zetta.voice.models.audio import AudioData, AudioFormat
from core.zetta.voice.speech_to_text.groq import GroqWhisperSTTProvider


class TestGroqSTT:
    """Test suite for Groq Whisper STT Provider."""

    def test_empty_audio_returns_empty_result(self):
        mock_client = MagicMock()
        provider = GroqWhisperSTTProvider(client=mock_client)

        empty_audio = AudioData(data=b"")
        result = provider.transcribe(empty_audio)
        assert result.text == ""
        assert result.confidence == 0.0
        assert not mock_client.transcribe_audio.called

    def test_successful_transcription_parsing(self):
        mock_client = MagicMock()
        mock_client.is_configured.return_value = True
        mock_client.transcribe_audio.return_value = {
            "text": "Hello ZETTA real transcription",
            "language": "en",
            "segments": [
                {"text": "Hello ZETTA", "start": 0.0, "end": 1.2, "confidence": 0.96},
                {"text": "real transcription", "start": 1.2, "end": 2.4, "confidence": 0.94},
            ],
        }

        provider = GroqWhisperSTTProvider(client=mock_client)
        assert provider.is_available()

        audio = AudioData(
            data=b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00",
            format=AudioFormat(sample_rate=16000, channels=1, bit_depth=16, container="wav"),
        )
        result = provider.transcribe(audio)

        assert result.text == "Hello ZETTA real transcription"
        assert len(result.segments) == 2
        assert result.segments[0].start_time == 0.0
        assert result.segments[1].end_time == 2.4
        assert result.language == "en"

    def test_missing_api_key_handles_gracefully(self):
        mock_client = MagicMock()
        mock_client.is_configured.return_value = False
        mock_client.transcribe_audio.side_effect = GroqAPIKeyMissingError()

        provider = GroqWhisperSTTProvider(client=mock_client)
        assert not provider.is_available()

        audio = AudioData(data=b"dummy_raw_pcm_bytes", format=AudioFormat(sample_rate=16000))
        result = provider.transcribe(audio)
        assert "GROQ_API_KEY is not set" in result.error or "Error" in result.text
        assert result.confidence == 0.0

    def test_raw_pcm_is_wrapped_in_wav_container(self):
        mock_client = MagicMock()
        mock_client.transcribe_audio.return_value = {"text": "Transcribed", "segments": []}

        provider = GroqWhisperSTTProvider(client=mock_client)
        pcm_data = b"\x00\x00" * 1600  # 0.1s of 16kHz mono audio
        audio = AudioData(data=pcm_data, format=AudioFormat(sample_rate=16000, channels=1, bit_depth=16))

        result = provider.transcribe(audio)
        assert result.text == "Transcribed"

        # Check call args to ensure WAV header was prepended
        called_args, called_kwargs = mock_client.transcribe_audio.call_args
        submitted_bytes = called_kwargs["audio_bytes"]
        assert submitted_bytes.startswith(b"RIFF")
