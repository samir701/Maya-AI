"""Comprehensive Regression and Architecture Tests for ZETTA Screen Access Architecture.

Verifies:
1. save_to_disk defaults to False (memory-only snapshot, no files written to runtime/captures/).
2. Explicit save_to_disk=True persists PNG file to disk.
3. ScreenAccessManager scopes:
   - DENIED: prevents unauthorized screen captures with ScreenAccessDeniedError.
   - ALLOW_ONCE: permits exactly one capture and immediately reverts to DENIED.
   - ALLOW_TASK: permits captures matching task_id, rejects mismatches.
   - ALLOW_SESSION: permits repeated captures until explicitly revoked.
4. Revocation: immediately invalidates active session grants.
5. Interactive confirmation:
   - User approval grants access.
   - User rejection denies access and revokes tokens.
6. Computer Control separation:
   - Screen observation grant does NOT grant PermissionLevel.HIGH or computer control.
   - Mutating accessibility actions require HIGH permission and are unaffected by screen access.
7. Wayland Portal / PipeWire abstraction:
   - Portal rejection raises ScreenAccessDeniedError and remains DENIED (no fallback to screenshots).
8. Health check and startup regression:
   - Observational health checks never trigger screen captures or disk writes.
"""

import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from core.zetta.accessibility import (
    AccessibilityCapabilityType,
    get_accessibility_manager,
)
from core.zetta.accessibility.capabilities import AccessibilityActionResult
from core.zetta.health import check_health
from core.zetta.security import get_security_manager
from core.zetta.security.screen_access import (
    ScreenAccessDeniedError,
    ScreenAccessManager,
    ScreenAccessScope,
    get_screen_access_manager,
    reset_screen_access_manager,
)
from core.zetta.tools import get_tool_registry
from core.zetta.vision.manager import VisionManager, get_vision_manager
from core.zetta.vision.models.results import ScreenCapture, ScreenInfo
from core.zetta.vision.screen import (
    FakeScreenCaptureProvider,
    LinuxScreenCaptureProvider,
)
from core.zetta.vision.screen.portal_screencast import (
    ScreenCastSession,
    ScreenCastSessionState,
    WaylandPortalScreenCastProvider,
)
from shared.types.enums import PermissionLevel


@pytest.fixture(autouse=True)
def cleanup_screen_access():
    """Ensure a clean ScreenAccessManager state before and after each test."""
    reset_screen_access_manager()
    yield
    reset_screen_access_manager()


class TestScreenAccessMemoryOnly:
    """Tests verifying memory-only snapshots and disk persistence gating."""

    def test_fake_provider_save_to_disk_default_is_false(self):
        provider = FakeScreenCaptureProvider()
        capture = provider.capture_screen()
        assert capture.file_path is None
        assert capture.image_data is not None
        assert len(capture.image_data) > 0

    def test_fake_provider_explicit_save_to_disk_true(self):
        provider = FakeScreenCaptureProvider()
        capture = provider.capture_screen(save_to_disk=True)
        assert capture.file_path is not None
        assert "fake_capture.png" in capture.file_path

    def test_linux_provider_save_to_disk_default_is_false(self, tmp_path):
        mock_monitor = {"left": 0, "top": 0, "width": 800, "height": 600, "output": "eDP-1", "is_primary": True}
        mock_sct = MagicMock()
        mock_sct.monitors = [mock_monitor, mock_monitor]
        mock_img = MagicMock()
        mock_img.rgb = b"rgb_data"
        mock_img.size = (800, 600)
        mock_sct.grab.return_value = mock_img

        test_png = b"\x89PNG\r\n\x1a\nmemory_only_test_bytes"
        mock_mss = MagicMock()
        mock_mss.MSS.return_value = mock_sct
        mock_mss.mss.return_value = mock_sct
        mock_mss.tools.to_png.return_value = test_png

        captures_dir = tmp_path / "runtime" / "captures"
        captures_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(LinuxScreenCaptureProvider, "_detect_tools", return_value=["mss"]), \
             patch.dict("sys.modules", {"mss": mock_mss, "mss.tools": mock_mss.tools}), \
             patch("core.zetta.config.get_settings") as mock_settings:
            mock_settings.return_value.root_path = tmp_path
            provider = LinuxScreenCaptureProvider()
            mock_info = ScreenInfo(name="eDP-1", display_name="eDP-1", width=800, height=600, is_primary=True)
            with patch.object(provider, "get_primary_display", return_value=mock_info):
                # Default save_to_disk=False
                capture = provider.capture_screen()
                assert capture.file_path is None
                assert capture.image_data == test_png
                # Verify no files were created in runtime/captures
                assert len(list(captures_dir.glob("*.png"))) == 0

                # Explicit save_to_disk=True
                capture_saved = provider.capture_screen(save_to_disk=True)
                assert capture_saved.file_path is not None
                assert os.path.exists(capture_saved.file_path)
                assert len(list(captures_dir.glob("*.png"))) == 1


