"""Audio Capture, Playback, and Hardware Management."""

from core.zetta.voice.audio.base import AudioCaptureProvider, AudioPlaybackProvider
from core.zetta.voice.audio.device import AudioDeviceManager
from core.zetta.voice.audio.fake import FakeAudioCaptureProvider, FakeAudioPlaybackProvider
from core.zetta.voice.audio.linux import LinuxALSAAudioCaptureProvider, LinuxAudioPlaybackProvider

__all__ = [
    "AudioCaptureProvider",
    "AudioPlaybackProvider",
    "AudioDeviceManager",
    "FakeAudioCaptureProvider",
    "FakeAudioPlaybackProvider",
    "LinuxALSAAudioCaptureProvider",
    "LinuxAudioPlaybackProvider",
]
