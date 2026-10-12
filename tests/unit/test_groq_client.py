"""Unit tests for reusable GroqClient layer."""

import json
import urllib.error
from unittest.mock import MagicMock, patch
import pytest
from core.zetta.integrations.groq.client import GroqClient
from core.zetta.integrations.groq.errors import (
    GroqAPIKeyMissingError,
    GroqAuthError,
    GroqNetworkError,
    GroqRateLimitError,
    GroqTimeoutError,
)


class TestGroqClient:
    """Test suite for GroqClient error handling, retries, and API calls."""

    def test_missing_api_key_raises(self):
        client = GroqClient(api_key="")
        assert not client.is_configured()
        assert client.masked_api_key == "(not set)"

        with pytest.raises(GroqAPIKeyMissingError):
            client.chat_completion(messages=[{"role": "user", "content": "hi"}])

        with pytest.raises(GroqAPIKeyMissingError):
            client.transcribe_audio(audio_bytes=b"dummy")

        with pytest.raises(GroqAPIKeyMissingError):
            client.synthesize_speech(text="hello")

    def test_api_key_never_exposed_in_repr_or_str(self):
        secret_key = "gsk_supersecretkey1234567890abcdef"
        client = GroqClient(api_key=secret_key)
        assert secret_key not in repr(client)
        assert secret_key not in client.masked_api_key
        assert client.masked_api_key.startswith("gsk_")
        assert client.masked_api_key.endswith("cdef")
        assert client.is_configured()

    @patch("urllib.request.urlopen")
    def test_successful_chat_completion(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "id": "chatcmpl_123",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello world"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = GroqClient(api_key="gsk_test")
        res = client.chat_completion(messages=[{"role": "user", "content": "hello"}])
        assert res["id"] == "chatcmpl_123"
        assert res["choices"][0]["message"]["content"] == "Hello world"

    @patch("urllib.request.urlopen")
    def test_auth_failure_raises_immediately(self, mock_urlopen):
        mock_error = urllib.error.HTTPError(
            url="https://api.groq.com",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=None,
        )
        mock_urlopen.side_effect = mock_error

        client = GroqClient(api_key="gsk_invalid", max_retries=2)
        with pytest.raises(GroqAuthError):
            client.chat_completion(messages=[{"role": "user", "content": "hi"}])
        # Should not retry 401
        assert mock_urlopen.call_count == 1

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_rate_limit_retries_and_raises(self, mock_urlopen, mock_sleep):
        mock_error = urllib.error.HTTPError(
            url="https://api.groq.com",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=None,
        )
        mock_urlopen.side_effect = mock_error

        client = GroqClient(api_key="gsk_test", max_retries=1)
        with pytest.raises(GroqRateLimitError):
            client.chat_completion(messages=[{"role": "user", "content": "hi"}])
        assert mock_urlopen.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("time.sleep")
    @patch("urllib.request.urlopen")
    def test_timeout_retries_and_raises(self, mock_urlopen, mock_sleep):
        mock_urlopen.side_effect = urllib.error.URLError("timed out")

        client = GroqClient(api_key="gsk_test", timeout=5.0, max_retries=1)
        with pytest.raises(GroqTimeoutError):
            client.chat_completion(messages=[{"role": "user", "content": "hi"}])
        assert mock_urlopen.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("urllib.request.urlopen")
    def test_network_error_raises(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        client = GroqClient(api_key="gsk_test", max_retries=0)
        with pytest.raises(GroqNetworkError):
            client.chat_completion(messages=[{"role": "user", "content": "hi"}])

    @patch("urllib.request.urlopen")
    def test_successful_audio_transcription(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "text": "Testing transcription",
            "language": "en",
            "segments": [{"text": "Testing transcription", "start": 0.0, "end": 1.5, "confidence": 0.98}],
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = GroqClient(api_key="gsk_test")
        res = client.transcribe_audio(audio_bytes=b"RIFF\x24\x00\x00\x00WAVEfmt ")
        assert res["text"] == "Testing transcription"
        assert len(res["segments"]) == 1

    @patch("urllib.request.urlopen")
    def test_successful_speech_synthesis(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"RIFFfake_wav_audio_payload"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = GroqClient(api_key="gsk_test")
        audio_bytes = client.synthesize_speech(text="Hello world")
        assert audio_bytes.startswith(b"RIFF")
