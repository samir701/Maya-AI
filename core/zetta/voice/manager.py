"""ZETTA Voice Subsystem Manager Facade."""

import time
from typing import Any, Dict, List, Optional
from core.zetta.config import get_settings
from core.zetta.events import Event, get_event_bus
from core.zetta.utils.errors import ToolError
from core.zetta.utils.logging import get_logger
from core.zetta.voice.audio.base import AudioCaptureProvider, AudioPlaybackProvider
from core.zetta.voice.audio.fake import FakeAudioCaptureProvider, FakeAudioPlaybackProvider
from core.zetta.voice.audio.linux import LinuxALSAAudioCaptureProvider, LinuxAudioPlaybackProvider
from core.zetta.voice.controller import VoiceController
from core.zetta.voice.models.audio import AudioData, AudioDevice
from core.zetta.voice.models.session import (
    VoiceSession,
    VoiceSessionState,
    VoiceTurn,
)
from core.zetta.voice.models.stt import TranscriptionResult
from core.zetta.voice.models.tts import SynthesisResult
from core.zetta.voice.speech_to_text.base import STTProvider
from core.zetta.voice.speech_to_text.fake import FakeSTTProvider
from core.zetta.voice.speech_to_text.groq import GroqWhisperSTTProvider
from core.zetta.voice.speech_to_text.local import LocalSTTProvider
from core.zetta.voice.text_to_speech.base import TTSProvider
from core.zetta.voice.text_to_speech.fake import FakeTTSProvider
from core.zetta.voice.text_to_speech.groq import GroqTTSProvider
from core.zetta.voice.text_to_speech.kokoro import KokoroTTSProvider
from core.zetta.voice.text_to_speech.local import LocalTTSProvider
from core.zetta.voice.text_to_speech.router import TTSRouter
from core.zetta.voice.vad.detector import EnergyVADDetector, VADDetector
from core.zetta.voice.vad.fake import FakeVADDetector
from shared.types.enums import EventType

logger = get_logger("voice_manager")


