"""ZETTA Real-Time Voice & Audio Subsystem (Phase 07)."""

from core.zetta.voice.audio import (
    AudioCaptureProvider,
    AudioDeviceManager,
    AudioPlaybackProvider,
    FakeAudioCaptureProvider,
    FakeAudioPlaybackProvider,
    LinuxALSAAudioCaptureProvider,
    LinuxAudioPlaybackProvider,
)
from core.zetta.voice.controller import VoiceController
from core.zetta.voice.manager import (
    VoiceManager,
    get_voice_manager,
    set_voice_manager,
)
from core.zetta.voice.models import (
    AudioChunk,
    AudioData,
    AudioDevice,
    AudioFormat,
    SpeechActivityState,
    SynthesisRequest,
    SynthesisResult,
    TranscriptionResult,
    TranscriptionSegment,
    VADResult,
    VoiceProfile,
    VoiceSession,
    VoiceSessionState,
    VoiceTurn,
)
from core.zetta.voice.speech_to_text import (
    FakeSTTProvider,
    LocalSTTProvider,
    STTProvider,
)
from core.zetta.voice.text_to_speech import (
    FakeTTSProvider,
    LocalTTSProvider,
    TTSProvider,
    generate_wav_sine_tone,
)
from core.zetta.voice.vad import (
    EnergyVADDetector,
    FakeVADDetector,
    VADDetector,
)

__all__ = [
    # Manager & Controller
    "VoiceManager",
    "get_voice_manager",
    "set_voice_manager",
    "VoiceController",
    # Models
    "AudioFormat",
    "AudioDevice",
    "AudioChunk",
    "AudioData",
    "SpeechActivityState",
    "VADResult",
    "TranscriptionSegment",
    "TranscriptionResult",
    "VoiceProfile",
    "SynthesisRequest",
    "SynthesisResult",
    "VoiceSessionState",
    "VoiceTurn",
    "VoiceSession",
    # Audio Providers
    "AudioCaptureProvider",
    "AudioPlaybackProvider",
    "AudioDeviceManager",
    "FakeAudioCaptureProvider",
    "FakeAudioPlaybackProvider",
    "LinuxALSAAudioCaptureProvider",
    "LinuxAudioPlaybackProvider",
    # STT & TTS Providers
    "STTProvider",
    "FakeSTTProvider",
    "LocalSTTProvider",
    "TTSProvider",
    "FakeTTSProvider",
    "LocalTTSProvider",
    "generate_wav_sine_tone",
    # VAD
    "VADDetector",
    "EnergyVADDetector",
    "FakeVADDetector",
]