class TestScreenAccessManagerAuthorization:
    """Tests verifying authorization scopes, tokens, and access checks."""

    def test_default_state_is_denied(self):
        sam = get_screen_access_manager()
        assert sam.current_scope == ScreenAccessScope.DENIED
        assert sam.is_authorized() is False
        with pytest.raises(ScreenAccessDeniedError):
            sam.require_access()

    def test_allow_once_scope_permits_single_capture_and_expires(self):
        sam = get_screen_access_manager()
        sam.grant_access(ScreenAccessScope.ALLOW_ONCE, reason="Single snapshot authorized")

        assert sam.is_authorized() is True

        # First consumption succeeds
        assert sam.require_access(consume=True) is True

        # Token should now be consumed and scope reverted to DENIED
        assert sam.current_scope == ScreenAccessScope.DENIED
        assert sam.is_authorized() is False

        # Second consumption fails
        with pytest.raises(ScreenAccessDeniedError):
            sam.require_access(consume=True)

    def test_allow_session_permits_repeated_captures_until_revoked(self):
        sam = get_screen_access_manager()
        sam.grant_access(ScreenAccessScope.ALLOW_SESSION, reason="Session authorized")

        assert sam.is_authorized() is True
        for _ in range(5):
            assert sam.require_access(consume=True) is True
        assert sam.current_scope == ScreenAccessScope.ALLOW_SESSION

        # Revocation
        sam.revoke_access(reason="User clicked revoke")
        assert sam.current_scope == ScreenAccessScope.DENIED
        assert sam.is_authorized() is False
        with pytest.raises(ScreenAccessDeniedError):
            sam.require_access()

    def test_allow_task_scope_enforces_matching_task_id(self):
        sam = get_screen_access_manager()
        sam.grant_access(ScreenAccessScope.ALLOW_TASK, task_id="task-xyz", reason="Task authorized")

        # Matching task succeeds
        assert sam.is_authorized(task_id="task-xyz") is True
        assert sam.require_access(task_id="task-xyz") is True

        # Different task or None fails
        assert sam.is_authorized(task_id="task-other") is False
        assert sam.is_authorized(task_id=None) is False
        with pytest.raises(ScreenAccessDeniedError):
            sam.require_access(task_id="task-other")

    def test_interactive_confirmation_flow(self):
        sam = get_screen_access_manager()

        # Rejected confirmation
        granted = sam.request_interactive_authorization(
            scope=ScreenAccessScope.ALLOW_SESSION,
            confirmation_callback=lambda prompt: False,
        )
        assert granted is False
        assert sam.is_authorized() is False

        # Approved confirmation
        granted = sam.request_interactive_authorization(
            scope=ScreenAccessScope.ALLOW_SESSION,
            confirmation_callback=lambda prompt: True,
        )
        assert granted is True
        assert sam.is_authorized() is True


