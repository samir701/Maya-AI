"""Integration Tests for Phase 07: Real-Time Voice & Audio Subsystem."""

import pytest
from core.zetta.health import check_health
from core.zetta.interaction.session import get_session_manager
from core.zetta.security import get_security_manager
from core.zetta.tools.registry.registry import get_tool_registry
from core.zetta.voice.audio.fake import FakeAudioCaptureProvider, FakeAudioPlaybackProvider
from core.zetta.voice.controller import VoiceController
from core.zetta.voice.manager import VoiceManager, get_voice_manager
from core.zetta.voice.models.session import VoiceSession
from core.zetta.voice.speech_to_text.fake import FakeSTTProvider
from core.zetta.voice.text_to_speech.fake import FakeTTSProvider
from core.zetta.voice.vad.fake import FakeVADDetector
from shared.types.enums import PermissionLevel


class TestPhase07Integration:
    """End-to-End and Security Integration Tests for Voice Subsystem."""

    def test_e2e_voice_spoken_tool_intent_execution(self):
        """Spoken command 'what is my cpu usage' executes tool via ToolRouter and responds with speech."""
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
            play_response_audio=True,
        )

        session = VoiceSession()
        turn = controller.execute_voice_turn(session=session, max_listen_duration=2.0)

        assert turn.user_transcript == "what is my cpu usage"
        # ToolRouter should detect system_cpu_usage tool and execute it
        assert "Executed Tool 'system_cpu_usage'" in turn.assistant_response
        assert playback.last_played_audio is not None
        assert playback.last_played_audio.data.startswith(b"RIFF")
        assert len(session.turns) == 1

    def test_e2e_spoken_command_security_confirmation_enforced(self):
        """Spoken command requiring HIGH permission (file_delete) cannot bypass ConfirmationPolicy."""
        capture = FakeAudioCaptureProvider()
        playback = FakeAudioPlaybackProvider()
        # Direct tool invocation format that routes to file_delete
        stt = FakeSTTProvider(
            default_text='{"tool": "file_delete", "arguments": {"path": "dummy.txt"}}'
        )
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

        session = VoiceSession()
        turn = controller.execute_voice_turn(session=session, max_listen_duration=2.0)

        # file_delete requires CRITICAL permission; without grant/confirmation, it MUST fail or be rejected
        assert any(
            phrase in turn.assistant_response
            for phrase in ("AuthorizationError", "Cannot execute tool 'file_delete'", "Tool Execution Failed", "was cancelled by user")
        )

    def test_e2e_voice_ai_conversation(self):
        """Spoken conversation prompt routes to AIBrain and synthesizes assistant reply."""
        capture = FakeAudioCaptureProvider()
        playback = FakeAudioPlaybackProvider()
        stt = FakeSTTProvider(default_text="Hello ZETTA tell me about your capabilities")
        tts = FakeTTSProvider()
        vad = FakeVADDetector()

        controller = VoiceController(
            capture_provider=capture,
            playback_provider=playback,
            stt_provider=stt,
            tts_provider=tts,
            vad_detector=vad,
            play_response_audio=True,
        )

        session = VoiceSession()
        turn = controller.execute_voice_turn(session=session, max_listen_duration=2.0)

        assert turn.user_transcript == "Hello ZETTA tell me about your capabilities"
        assert len(turn.assistant_response) > 10
        assert playback.last_played_audio is not None

    def test_e2e_multi_turn_voice_session(self):
        """Multi-turn voice session accumulates conversation history in SessionManager."""
        vm = VoiceManager(use_fake=True)
        session = vm.start_session()

        # Turn 1
        t1 = vm.execute_turn(session_id=session.session_id, max_listen_duration=2.0)
        assert t1.user_transcript != ""
        assert len(session.turns) == 1

        # Turn 2
        t2 = vm.execute_turn(session_id=session.session_id, max_listen_duration=2.0)
        assert t2.user_transcript != ""
        assert len(session.turns) == 2

        vm.stop_session(session.session_id)
        assert session.state.value == "STOPPED"

    def test_e2e_voice_health_check_integration(self):
        """System health check passes with voice subsystem reporting OK."""
        health = check_health()
        assert health.status == "OK"
        assert "voice_subsystem" in health.checks
        voice_check = health.checks["voice_subsystem"]
        assert voice_check["status"] in ("OK", "DEGRADED")
        assert "capture_provider" in voice_check
        assert "playback_provider" in voice_check
        assert "test_synthesis_duration_ms" in voice_check
