"""ZETTA Voice Controller — Session Lifecycle and Turn Coordination."""

import time
from typing import TYPE_CHECKING, Any, Optional
from core.zetta.events import Event, EventBus, get_event_bus
from core.zetta.utils.errors import ToolError
from core.zetta.utils.logging import get_logger
from core.zetta.voice.audio.base import AudioCaptureProvider, AudioPlaybackProvider
from core.zetta.voice.models.audio import AudioData
from core.zetta.voice.models.session import (
    VoiceSession,
    VoiceSessionState,
    VoiceTurn,
)
from core.zetta.voice.models.stt import TranscriptionResult
from core.zetta.voice.models.tts import SynthesisRequest, SynthesisResult
from core.zetta.voice.models.vad import SpeechActivityState
from core.zetta.voice.speech_to_text.base import STTProvider
from core.zetta.voice.text_to_speech.base import TTSProvider
from core.zetta.voice.vad.detector import VADDetector
from shared.types.enums import EventType

if TYPE_CHECKING:
    from core.zetta.interaction.manager import InteractionManager

logger = get_logger("voice_controller")


class VoiceController:
    """Coordinates voice activity detection, capture, STT, interaction, and TTS."""

    def __init__(
        self,
        capture_provider: AudioCaptureProvider,
        playback_provider: AudioPlaybackProvider,
        stt_provider: STTProvider,
        tts_provider: TTSProvider,
        vad_detector: VADDetector,
        interaction_manager: Optional[Any] = None,
        event_bus: Optional[EventBus] = None,
        play_response_audio: bool = True,
    ) -> None:
        self.capture = capture_provider
        self.playback = playback_provider
        self.stt = stt_provider
        self.tts = tts_provider
        self.vad = vad_detector
        self._interaction_manager = interaction_manager
        self.event_bus = event_bus or get_event_bus()
        self.play_response_audio = play_response_audio

        self._current_state = VoiceSessionState.IDLE
        self._is_cancelled = False

    @property
    def interaction_manager(self) -> Any:
        if self._interaction_manager is None:
            from core.zetta.interaction.manager import get_interaction_manager
            self._interaction_manager = get_interaction_manager()
        return self._interaction_manager

    @property
    def state(self) -> VoiceSessionState:
        return self._current_state

    def stop(self) -> None:
        """Cancel current voice activity immediately."""
        self._is_cancelled = True
        self._current_state = VoiceSessionState.STOPPED
        try:
            self.capture.stop_capture()
        except Exception:
            pass
        try:
            self.playback.stop()
        except Exception:
            pass

    def listen_and_transcribe(
        self,
        max_duration: float = 10.0,
        device_id: Optional[str] = None,
    ) -> TranscriptionResult:
        """Listen to microphone until speech ends or timeout, then transcribe."""
        self._is_cancelled = False
        self._current_state = VoiceSessionState.LISTENING
        self.vad.reset()

        self.event_bus.publish(
            Event(
                event_type=EventType.VOICE_RECORDING_STARTED,
                payload={"max_duration": max_duration, "device_id": device_id},
            )
        )

        try:
            self.capture.start_capture(device_id=device_id)
        except Exception as e:
            self._current_state = VoiceSessionState.ERROR
            raise ToolError(f"Failed to start audio capture: {e}")

        start_time = time.time()
        speech_started = False
        consecutive_empty = 0

        while not self._is_cancelled and (time.time() - start_time) < max_duration:
            chunk = self.capture.read_chunk()
            if not chunk or not chunk.data:
                consecutive_empty += 1
                if consecutive_empty >= 5 and speech_started:
                    break
                elif consecutive_empty >= 25:
                    break
                time.sleep(0.01)
                continue

            consecutive_empty = 0
            vad_result = self.vad.process_chunk(chunk.data)

            if vad_result.is_speech and not speech_started:
                speech_started = True
                self.event_bus.publish(
                    Event(
                        event_type=EventType.VOICE_SPEECH_DETECTED,
                        payload={"energy": vad_result.energy},
                    )
                )

            # If speech started and then transitioned back to silence, speech turn is complete
            if speech_started and vad_result.state == SpeechActivityState.SILENCE:
                logger.info("Speech end detected by VAD.")
                break

        # Stop capture and collect audio
        audio_data = self.capture.stop_capture()
        self.event_bus.publish(
            Event(
                event_type=EventType.VOICE_RECORDING_STOPPED,
                payload={"duration_seconds": audio_data.duration_seconds},
            )
        )

        # Transcribe
        self._current_state = VoiceSessionState.PROCESSING
        self.event_bus.publish(
            Event(
                event_type=EventType.VOICE_TRANSCRIPTION_STARTED,
                payload={"audio_samples": audio_data.num_samples},
            )
        )

        transcript = self.stt.transcribe(audio_data)

        self.event_bus.publish(
            Event(
                event_type=EventType.VOICE_TRANSCRIPTION_COMPLETED,
                payload={"text": transcript.text, "confidence": transcript.confidence},
            )
        )

        self._current_state = VoiceSessionState.IDLE
        return transcript

    def speak(self, text: str, voice: Optional[str] = None) -> SynthesisResult:
        """Synthesize text and play audio through speaker (suspends microphone to prevent echo)."""
        self._current_state = VoiceSessionState.SPEAKING
        self.event_bus.publish(
            Event(
                event_type=EventType.VOICE_SYNTHESIS_STARTED,
                payload={"text": text, "voice": voice},
            )
        )

        request = SynthesisRequest(text=text, voice=voice)
        result = self.tts.synthesize(request)

        self.event_bus.publish(
            Event(
                event_type=EventType.VOICE_SYNTHESIS_COMPLETED,
                payload={"duration_ms": result.duration_ms, "characters": result.characters},
            )
        )

        if self.play_response_audio and result.audio.data:
            self.playback.play(result.audio)

        self._current_state = VoiceSessionState.IDLE
        return result

    def execute_voice_turn(
        self,
        session: VoiceSession,
        max_listen_duration: float = 10.0,
    ) -> VoiceTurn:
        """Execute a complete interactive voice turn: listen -> transcribe -> think/route -> speak."""
        turn_start = time.time()

        # 1. Listen & Transcribe
        transcript = self.listen_and_transcribe(
            max_duration=max_listen_duration,
            device_id=session.audio_device,
        )
        user_text = transcript.text.strip()

        if not user_text:
            turn = VoiceTurn(
                user_transcript="",
                assistant_response="I didn't catch that. Could you please repeat?",
                duration_ms=(time.time() - turn_start) * 1000.0,
            )
            session.add_turn(turn)
            return turn

        # 2. Forward to InteractionManager for full AI / Tool / Task routing & Security gating
        try:
            assistant_response = self.interaction_manager.process_user_message(
                session_id=session.session_id,
                user_input=user_text,
            )
        except Exception as e:
            logger.warning(f"Voice interaction turn encountered error: {e}")
            assistant_response = f"Command Error: {e}"

        # 3. Speak the assistant response (TTS)
        if assistant_response:
            self.speak(assistant_response)

        turn_duration = (time.time() - turn_start) * 1000.0
        turn = VoiceTurn(
            user_transcript=user_text,
            assistant_response=assistant_response,
            duration_ms=turn_duration,
        )
        session.add_turn(turn)
        return turn
