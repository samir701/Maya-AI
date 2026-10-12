"""Kokoro ONNX Local Text-to-Speech (TTS) Provider."""

import concurrent.futures
import io
import os
import re
import threading
import time
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from core.zetta.config import get_settings
from core.zetta.utils.logging import get_logger
from core.zetta.voice.models.audio import AudioData, AudioFormat
from core.zetta.voice.models.tts import (
    SynthesisRequest,
    SynthesisResult,
    VoiceProfile,
)
from core.zetta.voice.text_to_speech.base import TTSProvider
from core.zetta.voice.text_to_speech.errors import (
    KokoroInferenceError,
    KokoroLoadFailedError,
    KokoroTimeoutError,
    KokoroUnavailableError,
)

logger = get_logger("kokoro_tts")


class KokoroTTSProvider(TTSProvider):
    """Primary local neural TTS engine running Kokoro ONNX with CPU baseline
    and resource-safe single concurrency, lazy loading, and timeout guards.
    """

    DEFAULT_VOICES = [
        VoiceProfile(id="af_heart", name="American Female - Heart", gender="female", language="en-us"),
        VoiceProfile(id="af_bella", name="American Female - Bella", gender="female", language="en-us"),
        VoiceProfile(id="am_adam", name="American Male - Adam", gender="male", language="en-us"),
        VoiceProfile(id="am_michael", name="American Male - Michael", gender="male", language="en-us"),
        VoiceProfile(id="bf_emma", name="British Female - Emma", gender="female", language="en-gb"),
        VoiceProfile(id="bm_george", name="British Male - George", gender="male", language="en-gb"),
    ]

    def __init__(
        self,
        voice: Optional[str] = None,
        device: Optional[str] = None,
        max_text_chars: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        model_path: Optional[str] = None,
        voices_path: Optional[str] = None,
        lazy_load: bool = True,
    ) -> None:
        settings = get_settings()
        v_cfg = getattr(settings, "voice", None)

        self.default_voice = voice or getattr(v_cfg, "kokoro_voice", "af_heart")
        self.device_config = (device or getattr(v_cfg, "kokoro_device", "cpu")).lower()
        self.max_text_chars = max_text_chars or getattr(v_cfg, "kokoro_max_text_chars", 200)
        self.timeout_seconds = float(timeout_seconds or getattr(v_cfg, "kokoro_timeout_seconds", 30.0))

        # Model file paths
        root_path = getattr(settings, "root_path", Path("."))
        default_model_dir = root_path / "data" / "models" / "kokoro"
        self.model_path = model_path or os.getenv(
            "KOKORO_MODEL_PATH",
            str(default_model_dir / "kokoro-v0_19.onnx"),
        )
        self.voices_path = voices_path or os.getenv(
            "KOKORO_VOICES_PATH",
            str(default_model_dir / "voices.json"),
        )

        self._kokoro = None
        self._is_loaded = False
        self._active_device = "CPU"
        self._lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="KokoroTTSWorker",
        )

        if not lazy_load:
            self._ensure_model_loaded()

    def __repr__(self) -> str:
        loaded_str = "Yes" if self._is_loaded else "No"
        return f"<KokoroTTSProvider voice='{self.default_voice}' device='CPU' loaded={loaded_str}>"

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @property
    def active_device(self) -> str:
        return "CPU"

    def is_available(self) -> bool:
        """Check if Kokoro backend libraries and model weights are installed/present."""
        try:
            import kokoro_onnx  # noqa: F401
            return os.path.exists(self.model_path) and os.path.exists(self.voices_path)
        except ImportError:
            return False

    def status(self) -> Dict[str, Any]:
        """Return provider health and runtime telemetry."""
        return {
            "provider": "Kokoro",
            "voice": self.default_voice,
            "device": "CPU",
            "loaded": "Yes" if self._is_loaded else "No",
            "max_text_chars": self.max_text_chars,
            "timeout_seconds": self.timeout_seconds,
            "is_available": self.is_available(),
        }

    def _resolve_device(self) -> str:
        """Explicitly return CPU execution device."""
        return "CPU"

    def _ensure_model_loaded(self) -> None:
        """Lazy model loader. Must be called under lock or prior to generation."""
        if self._is_loaded and self._kokoro is not None:
            return

        start_time = time.time()
        try:
            from kokoro_onnx import Kokoro
        except ImportError as e:
            raise KokoroUnavailableError(f"'kokoro_onnx' library is not installed: {e}")

        if not os.path.exists(self.model_path) or not os.path.exists(self.voices_path):
            raise KokoroUnavailableError(
                f"Kokoro model files not found at '{self.model_path}' and '{self.voices_path}'. "
                "Download model weights to enable local Kokoro synthesis."
            )

        try:
            self._active_device = "CPU"
            os.environ["ONNX_PROVIDER"] = "CPUExecutionProvider"
            logger.info("Loading Kokoro TTS model on device 'CPU'...")
            self._kokoro = Kokoro(self.model_path, self.voices_path)
            self._is_loaded = True
            load_time = time.time() - start_time
            logger.info(f"Kokoro TTS model loaded successfully in {load_time:.2f}s.")
        except Exception as e:
            self._is_loaded = False
            self._kokoro = None
            raise KokoroLoadFailedError(f"Failed to load Kokoro ONNX model: {e}")

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into sentences or safe segments under max_text_chars."""
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.max_text_chars:
            return [text]

        # Split on punctuation (sentence boundaries)
        sentences = re.split(r"(?<=[.!?;\n])\s+", text)
        chunks: List[str] = []
        current_chunk = ""

        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if len(s) > self.max_text_chars:
                # If a single sentence exceeds limit, split on commas or spaces
                words = s.split(" ")
                for w in words:
                    if len(current_chunk) + len(w) + 1 <= self.max_text_chars:
                        current_chunk = f"{current_chunk} {w}".strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = w[: self.max_text_chars]
            elif len(current_chunk) + len(s) + 1 <= self.max_text_chars:
                current_chunk = f"{current_chunk} {s}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = s

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _generate_chunk_audio(self, chunk: str, voice: str, speed: float) -> Tuple[bytes, int]:
        """Generate audio for a single text chunk using Kokoro backend."""
        self._ensure_model_loaded()

        try:
            # kokoro.create returns (samples: np.ndarray, sample_rate: int)
            samples, sample_rate = self._kokoro.create(
                chunk,
                voice=voice,
                speed=speed,
                lang="en-us",
            )
            import numpy as np

            int16_samples = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
            pcm_bytes = int16_samples.tobytes()
            return pcm_bytes, sample_rate
        except Exception as e:
            raise KokoroInferenceError(f"Kokoro chunk inference failed for '{chunk[:30]}...': {e}")

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        """Synthesize text into speech audio with single concurrency and timeout protection."""
        text = request.text.strip()
        if not text:
            return SynthesisResult(
                audio=AudioData(data=b""),
                duration_ms=0.0,
                format="wav",
                characters=0,
            )

        voice = request.voice or self.default_voice

        # Execute generation within concurrency lock & timeout
        def _execute_synthesis() -> SynthesisResult:
            with self._lock:
                start_time = time.time()
                chunks = self._chunk_text(text)
                if not chunks:
                    return SynthesisResult(
                        audio=AudioData(data=b""),
                        duration_ms=0.0,
                        format="wav",
                        characters=0,
                    )

                accumulated_pcm = bytearray()
                sample_rate = 24000

                for chunk in chunks:
                    pcm_bytes, sr = self._generate_chunk_audio(chunk, voice=voice, speed=request.speed)
                    accumulated_pcm.extend(pcm_bytes)
                    sample_rate = sr

                # Wrap raw PCM into standard WAV container
                wav_io = io.BytesIO()
                with wave.open(wav_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(accumulated_pcm)
                wav_bytes = wav_io.getvalue()

                elapsed_ms = (time.time() - start_time) * 1000.0
                audio = AudioData(
                    data=wav_bytes,
                    format=AudioFormat(
                        sample_rate=sample_rate,
                        channels=1,
                        bit_depth=16,
                        container="wav",
                    ),
                )
                return SynthesisResult(
                    audio=audio,
                    duration_ms=elapsed_ms,
                    format="wav",
                    characters=len(text),
                )

        future = self._executor.submit(_execute_synthesis)
        try:
            return future.result(timeout=self.timeout_seconds)
        except concurrent.futures.TimeoutError:
            logger.error(f"Kokoro synthesis timed out after {self.timeout_seconds}s for text: '{text[:40]}...'")
            raise KokoroTimeoutError(
                f"Kokoro generation timed out after {self.timeout_seconds}s."
            )
        except Exception as e:
            if isinstance(e, (KokoroUnavailableError, KokoroLoadFailedError, KokoroInferenceError, KokoroTimeoutError)):
                raise e
            raise KokoroInferenceError(f"Kokoro synthesis error: {e}")

    def list_voices(self) -> List[VoiceProfile]:
        """Return available voices supported by Kokoro."""
        return list(self.DEFAULT_VOICES)
