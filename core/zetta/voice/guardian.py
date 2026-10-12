"""ZETTA Voice Guardian for voice identity and permission gating."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from core.zetta.security.manager import SecurityManager, get_security_manager
from core.zetta.utils.errors import SecurityError
from core.zetta.utils.logging import get_logger
from shared.types.enums import PermissionLevel, VoiceAuthLevel

logger = get_logger("voice_guardian")


@dataclass
class VoiceProfile:
    """Registered voice authorization profile."""
    speaker_id: str
    name: str
    auth_level: VoiceAuthLevel = VoiceAuthLevel.AUTHORIZED
    enrolled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseVoiceAuthenticator(ABC):
    """Abstract interface for speaker voice verification."""

    @abstractmethod
    def verify_speaker(self, audio_data: bytes) -> Tuple[VoiceAuthLevel, str, float]:
        """Verify audio snippet and return (auth_level, speaker_id, confidence)."""
        raise NotImplementedError

    @abstractmethod
    def enroll_speaker(self, profile: VoiceProfile, sample_data: Optional[bytes] = None) -> bool:
        """Enroll a speaker profile."""
        raise NotImplementedError


class FakeVoiceAuthenticator(BaseVoiceAuthenticator):
    """Deterministic offline voice authenticator."""

    def __init__(self, default_level: VoiceAuthLevel = VoiceAuthLevel.AUTHORIZED) -> None:
        self.default_level = default_level
        self._profiles: Dict[str, VoiceProfile] = {
            "owner": VoiceProfile(speaker_id="owner", name="Primary User", auth_level=VoiceAuthLevel.AUTHORIZED),
            "guest_1": VoiceProfile(speaker_id="guest_1", name="Guest Speaker", auth_level=VoiceAuthLevel.UNKNOWN),
            "blocked_1": VoiceProfile(speaker_id="blocked_1", name="Restricted User", auth_level=VoiceAuthLevel.RESTRICTED),
        }

    def enroll_speaker(self, profile: VoiceProfile, sample_data: Optional[bytes] = None) -> bool:
        self._profiles[profile.speaker_id] = profile
        return True

    def verify_speaker(self, audio_data: bytes) -> Tuple[VoiceAuthLevel, str, float]:
        if not audio_data:
            return self.default_level, "owner", 1.0

        # Deterministic simulation based on bytes content or length
        content = audio_data.decode("latin1", errors="ignore")
        if "restricted" in content or "blocked" in content:
            return VoiceAuthLevel.RESTRICTED, "blocked_1", 0.95
        elif "guest" in content or "unknown" in content:
            return VoiceAuthLevel.UNKNOWN, "guest_1", 0.50
        else:
            return VoiceAuthLevel.AUTHORIZED, "owner", 0.98


class VoiceGuardian:
    """Enforces speaker authorization and permission gating for voice interactions."""

    def __init__(
        self,
        authenticator: Optional[BaseVoiceAuthenticator] = None,
        security_manager: Optional[SecurityManager] = None,
    ) -> None:
        self.authenticator = authenticator or FakeVoiceAuthenticator()
        self.security = security_manager or get_security_manager()

    def verify_and_gate_permission(
        self,
        audio_data: bytes,
        required_permission: PermissionLevel,
        action: str = "voice_command",
    ) -> Tuple[bool, VoiceAuthLevel, str]:
        """Verify speaker identity and determine if the required permission is granted."""
        auth_level, speaker_id, confidence = self.authenticator.verify_speaker(audio_data)

        # Mapping:
        # AUTHORIZED -> Allows up to HIGH
        # UNKNOWN -> Allows only LOW
        # RESTRICTED -> Allows only LOW or None
        is_allowed = False
        if auth_level == VoiceAuthLevel.AUTHORIZED:
            is_allowed = True
        elif auth_level == VoiceAuthLevel.UNKNOWN:
            is_allowed = (required_permission == PermissionLevel.LOW)
        else:  # RESTRICTED
            is_allowed = False

        status = "GRANTED" if is_allowed else "DENIED"
        self.security.audit.log_event(
            action=f"voice_guardian:{action}",
            actor=f"speaker:{speaker_id}",
            resource="voice_system",
            status=status,
            details={
                "auth_level": auth_level.value,
                "confidence": confidence,
                "required_permission": required_permission.value,
            },
        )

        if not is_allowed:
            logger.warning(
                "Voice guardian rejected %s: speaker '%s' has auth level %s but requires %s",
                action, speaker_id, auth_level.value, required_permission.value
            )
            return False, auth_level, speaker_id

        return True, auth_level, speaker_id


_global_voice_guardian: Optional[VoiceGuardian] = None


def get_voice_guardian(authenticator: Optional[BaseVoiceAuthenticator] = None) -> VoiceGuardian:
    """Get or initialize global VoiceGuardian singleton."""
    global _global_voice_guardian
    if _global_voice_guardian is None:
        _global_voice_guardian = VoiceGuardian(authenticator=authenticator)
    return _global_voice_guardian
