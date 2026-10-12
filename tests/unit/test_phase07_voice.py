"""Unit Tests for Phase 07: Real-Time Voice & Audio Subsystem."""

import pytest
from core.zetta.tools.registry.registry import get_tool_registry
from core.zetta.tools.routing import ToolRouter
from core.zetta.voice.audio.base import AudioCaptureProvider, AudioPlaybackProvider
from core.zetta.voice.audio.device import AudioDeviceManager
from core.zetta.voice.audio.fake import (
    FakeAudioCaptureProvider,
    FakeAudioPlaybackProvider,
    generate_synthetic_pcm_sine,
)
from core.zetta.voice.audio.linux import (
    LinuxALSAAudioCaptureProvider,
    LinuxAudioPlaybackProvider,
)
from core.zetta.voice.controller import VoiceController
from core.zetta.voice.manager import VoiceManager, get_voice_manager, set_voice_manager
from core.zetta.voice.models.audio import (
    AudioChunk,
    AudioData,
    AudioDevice,
    AudioFormat,
)
from core.zetta.voice.models.session import (
    VoiceSession,
    VoiceSessionState,
    VoiceTurn,
)
from core.zetta.voice.models.stt import (
    TranscriptionResult,
    TranscriptionSegment,
)
from core.zetta.voice.models.tts import (
    SynthesisRequest,
    SynthesisResult,
    VoiceProfile,
)
from core.zetta.voice.models.vad import (
    SpeechActivityState,
    VADResult,
)
from core.zetta.voice.speech_to_text.fake import FakeSTTProvider
from core.zetta.voice.text_to_speech.fake import FakeTTSProvider, generate_wav_sine_tone
from core.zetta.voice.vad.detector import EnergyVADDetector
from core.zetta.voice.vad.fake import FakeVADDetector
from shared.types.enums import PermissionLevel


class TestAudioModels:
    """Validate audio data models, telemetry, and privacy enforcement."""

    def test_audio_format_defaults(self):
        fmt = AudioFormat()
        assert fmt.sample_rate == 16000
        assert fmt.channels == 1
        assert fmt.bit_depth == 16
        assert fmt.encoding == "pcm_s16le"
        assert fmt.container == "wav"
        d = fmt.to_dict()
        assert d["sample_rate"] == 16000

    def test_audio_device_model(self):
        dev = AudioDevice(
            id="hw:1,0",
            name="USB Microphone",
            card_index=1,
            device_index=0,
            is_input=True,
            is_default=True,
            backend="alsa",
        )
        assert dev.is_input is True
        assert dev.is_output is False
        d = dev.to_dict()
        assert d["id"] == "hw:1,0"
        assert d["backend"] == "alsa"

    def test_audio_chunk_rms_calculation(self):
        pcm = generate_synthetic_pcm_sine(duration_seconds=0.1, amplitude=5000.0)
        chunk = AudioChunk(chunk_id=1, data=pcm)
        rms = chunk.calculate_rms()
        assert rms > 3000.0  # RMS of sine with amp 5000 is ~3535

    def test_audio_data_privacy_excludes_raw_bytes(self):
        pcm = generate_synthetic_pcm_sine(duration_seconds=0.5, amplitude=6000.0)
        audio = AudioData(data=pcm)
        assert audio.duration_seconds > 0.4
        assert audio.rms_energy > 0.0

        d = audio.to_dict()
        # Privacy check: raw audio bytes must NOT be in dict
        assert "data" not in d
        assert "bytes_length" in d
        assert d["bytes_length"] == len(pcm)
        assert "duration_seconds" in d
        assert "rms_energy" in d

    def test_voice_session_and_turn_models(self):
        session = VoiceSession()
        assert session.session_id.startswith("voice_session_")
        assert session.state == VoiceSessionState.IDLE
        assert len(session.turns) == 0

        turn = VoiceTurn(
            user_transcript="hello zetta",
            assistant_response="hello user",
            duration_ms=120.5,
        )
        session.add_turn(turn)
        assert len(session.turns) == 1
        d = session.to_dict()
        assert d["turn_count"] == 1
        assert d["turns"][0]["user_transcript"] == "hello zetta"


