"""Unit tests for Phone Link, Voice Guardian, Comms, and Creator Suite (Phase 08.14 - 08.17)."""

import pytest
from core.zetta.comms.email import FakeEmailProvider
from core.zetta.comms.expenses import FakeExpenseProvider
from core.zetta.comms.manager import CommunicationManager
from core.zetta.comms.messaging import FakeMessagingProvider
from core.zetta.creator.manager import CreatorManager
from core.zetta.creator.provider import FakeMediaProcessor
from core.zetta.phone.fake import FakePhoneProvider
from core.zetta.phone.manager import PhoneManager
from core.zetta.phone.models import DeviceConnectionState
from core.zetta.security.manager import SecurityManager
from core.zetta.utils.errors import SecurityError
from core.zetta.voice.guardian import FakeVoiceAuthenticator, VoiceGuardian
from shared.types.enums import PermissionLevel, VoiceAuthLevel


class TestPhoneLink:
    """Tests for Milestone 08.14 Phone Link Architecture."""

    def test_phone_pairing_and_state(self):
        provider = FakePhoneProvider(default_paired=False)
        manager = PhoneManager(provider=provider)

        assert manager.get_status()["state"] == DeviceConnectionState.DISCONNECTED.value

        # Invalid pairing code
        assert manager.pair_device("123") is False
        assert manager.get_status()["state"] == DeviceConnectionState.DISCONNECTED.value

        # Valid 6-digit code
        assert manager.pair_device("123456") is True
        assert manager.get_status()["state"] == DeviceConnectionState.CONNECTED.value
        assert manager.get_status()["device"]["model"] == "Google Pixel 8 Pro"

        # Disconnect
        manager.disconnect_device()
        assert manager.get_status()["state"] == DeviceConnectionState.DISCONNECTED.value

    def test_phone_commands_and_security(self):
        provider = FakePhoneProvider(default_paired=True)
        sec = SecurityManager()
        manager = PhoneManager(provider=provider, security_manager=sec)

        # Low risk command (ping) succeeds for standard user
        res = manager.send_command("ping", user_role="user")
        assert res["success"] is True
        assert res["pong"] is True

        # High risk command (sms) rejected if confirmation denied or no confirmation callback provided
        with pytest.raises(SecurityError):
            manager.send_command("sms", {"recipient": "+1234567890", "body": "Hi"}, user_role="user")

        # High risk command succeeds when confirmation callback approves
        res_sms = manager.send_command(
            "sms",
            {"recipient": "+1234567890", "body": "Hi"},
            user_role="user",
            confirmation_callback=lambda msg: True,
        )
        assert res_sms["success"] is True
        assert res_sms["status"] == "DELIVERED"


class TestVoiceGuardian:
    """Tests for Milestone 08.15 Voice Guardian."""

    def test_voice_guardian_permission_gating(self):
        auth = FakeVoiceAuthenticator()
        sec = SecurityManager()
        guardian = VoiceGuardian(authenticator=auth, security_manager=sec)

        # Owner audio grants HIGH permission
        allowed, level, speaker = guardian.verify_and_gate_permission(
            b"Hello I am owner", required_permission=PermissionLevel.HIGH
        )
        assert allowed is True
        assert level == VoiceAuthLevel.AUTHORIZED

        # Guest audio allows LOW permission
        allowed_low, level_low, _ = guardian.verify_and_gate_permission(
            b"unknown guest voice", required_permission=PermissionLevel.LOW
        )
        assert allowed_low is True
        assert level_low == VoiceAuthLevel.UNKNOWN

        # Guest audio denied HIGH permission
        allowed_high, level_guest, _ = guardian.verify_and_gate_permission(
            b"unknown guest voice", required_permission=PermissionLevel.HIGH
        )
        assert allowed_high is False
        assert level_guest == VoiceAuthLevel.UNKNOWN

        # Blocked/Restricted voice denied even LOW permission
        allowed_blocked, level_blocked, _ = guardian.verify_and_gate_permission(
            b"restricted speaker", required_permission=PermissionLevel.LOW
        )
        assert allowed_blocked is False
        assert level_blocked == VoiceAuthLevel.RESTRICTED


class TestCommunicationIntegrations:
    """Tests for Milestone 08.16 Communication Integration Architecture."""

    def test_email_and_messaging_dispatch(self):
        email_prov = FakeEmailProvider()
        msg_prov = FakeMessagingProvider()
        exp_prov = FakeExpenseProvider()
        sec = SecurityManager()
        mgr = CommunicationManager(
            email_provider=email_prov,
            messaging_provider=msg_prov,
            expense_provider=exp_prov,
            security_manager=sec,
        )

        # Send email with confirmation
        email_res = mgr.send_email(
            to=["dev@example.com"],
            subject="Release Ready",
            body="Phase 08 verified.",
            user_role="user",
            confirmation_callback=lambda msg: True,
        )
        assert email_res["success"] is True
        assert len(email_prov.sent_messages) == 1

        # Send chat message with confirmation
        chat_res = mgr.send_message(
            recipient="+1987654321",
            content="Tests are passing.",
            channel="whatsapp",
            user_role="user",
            confirmation_callback=lambda msg: True,
        )
        assert chat_res["success"] is True
        assert chat_res["status"] == "DELIVERED"

        # Record expense
        exp_res = mgr.record_expense(
            category="Cloud",
            amount=50.0,
            merchant="AWS",
            user_role="user",
        )
        assert exp_res["success"] is True
        summary = exp_prov.get_summary(category="Cloud")
        assert summary["total"] == 50.0


class TestCreatorSuite:
    """Tests for Milestone 08.17 Creator Suite Architecture."""

    def test_media_processing_and_content_pack(self):
        processor = FakeMediaProcessor()
        sec = SecurityManager()
        mgr = CreatorManager(media_processor=processor, security_manager=sec)

        # Process media
        item = mgr.process_media("sample_tutorial.mp4", user_role="user")
        assert item.media_type == "video"
        assert item.duration_seconds == 120.0
        assert item.resolution == "1920x1080"

        # Generate content pack
        pack = mgr.generate_content_pack(
            topic="ZETTA Autonomous AI Employee",
            transcript="ZETTA is capable of multi-agent planning and computer control.",
            platform="youtube",
            user_role="user",
        )
        assert "ZETTA" in pack.title
        assert len(pack.tags) > 0
        assert "Transcript Summary" in pack.description
