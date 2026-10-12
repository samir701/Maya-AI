"""Voice and Audio Control Tools for ZETTA Tool Registry."""

from typing import Any, Dict
from core.zetta.tools.base.base_tool import Tool
from core.zetta.voice.manager import get_voice_manager
from shared.types.enums import PermissionLevel


class VoiceStatusTool(Tool):
    """Tool to inspect audio devices and voice subsystem readiness."""
    name = "voice_status"
    description = "Inspect audio input/output devices and speech recognition/synthesis readiness."
    required_permission = PermissionLevel.LOW
    category = "voice"
    input_schema = {
        "type": "object",
        "properties": {
            "fake": {"type": "boolean", "description": "Run in deterministic fake mode", "default": False},
        },
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        use_fake = input_data.get("fake", False)
        vm = get_voice_manager(use_fake=use_fake)
        return vm.status()


class VoiceCaptureTool(Tool):
    """Tool to capture an ephemeral audio clip for testing or input analysis."""
    name = "voice_capture"
    description = "Record a short audio sample from active microphone."
    required_permission = PermissionLevel.LOW
    category = "voice"
    input_schema = {
        "type": "object",
        "properties": {
            "duration": {"type": "number", "description": "Duration in seconds to record", "default": 2.0},
            "device_id": {"type": "string", "description": "Target input audio device ID"},
            "fake": {"type": "boolean", "description": "Run in deterministic fake mode", "default": False},
        },
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        duration = float(input_data.get("duration", 2.0))
        device_id = input_data.get("device_id")
        use_fake = input_data.get("fake", False)

        vm = get_voice_manager(use_fake=use_fake)
        audio = vm.record_clip(duration=duration, device_id=device_id)
        # Return privacy-safe metadata dict
        return audio.to_dict()


class VoiceTranscribeTool(Tool):
    """Tool to transcribe recorded or synthetic audio data into text."""
    name = "voice_transcribe"
    description = "Transcribe audio into text using configured STT provider."
    required_permission = PermissionLevel.LOW
    category = "voice"
    input_schema = {
        "type": "object",
        "properties": {
            "duration": {"type": "number", "description": "Sample audio duration if capturing new audio", "default": 2.0},
            "fake": {"type": "boolean", "description": "Run in deterministic fake mode", "default": False},
        },
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        duration = float(input_data.get("duration", 2.0))
        use_fake = input_data.get("fake", False)

        vm = get_voice_manager(use_fake=use_fake)
        audio = vm.record_clip(duration=duration)
        transcript = vm.transcribe(audio)
        return transcript.to_dict()


class VoiceSynthesizeTool(Tool):
    """Tool to synthesize text into audible speech using TTS."""
    name = "voice_synthesize"
    description = "Synthesize text into speech audio and optionally play through speaker."
    required_permission = PermissionLevel.LOW
    category = "voice"
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text message to speak"},
            "voice": {"type": "string", "description": "Optional voice persona name"},
            "play": {"type": "boolean", "description": "Whether to play audio via speaker", "default": False},
            "fake": {"type": "boolean", "description": "Run in deterministic fake mode", "default": False},
        },
        "required": ["text"],
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        text = input_data.get("text", "")
        voice = input_data.get("voice")
        play = input_data.get("play", False)
        use_fake = input_data.get("fake", False)

        if not text:
            raise ValueError("Parameter 'text' is required for voice synthesis.")

        vm = get_voice_manager(use_fake=use_fake)
        result = vm.synthesize(text=text, voice=voice)
        if play and result.audio.data:
            vm.play_audio(result.audio)
        return result.to_dict()


class VoiceSessionTool(Tool):
    """Tool to manage interactive conversational voice sessions."""
    name = "voice_session"
    description = "Start, execute turn, or stop an interactive voice session."
    required_permission = PermissionLevel.MEDIUM
    category = "voice"
    input_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "Action: 'start', 'turn', 'stop', 'status'", "default": "turn"},
            "session_id": {"type": "string", "description": "Target voice session ID"},
            "fake": {"type": "boolean", "description": "Run in deterministic fake mode", "default": False},
        },
    }

    def run(self, input_data: Dict[str, Any]) -> Any:
        action = input_data.get("action", "turn").lower()
        session_id = input_data.get("session_id")
        use_fake = input_data.get("fake", False)

        vm = get_voice_manager(use_fake=use_fake)
        if action == "start":
            session = vm.start_session()
            return session.to_dict()

        elif action == "turn":
            turn = vm.execute_turn(session_id=session_id)
            return turn.to_dict()

        elif action == "stop":
            stopped = vm.stop_session(session_id=session_id)
            return {"stopped": stopped}

        elif action == "status":
            sess = vm.get_session(session_id)
            return sess.to_dict() if sess else {"status": "none"}

        else:
            raise ValueError(f"Unknown voice session action '{action}'. Valid actions: start, turn, stop, status.")