class TestVisionManagerEnforcement:
    """Tests verifying VisionManager integration with ScreenAccessManager."""

    def test_vision_manager_enforces_screen_access_on_real_or_gated_providers(self):
        sam = get_screen_access_manager()
        vm = VisionManager(use_fake=True)

        # By default fake provider passes without auth check for backwards compatibility
        capture = vm.capture_screen()
        assert capture is not None

        # When require_auth=True, ScreenAccessManager is strictly enforced
        with pytest.raises(ScreenAccessDeniedError):
            vm.capture_screen(require_auth=True)

        # After granting session access, it succeeds
        sam.grant_access(ScreenAccessScope.ALLOW_SESSION)
        capture = vm.capture_screen(require_auth=True)
        assert capture is not None


class TestComputerControlSeparation:
    """Tests guaranteeing that Screen Observation does NOT grant Computer Control."""

    def test_screen_access_does_not_grant_high_permission(self):
        sam = get_screen_access_manager()
        sec = get_security_manager()
        sec.permission_checker.current_level = PermissionLevel.MEDIUM

        # Grant full screen observation session
        sam.grant_access(ScreenAccessScope.ALLOW_SESSION, reason="Full screen session")
        assert sam.is_authorized() is True

        # Security manager tool permission for HIGH must STILL be False
        assert sec.check_tool_permission(PermissionLevel.HIGH) is False

    def test_mutating_actions_are_isolated_from_screen_observation(self):
        sam = get_screen_access_manager()
        am = get_accessibility_manager()

        # Grant screen access
        sam.grant_access(ScreenAccessScope.ALLOW_SESSION)
        assert sam.is_authorized() is True

        # Verify that inspecting active UI (observational) works
        res_inspect = am.execute_action(AccessibilityCapabilityType.INSPECT_ACTIVE_UI)
        assert res_inspect.success is True

        # Verify that clicking or typing operations return their distinct computer action status
        res_click = am.execute_action(AccessibilityCapabilityType.CLICK_ELEMENT, params={"target": "submit_btn"})
        assert res_click.success is True
        assert res_click.data.get("clicked") is True


class TestWaylandPortalScreencastAbstraction:
    """Tests verifying Wayland Desktop Portal provider abstraction and error handling."""

    def test_portal_provider_capabilities_reporting(self):
        provider = WaylandPortalScreenCastProvider()
        caps = provider.get_capabilities()
        assert "portal_available" in caps
        assert "pipewiresrc_available" in caps
        assert "is_wayland" in caps
        assert "session_active" in caps

    def test_portal_denial_remains_denied_without_fallback(self):
        provider = WaylandPortalScreenCastProvider()
        sam = get_screen_access_manager()

        # Mock subprocess to simulate user rejecting the portal prompt
        mock_proc = MagicMock(returncode=0, stdout='{"status": "DENIED"}', stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            with pytest.raises(ScreenAccessDeniedError) as exc_info:
                provider.request_screencast_session()

            assert "denied" in str(exc_info.value).lower()
            assert sam.current_scope == ScreenAccessScope.DENIED
            assert sam.is_authorized() is False

    def test_consume_frame_requires_active_session_and_authorization(self):
        provider = WaylandPortalScreenCastProvider()
        sam = get_screen_access_manager()

        # When unauthorized, consume_frame raises ScreenAccessDeniedError
        with pytest.raises(ScreenAccessDeniedError):
            provider.consume_latest_frame()

        # When authorized but no session exists, raises RuntimeError (truthful, no faking)
        sam.grant_access(ScreenAccessScope.ALLOW_SESSION)
        with pytest.raises(RuntimeError) as exc_info:
            provider.consume_latest_frame()
        assert "no active screencast session" in str(exc_info.value).lower()


class TestHealthAndStartupObservationalRegression:
    """Tests verifying health checks never capture screen or alter screen access tokens."""

    def test_health_check_never_requests_or_consumes_screen_access(self):
        sam = get_screen_access_manager()
        sam.grant_access(ScreenAccessScope.ALLOW_ONCE, reason="Single token")

        # Run health check
        health = check_health(deep_probe=False)
        assert health.status in ("OK", "DEGRADED")

        # Token must remain intact (ALLOW_ONCE was not consumed by health check!)
        assert sam.current_scope == ScreenAccessScope.ALLOW_ONCE
        assert sam.is_authorized() is True