class TestEnergyVADDetector:
    """Validate pure-Python zero-dependency energy VAD detector."""

    def test_silence_detection(self):
        vad = EnergyVADDetector(energy_threshold=500.0)
        # Generate low-amplitude noise
        silence_pcm = generate_synthetic_pcm_sine(duration_seconds=0.05, amplitude=50.0)
        res = vad.process_chunk(silence_pcm)
        assert res.is_speech is False
        assert res.state == SpeechActivityState.SILENCE

    def test_speech_onset_and_hangover(self):
        vad = EnergyVADDetector(energy_threshold=500.0, speech_onset_chunks=2, speech_hangover_chunks=3)
        speech_pcm = generate_synthetic_pcm_sine(duration_seconds=0.05, amplitude=6000.0)
        silence_pcm = generate_synthetic_pcm_sine(duration_seconds=0.05, amplitude=50.0)

        # Chunk 1: Speech onset tentative
        r1 = vad.process_chunk(speech_pcm)
        assert r1.state == SpeechActivityState.SPEECH_POSSIBLE

        # Chunk 2: Speech confirmed active
        r2 = vad.process_chunk(speech_pcm)
        assert r2.state == SpeechActivityState.SPEECH_ACTIVE
        assert r2.is_speech is True

        # Chunk 3: Silence starts -> SPEECH_ENDING
        r3 = vad.process_chunk(silence_pcm)
        assert r3.state == SpeechActivityState.SPEECH_ENDING
        assert r3.is_speech is True

        # Continue silence chunks until hangover expires
        vad.process_chunk(silence_pcm)
        r5 = vad.process_chunk(silence_pcm)
        assert r5.state == SpeechActivityState.SILENCE
        assert r5.is_speech is False

    def test_vad_reset(self):
        vad = EnergyVADDetector()
        speech_pcm = generate_synthetic_pcm_sine(duration_seconds=0.05, amplitude=6000.0)
        vad.process_chunk(speech_pcm)
        vad.process_chunk(speech_pcm)
        assert vad.current_state == SpeechActivityState.SPEECH_ACTIVE
        vad.reset()
        assert vad.current_state == SpeechActivityState.SILENCE


class TestFakeProviders:
    """Validate deterministic offline fake providers."""

    def test_fake_audio_capture_lifecycle(self):
        provider = FakeAudioCaptureProvider(synthetic_duration=0.5, simulate_speech=True)
        assert provider.is_available() is True
        devices = provider.list_devices()
        assert len(devices) >= 1
        assert devices[0].backend == "fake"

        provider.start_capture()
        chunks = []
        while True:
            c = provider.read_chunk()
            if not c:
                break
            chunks.append(c)

        assert len(chunks) == 10
        audio = provider.stop_capture()
        assert isinstance(audio, AudioData)
        assert len(audio.data) > 0
        assert audio.duration_seconds > 0.0

    def test_fake_audio_playback(self):
        provider = FakeAudioPlaybackProvider()
        assert provider.is_available() is True
        pcm = generate_synthetic_pcm_sine(duration_seconds=0.2)
        audio = AudioData(data=pcm)
        assert provider.play(audio) is True
        assert provider.last_played_audio is audio
        assert len(provider.playback_history) == 1

    def test_fake_stt_transcription(self):
        stt = FakeSTTProvider(default_text="Zetta status probe")
        audio = AudioData(data=b"dummy_pcm_bytes", duration_seconds=1.0)
        result = stt.transcribe(audio)
        assert isinstance(result, TranscriptionResult)
        assert result.text == "Zetta status probe"
        assert result.confidence > 0.9
        assert result.is_final is True

        # Test queued custom transcription
        stt.set_next_transcription("Launch browser now")
        res2 = stt.transcribe(audio)
        assert res2.text == "Launch browser now"

    def test_fake_tts_synthesis(self):
        tts = FakeTTSProvider()
        voices = tts.list_voices()
        assert len(voices) >= 1

        req = SynthesisRequest(text="System online and ready")
        result = tts.synthesize(req)
        assert isinstance(result, SynthesisResult)
        assert result.audio.data.startswith(b"RIFF")  # Valid standard WAV header
        assert result.characters == len("System online and ready")
        assert result.duration_ms > 0.0


class TestLinuxAudioProviders:
    """Validate Linux ALSA hardware discovery and fallback behavior."""

    def test_alsa_device_parsing(self):
        mgr = AudioDeviceManager()
        sample_arecord_output = """
**** List of CAPTURE Hardware Devices ****
card 0: PCH [HDA Intel PCH], device 0: ALC269VC Analog [ALC269VC Analog]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: USB [USB Audio Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
"""
        devices = mgr._parse_alsa_devices(sample_arecord_output, is_input=True)
        assert len(devices) == 2
        assert devices[0].id == "hw:0,0"
        assert devices[0].name == "HDA Intel PCH - ALC269VC Analog"
        assert devices[0].is_input is True
        assert devices[1].id == "hw:1,0"
        assert devices[1].name == "USB Audio Device - USB Audio"

    def test_device_manager_lists_defaults(self):
        mgr = AudioDeviceManager()
        inputs = mgr.list_input_devices()
        outputs = mgr.list_output_devices()
        assert len(inputs) >= 1
        assert len(outputs) >= 1
        assert any(d.is_default for d in inputs)
        assert any(d.is_default for d in outputs)


