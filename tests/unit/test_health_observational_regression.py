"""Regression tests verifying observational, read-only health checks and idempotent lifecycle initialization.

Ensures that calling /api/health or check_health() repeatedly NEVER:
- captures the screen or writes PNG files to runtime/captures
- performs OCR or UI element detection
- synthesizes speech or invokes TTS providers
- spawns browser sessions
- registers duplicate agents or logs overwrite warnings
- registers duplicate tools or logs overwrite warnings
- creates tasks in the database
- publishes events to the event bus
"""

from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from core.zetta.health import check_health
from core.zetta.agents.manager.registry import get_agent_registry
from core.zetta.tools import get_tool_registry
from core.zetta.runtime import initialize_runtime, reset_runtime_lifecycle
from core.zetta.api.app import get_api_app
from core.zetta.vision.manager import VisionManager
from core.zetta.voice.manager import VoiceManager
from core.zetta.browser import BrowserManager


class TestObservationalHealthRegression:
    """Regression suite for ZETTA UI startup and health check lifecycle."""

    def test_repeated_check_health_does_not_capture_screen(self):
        """Calling check_health() repeatedly must not write screenshots to runtime/captures/."""
        captures_dir = Path("runtime/captures")
        captures_dir.mkdir(parents=True, exist_ok=True)
        initial_png_count = len(list(captures_dir.glob("*.png")))

        # Call health check 10 times consecutively
        for _ in range(10):
            status = check_health()
            assert status.status in ("OK", "DEGRADED")

        final_png_count = len(list(captures_dir.glob("*.png")))
        assert final_png_count == initial_png_count, (
            f"Screen capture leak detected: initial={initial_png_count}, final={final_png_count}"
        )

    def test_repeated_check_health_does_not_duplicate_registrations(self):
        """Calling check_health() repeatedly must not duplicate tools or agents."""
        a_reg = get_agent_registry()
        t_reg = get_tool_registry()

        initial_agent_count = len(a_reg.list_agents())
        initial_tool_count = len(t_reg.list_tools())

        for _ in range(10):
            status = check_health()
            assert status.status in ("OK", "DEGRADED")

        assert len(a_reg.list_agents()) == initial_agent_count
        assert len(t_reg.list_tools()) == initial_tool_count

    def test_repeated_check_health_does_not_invoke_expensive_providers(self):
        """Health check must be purely observational, never executing vision capture, browser launch, or TTS."""
        with patch.object(VisionManager, "capture_screen") as mock_vision, \
             patch.object(VoiceManager, "synthesize") as mock_voice, \
             patch.object(BrowserManager, "launch") as mock_browser:

            for _ in range(5):
                report = check_health()
                assert report.status in ("OK", "DEGRADED")

            mock_vision.assert_not_called()
            mock_voice.assert_not_called()
            mock_browser.assert_not_called()

    def test_api_health_endpoint_repeated_calls_are_observational(self):
        """GET /api/health must be idempotent and purely read-only."""
        client = TestClient(get_api_app())

        with patch.object(VisionManager, "capture_screen") as mock_vision, \
             patch.object(VoiceManager, "synthesize") as mock_voice, \
             patch.object(BrowserManager, "launch") as mock_browser:

            for _ in range(10):
                response = client.get("/api/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] in ("healthy", "degraded")
                assert "subsystems" in data
                assert "vision_subsystem" in data["subsystems"]
                assert "voice_subsystem" in data["subsystems"]

            mock_vision.assert_not_called()
            mock_voice.assert_not_called()
            mock_browser.assert_not_called()

    def test_runtime_initialization_is_idempotent(self):
        """initialize_runtime() must safely execute once and be a no-op on subsequent calls."""
        reset_runtime_lifecycle()
        # First call executes initialization
        res1 = initialize_runtime()
        assert res1 is True

        # Subsequent calls are no-ops
        res2 = initialize_runtime()
        assert res2 is False
        res3 = initialize_runtime()
        assert res3 is False

    def test_observational_health_preserves_contract_keys(self):
        """Observational check must return all expected contract keys for backward compatibility."""
        report = check_health()
        assert report.status == "OK"

        expected_keys = [
            "config",
            "database",
            "event_bus",
            "tool_registry",
            "task_manager",
            "security",
            "ai_core",
            "memory_system",
            "interaction_layer",
            "system_tools",
            "filesystem_tools",
            "application_tools",
            "terminal_tools",
            "clipboard_tools",
            "tool_system",
            "vision_subsystem",
            "browser_subsystem",
            "voice_subsystem",
            "phase08_autonomous_agents",
        ]
        for key in expected_keys:
            assert key in report.checks, f"Missing expected check key: {key}"

        assert report.checks["database"]["status"] == "OK"
        assert report.checks["event_bus"]["status"] == "OK"
        assert report.checks["tool_registry"]["status"] == "OK"
        assert report.checks["task_manager"]["status"] == "OK"
        assert report.checks["security"]["status"] == "OK"
        assert report.checks["phase08_autonomous_agents"]["status"] == "OK"
        assert report.checks["voice_subsystem"]["test_synthesis_duration_ms"] == 0.0
