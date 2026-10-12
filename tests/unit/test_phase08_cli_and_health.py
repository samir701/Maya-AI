"""Unit tests for Phase 08 CLI Integration and Health Checks (Milestones 08.22 & 08.23)."""

from core.zetta.cli import (
    handle_agent_cli,
    handle_bgjob_cli,
    handle_persona_cli,
    handle_phone_cli,
    handle_plan_cli,
    handle_skill_cli,
)
from core.zetta.health import check_health


class TestPhase08CLI:
    """Tests for Milestone 08.22 CLI Integration."""

    def test_agent_cli_commands(self, capsys):
        handle_agent_cli(["list"])
        out, _ = capsys.readouterr()
        assert "ZETTA AGENT FLEET" in out
        assert "GeneralAssistantAgent" in out

        handle_agent_cli(["status", "GeneralAssistantAgent"])
        out_status, _ = capsys.readouterr()
        assert "Agent: GeneralAssistantAgent" in out_status
        assert "Status: READY" in out_status

    def test_plan_cli_commands(self, capsys):
        handle_plan_cli(["create", "Research robotics and write report"])
        out, _ = capsys.readouterr()
        assert "GENERATED TASK PLAN" in out
        assert "Gather Research Sources" in out

    def test_skill_and_persona_cli_commands(self, capsys):
        handle_skill_cli(["list"])
        out_s, _ = capsys.readouterr()
        assert "ZETTA REUSABLE SKILLS" in out_s

        handle_persona_cli(["list"])
        out_p, _ = capsys.readouterr()
        assert "ZETTA PERSONAS" in out_p
        assert "default" in out_p

        handle_persona_cli(["switch", "professional"])
        out_switch, _ = capsys.readouterr()
        assert "Switched persona to: professional" in out_switch

    def test_phone_and_bgjob_cli_commands(self, capsys):
        handle_phone_cli(["status"])
        out_ph, _ = capsys.readouterr()
        assert "ZETTA PHONE LINK STATUS" in out_ph

        handle_phone_cli(["pair", "123456"])
        out_pair, _ = capsys.readouterr()
        assert "Pairing successful" in out_pair

        handle_bgjob_cli(["list"])
        out_bg, _ = capsys.readouterr()
        assert "ZETTA BACKGROUND JOBS" in out_bg


class TestPhase08Health:
    """Tests for Milestone 08.23 Health System."""

    def test_phase08_health_check_operational(self):
        health = check_health()
        assert health.status == "OK"
        assert "phase08_autonomous_agents" in health.checks
        p8_check = health.checks["phase08_autonomous_agents"]
        assert p8_check["status"] == "OK"
        assert p8_check["planner_ready"] is True
        assert p8_check["workflow_engine_ready"] is True
        assert p8_check["phone_link_ready"] is True
        assert p8_check["voice_guardian_ready"] is True
        assert p8_check["skills_registry_ready"] is True
        assert p8_check["plugin_registry_ready"] is True