class TestVoiceController:
    """Validate voice controller state machine and turn coordination."""

    def test_controller_state_machine(self):
        capture = FakeAudioCaptureProvider()
        playback = FakeAudioPlaybackProvider()
        stt = FakeSTTProvider(default_text="what is my cpu usage")
        tts = FakeTTSProvider()
        vad = FakeVADDetector()

        controller = VoiceController(
            capture_provider=capture,
            playback_provider=playback,
            stt_provider=stt,
            tts_provider=tts,
            vad_detector=vad,
            play_response_audio=False,
        )
        assert controller.state == VoiceSessionState.IDLE

        transcript = controller.listen_and_transcribe(max_duration=2.0)
        assert transcript.text == "what is my cpu usage"
        assert controller.state == VoiceSessionState.IDLE

        synth = controller.speak("CPU usage is normal")
        assert synth.characters == len("CPU usage is normal")
        assert controller.state == VoiceSessionState.IDLE

    def test_controller_stop_cancellation(self):
        capture = FakeAudioCaptureProvider()
        playback = FakeAudioPlaybackProvider()
        stt = FakeSTTProvider()
        tts = FakeTTSProvider()
        vad = FakeVADDetector()

        controller = VoiceController(
            capture_provider=capture,
            playback_provider=playback,
            stt_provider=stt,
            tts_provider=tts,
            vad_detector=vad,
        )
        controller.stop()
        assert controller.state == VoiceSessionState.STOPPED


class TestVoiceManager:
    """Validate VoiceManager high-level facade."""

    def test_voice_manager_singleton_and_status(self):
        vm = get_voice_manager(use_fake=True)
        assert vm.use_fake is True
        status = vm.status()
        assert status["mode"] == "fake"
        assert status["is_available"] is True
        assert status["session_state"] == "IDLE"

        caps = vm.capabilities()
        assert "audio_input" in caps
        assert "audio_output" in caps
        assert "speech_to_text" in caps
        assert "text_to_speech" in caps

    def test_voice_manager_record_and_synthesize(self):
        vm = VoiceManager(use_fake=True)
        audio = vm.record_clip(duration=0.1)
        assert isinstance(audio, AudioData)
        assert len(audio.data) > 0

        transcript = vm.transcribe(audio)
        assert isinstance(transcript, TranscriptionResult)

        synth = vm.synthesize("Zetta offline test")
        assert isinstance(synth, SynthesisResult)
        assert synth.audio.data.startswith(b"RIFF")

    def test_voice_session_lifecycle(self):
        vm = VoiceManager(use_fake=True)
        session = vm.start_session()
        assert session.session_id.startswith("voice_session_")
        assert vm.get_session(session.session_id) is session

        turn = vm.execute_turn(session_id=session.session_id, max_listen_duration=2.0)
        assert isinstance(turn, VoiceTurn)
        assert len(session.turns) == 1

        stopped = vm.stop_session(session.session_id)
        assert stopped is True
        assert session.state == VoiceSessionState.STOPPED


class TestVoiceTools:
    """Validate registration and permissions of Voice tools in ToolRegistry."""

    def test_all_voice_tools_registered(self):
        registry = get_tool_registry()
        expected_tools = [
            "voice_status",
            "voice_capture",
            "voice_transcribe",
            "voice_synthesize",
            "voice_session",
        ]
        for name in expected_tools:
            tool = registry.get(name)
            assert tool is not None
            assert tool.name == name
            assert tool.category == "voice"

    def test_voice_tools_permissions(self):
        registry = get_tool_registry()
        assert registry.get("voice_status").required_permission == PermissionLevel.LOW
        assert registry.get("voice_capture").required_permission == PermissionLevel.LOW
        assert registry.get("voice_transcribe").required_permission == PermissionLevel.LOW
        assert registry.get("voice_synthesize").required_permission == PermissionLevel.LOW
        assert registry.get("voice_session").required_permission == PermissionLevel.MEDIUM

    def test_voice_tools_execution(self):
        registry = get_tool_registry()
        res_status = registry.execute("voice_status", {"fake": True})
        assert res_status.success is True
        assert res_status.data["mode"] == "fake"

        res_synth = registry.execute("voice_synthesize", {"text": "Hello test", "fake": True})
        assert res_synth.success is True
        assert res_synth.data["characters"] == len("Hello test")

        res_capture = registry.execute("voice_capture", {"duration": 0.1, "fake": True})
        assert res_capture.success is True
        assert "bytes_length" in res_capture.data


class TestVoiceToolRouterIntegration:
    """Validate regex intent pattern routing for voice commands."""

    def test_voice_intent_patterns(self):
        router = ToolRouter()

        intent1 = router.detect_intent("voice status")
        assert intent1 is not None
        assert intent1["tool"] == "voice_status"

        intent2 = router.detect_intent("record a test audio")
        assert intent2 is not None
        assert intent2["tool"] == "voice_capture"

        intent3 = router.detect_intent("transcribe audio")
        assert intent3 is not None
        assert intent3["tool"] == "voice_transcribe"

        intent4 = router.detect_intent("say 'Hello ZETTA'")
        assert intent4 is not None
        assert intent4["tool"] == "voice_synthesize"
        assert intent4["arguments"]["text"] == "Hello ZETTA"

        intent5 = router.detect_intent("start a voice session")
        assert intent5 is not None
        assert intent5["tool"] == "voice_session"