class VoiceManager:
    """High-level facade and orchestrator for voice and audio operations."""

    def __init__(
        self,
        use_fake: bool = False,
        capture_provider: Optional[AudioCaptureProvider] = None,
        playback_provider: Optional[AudioPlaybackProvider] = None,
        stt_provider: Optional[STTProvider] = None,
        tts_provider: Optional[TTSProvider] = None,
        vad_detector: Optional[VADDetector] = None,
    ) -> None:
        self.use_fake = use_fake
        self.settings = get_settings()
        self.event_bus = get_event_bus()

        # 1. Initialize Audio Capture Provider
        if capture_provider:
            self.capture = capture_provider
        elif use_fake:
            self.capture = FakeAudioCaptureProvider()
        else:
            linux_capture = LinuxALSAAudioCaptureProvider()
            self.capture = linux_capture if linux_capture.is_available() else FakeAudioCaptureProvider()

        # 2. Initialize Audio Playback Provider
        if playback_provider:
            self.playback = playback_provider
        elif use_fake:
            self.playback = FakeAudioPlaybackProvider()
        else:
            linux_playback = LinuxAudioPlaybackProvider()
            self.playback = linux_playback if linux_playback.is_available() else FakeAudioPlaybackProvider()

        # 3. Initialize STT Provider
        stt_mode = getattr(getattr(self.settings, "voice", None), "stt_provider", "fake").lower()
        if stt_provider:
            self.stt = stt_provider
        elif use_fake or stt_mode == "fake":
            self.stt = FakeSTTProvider()
        elif stt_mode == "groq":
            self.stt = GroqWhisperSTTProvider()
        else:
            local_stt = LocalSTTProvider()
            self.stt = local_stt if local_stt.is_available() else FakeSTTProvider()

        # 4. Initialize TTS Provider
        tts_mode = getattr(getattr(self.settings, "voice", None), "tts_provider", "fake").lower()
        if tts_provider:
            self.tts = tts_provider
        elif use_fake or tts_mode == "fake":
            self.tts = FakeTTSProvider()
        elif tts_mode == "groq":
            self.tts = GroqTTSProvider()
        elif tts_mode == "kokoro":
            self.tts = TTSRouter(configured_mode="kokoro")
        else:
            local_tts = LocalTTSProvider()
            self.tts = local_tts if local_tts.is_available() else FakeTTSProvider()

        # 5. Initialize VAD Detector
        if vad_detector:
            self.vad = vad_detector
        elif use_fake:
            self.vad = FakeVADDetector()
        else:
            threshold = getattr(getattr(self.settings, "voice", None), "vad_energy_threshold", 500.0)
            self.vad = EnergyVADDetector(energy_threshold=threshold)

        # 6. Initialize Controller
        self.controller = VoiceController(
            capture_provider=self.capture,
            playback_provider=self.playback,
            stt_provider=self.stt,
            tts_provider=self.tts,
            vad_detector=self.vad,
            event_bus=self.event_bus,
        )

        self._active_sessions: Dict[str, VoiceSession] = {}
        self._current_session_id: Optional[str] = None

    def status(self) -> Dict[str, Any]:
        """Inspect voice subsystem state, devices, and providers."""
        input_devices = self.capture.list_devices()
        output_devices = self.playback.list_devices()

        # AI Provider info
        ai_prov_name = getattr(getattr(self.settings, "ai", None), "default_provider", "fake")
        if ai_prov_name.lower() == "groq":
            ai_cls_name = "GroqAIProvider"
            ai_model = getattr(getattr(self.settings, "ai", None), "groq_llm_model", "openai/gpt-oss-20b")
        elif ai_prov_name.lower() == "fake":
            ai_cls_name = "FakeAIProvider"
            ai_model = "fake-model-v1"
        else:
            ai_cls_name = "OpenAIProvider"
            ai_model = getattr(getattr(self.settings, "ai", None), "default_model", "gpt-4o")

        # STT model info
        stt_model = getattr(self.stt, "model", None)

        # TTS Provider details
        tts_info: Dict[str, Any] = {
            "provider_class": self.tts.__class__.__name__,
            "voice": "af_heart",
            "device": "CPU",
            "loaded": "No",
        }
        fallback_info: Optional[Dict[str, Any]] = None

        if isinstance(self.tts, TTSRouter):
            primary = self.tts.primary
            tts_info["provider_class"] = primary.__class__.__name__
            if hasattr(primary, "default_voice"):
                tts_info["voice"] = getattr(primary, "default_voice", "af_heart")
            if hasattr(primary, "active_device"):
                tts_info["device"] = getattr(primary, "active_device", "CPU")
            if hasattr(primary, "is_loaded"):
                tts_info["loaded"] = "Yes" if getattr(primary, "is_loaded", False) else "No"

            if self.tts.fallback:
                fallback_info = {
                    "provider_class": self.tts.fallback.__class__.__name__,
                    "model": getattr(self.tts.fallback, "model", "canopylabs/orpheus-v1-english"),
                }
        elif isinstance(self.tts, KokoroTTSProvider):
            tts_info["voice"] = self.tts.default_voice
            tts_info["device"] = self.tts.active_device
            tts_info["loaded"] = "Yes" if self.tts.is_loaded else "No"
        elif isinstance(self.tts, GroqTTSProvider):
            tts_info["voice"] = self.tts.default_voice
            tts_info["model"] = self.tts.model

        return {
            "mode": "fake" if self.use_fake else "real",
            "is_available": self.capture.is_available() or self.use_fake,
            "capture_provider": self.capture.__class__.__name__,
            "playback_provider": self.playback.__class__.__name__,
            "stt_provider": self.stt.__class__.__name__,
            "stt_model": stt_model,
            "ai_provider": ai_cls_name,
            "ai_model": ai_model,
            "tts_provider": self.tts.__class__.__name__,
            "tts_details": tts_info,
            "tts_fallback": fallback_info,
            "vad_detector": self.vad.__class__.__name__,
            "input_devices_count": len(input_devices),
            "output_devices_count": len(output_devices),
            "active_session_id": self._current_session_id,
            "session_state": self.controller.state.value,
        }

    def capabilities(self) -> Dict[str, Any]:
        """Check hardware and provider readiness."""
        return {
            "audio_input": {
                "available": self.capture.is_available(),
                "provider": self.capture.__class__.__name__,
                "devices": [d.to_dict() for d in self.capture.list_devices()],
            },
            "audio_output": {
                "available": self.playback.is_available(),
                "provider": self.playback.__class__.__name__,
                "devices": [d.to_dict() for d in self.playback.list_devices()],
            },
            "speech_to_text": {
                "available": self.stt.is_available(),
                "provider": self.stt.__class__.__name__,
            },
            "text_to_speech": {
                "available": self.tts.is_available(),
                "provider": self.tts.__class__.__name__,
            },
        }

    def list_input_devices(self) -> List[AudioDevice]:
        return self.capture.list_devices()

    def list_output_devices(self) -> List[AudioDevice]:
        return self.playback.list_devices()

    def record_clip(
        self,
        duration: float = 3.0,
        device_id: Optional[str] = None,
    ) -> AudioData:
        """Record a fixed-length audio clip."""
        self.capture.start_capture(device_id=device_id)
        start_time = time.time()
        while (time.time() - start_time) < duration:
            chunk = self.capture.read_chunk()
            if not chunk or not chunk.data:
                time.sleep(0.01)
        return self.capture.stop_capture()

    def play_audio(self, audio: AudioData, device_id: Optional[str] = None) -> bool:
        """Play audio data."""
        return self.playback.play(audio, device_id=device_id)

    def transcribe(self, audio: AudioData) -> TranscriptionResult:
        """Transcribe audio to text."""
        return self.stt.transcribe(audio)

    def synthesize(self, text: str, voice: Optional[str] = None) -> SynthesisResult:
        """Synthesize text into speech."""
        from core.zetta.voice.models.tts import SynthesisRequest
        return self.tts.synthesize(SynthesisRequest(text=text, voice=voice))

    def speak(self, text: str, voice: Optional[str] = None) -> SynthesisResult:
        """Synthesize and play speech."""
        return self.controller.speak(text=text, voice=voice)

    def listen(
        self,
        max_duration: float = 10.0,
        device_id: Optional[str] = None,
    ) -> TranscriptionResult:
        """Listen to microphone and return transcription."""
        return self.controller.listen_and_transcribe(max_duration=max_duration, device_id=device_id)

    def start_session(self, device_id: Optional[str] = None) -> VoiceSession:
        """Start a new voice session."""
        session = VoiceSession(audio_device=device_id)
        self._active_sessions[session.session_id] = session
        self._current_session_id = session.session_id

        self.event_bus.publish(
            Event(
                event_type=EventType.VOICE_SESSION_STARTED,
                payload={"session_id": session.session_id},
            )
        )
        return session

    def get_session(self, session_id: Optional[str] = None) -> Optional[VoiceSession]:
        target_id = session_id or self._current_session_id
        return self._active_sessions.get(target_id) if target_id else None

    def execute_turn(
        self,
        session_id: Optional[str] = None,
        max_listen_duration: float = 10.0,
    ) -> VoiceTurn:
        """Execute a full conversational voice turn on the session."""
        session = self.get_session(session_id)
        if not session:
            session = self.start_session()

        return self.controller.execute_voice_turn(
            session=session,
            max_listen_duration=max_listen_duration,
        )

    def stop_session(self, session_id: Optional[str] = None) -> bool:
        """Stop and close an active voice session."""
        target_id = session_id or self._current_session_id
        if not target_id or target_id not in self._active_sessions:
            return False

        session = self._active_sessions[target_id]
        session.state = VoiceSessionState.STOPPED
        self.controller.stop()

        self.event_bus.publish(
            Event(
                event_type=EventType.VOICE_SESSION_STOPPED,
                payload={"session_id": target_id, "turn_count": len(session.turns)},
            )
        )

        if self._current_session_id == target_id:
            self._current_session_id = None

        return True


# Global Singleton
_voice_manager_instance: Optional[VoiceManager] = None


def get_voice_manager(use_fake: bool = False, reload: bool = False) -> VoiceManager:
    """Retrieve or initialize global VoiceManager instance."""
    global _voice_manager_instance
    if _voice_manager_instance is None or reload or (_voice_manager_instance.use_fake != use_fake):
        _voice_manager_instance = VoiceManager(use_fake=use_fake)
    return _voice_manager_instance


def set_voice_manager(manager: Optional[VoiceManager]) -> None:
    """Explicitly set or reset global VoiceManager instance."""
    global _voice_manager_instance
    _voice_manager_instance = manager
