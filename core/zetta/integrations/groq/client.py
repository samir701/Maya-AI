"""ZETTA Groq Unified Client Layer."""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple
from core.zetta.config import get_settings
from core.zetta.integrations.groq.errors import (
    GroqAPIKeyMissingError,
    GroqAuthError,
    GroqNetworkError,
    GroqRateLimitError,
    GroqTimeoutError,
)
from core.zetta.utils.errors import IntegrationError
from core.zetta.utils.logging import get_logger

logger = get_logger("groq_client")


class GroqClient:
    """Production-grade reusable HTTP client for Groq Cloud APIs.

    Provides bounded retries, rate-limit handling, credential masking,
    and unified access to Chat, Whisper STT, and Speech TTS endpoints.
    """

    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        settings = get_settings()
        env_key = (
            os.getenv("GROQ_API_KEY")
            or getattr(settings.ai, "groq_api_key", None)
            or getattr(settings.voice, "groq_api_key", None)
            or ""
        )
        self.api_key = (api_key if api_key is not None else env_key).strip()
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = float(timeout)
        self.max_retries = max(0, int(max_retries))

    def __repr__(self) -> str:
        masked = self.masked_api_key
        return f"<GroqClient base_url='{self.base_url}' api_key='{masked}' timeout={self.timeout}s>"

    @property
    def masked_api_key(self) -> str:
        """Return safely masked API key for logging or status reports."""
        if not self.api_key:
            return "(not set)"
        if len(self.api_key) <= 8:
            return "****"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

    def is_configured(self) -> bool:
        """Return True if an API key is present."""
        return bool(self.api_key)

    def _ensure_api_key(self) -> None:
        if not self.api_key:
            raise GroqAPIKeyMissingError()

    def _prepare_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        self._ensure_api_key()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "ZETTA-AI-Employee/0.1.0",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _execute_http_request(
        self,
        req: urllib.request.Request,
        retryable_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504),
    ) -> Tuple[int, bytes]:
        """Execute HTTP request with bounded exponential backoff retries."""
        attempts = 0
        backoff_sec = 0.5

        while True:
            attempts += 1
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.status, resp.read()
            except urllib.error.HTTPError as e:
                status = e.code
                error_body = e.read().decode("utf-8", errors="replace") if e.fp else str(e)

                # Auth errors: do not retry
                if status in (401, 403):
                    raise GroqAuthError(f"Groq authentication failed (HTTP {status}): {e.reason}")

                # Rate limit (429) or transient server errors (5xx): retry if attempts remain
                if status in retryable_status_codes and attempts <= self.max_retries:
                    logger.warning(
                        f"Groq API returned HTTP {status} (attempt {attempts}/{self.max_retries + 1}). "
                        f"Retrying in {backoff_sec:.1f}s..."
                    )
                    time.sleep(backoff_sec)
                    backoff_sec *= 2.0
                    continue

                if status == 429:
                    raise GroqRateLimitError(f"Groq rate limit exceeded (HTTP 429): {error_body}")

                raise IntegrationError(f"Groq API HTTP Error {status}: {e.reason}. Details: {error_body}")

            except urllib.error.URLError as e:
                # Socket timeout vs network resolution error
                if isinstance(e.reason, (TimeoutError, TimeoutError)) or "timed out" in str(e).lower():
                    if attempts <= self.max_retries:
                        logger.warning(f"Groq request timed out. Retrying in {backoff_sec:.1f}s...")
                        time.sleep(backoff_sec)
                        backoff_sec *= 2.0
                        continue
                    raise GroqTimeoutError(f"Groq request timed out after {self.timeout}s: {e}")

                if attempts <= self.max_retries:
                    logger.warning(f"Groq network error: {e}. Retrying in {backoff_sec:.1f}s...")
                    time.sleep(backoff_sec)
                    backoff_sec *= 2.0
                    continue

                raise GroqNetworkError(f"Groq network connection failed: {e}")

            except Exception as e:
                if "timeout" in str(e).lower():
                    raise GroqTimeoutError(f"Groq request timed out: {e}")
                raise IntegrationError(f"Groq request unexpected failure: {e}")

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = "openai/gpt-oss-20b",
        temperature: float = 0.7,
        max_tokens: Optional[int] = 2048,
        stop: Optional[List[str]] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Send chat completion request to Groq LLM endpoint."""
        self._ensure_api_key()
        endpoint = f"{self.base_url}/chat/completions"

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if stop:
            payload["stop"] = stop
        if response_format:
            payload["response_format"] = response_format

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers=self._prepare_headers("application/json"),
            method="POST",
        )

        _, response_bytes = self._execute_http_request(req)
        try:
            return json.loads(response_bytes.decode("utf-8"))
        except Exception as e:
            raise IntegrationError(f"Failed to parse Groq chat completion JSON response: {e}")

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        model: str = "whisper-large-v3-turbo",
        response_format: str = "verbose_json",
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transcribe audio bytes using Groq Whisper endpoint via multipart/form-data."""
        self._ensure_api_key()
        endpoint = f"{self.base_url}/audio/transcriptions"

        fields: Dict[str, str] = {
            "model": model,
            "response_format": response_format,
        }
        if language:
            fields["language"] = language
        if prompt:
            fields["prompt"] = prompt

        boundary = f"----ZettaGroqBoundary{int(time.time() * 1000)}"
        body = bytearray()

        for field_name, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'.encode("utf-8"))
            body.extend(f"{value}\r\n".encode("utf-8"))

        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f'Content-Type: audio/wav\r\n\r\n'.encode("utf-8")
        )
        body.extend(audio_bytes)
        body.extend(b"\r\n")

        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        headers = self._prepare_headers(f"multipart/form-data; boundary={boundary}")
        req = urllib.request.Request(endpoint, data=bytes(body), headers=headers, method="POST")

        _, response_bytes = self._execute_http_request(req)
        try:
            return json.loads(response_bytes.decode("utf-8"))
        except Exception as e:
            raise IntegrationError(f"Failed to parse Groq Whisper transcription JSON response: {e}")

    def synthesize_speech(
        self,
        text: str,
        model: str = "canopylabs/orpheus-v1-english",
        voice: Optional[str] = None,
        response_format: str = "wav",
    ) -> bytes:
        """Synthesize speech audio from text using Groq TTS endpoint."""
        self._ensure_api_key()
        endpoint = f"{self.base_url}/audio/speech"

        payload: Dict[str, Any] = {
            "model": model,
            "input": text,
            "response_format": response_format,
        }
        if voice:
            payload["voice"] = voice

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers=self._prepare_headers("application/json"),
            method="POST",
        )

        _, response_bytes = self._execute_http_request(req)
        return response_bytes
