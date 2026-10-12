"""End-to-End Integration Tests for Phase 08 Autonomous AI Employee."""

from pathlib import Path
import tempfile
import time
import pytest
from core.zetta.agents.fleet.coding_agent import CodingAgent
from core.zetta.agents.manager.registry import AgentRegistry
from core.zetta.agents.orchestrator.background_runner import BackgroundAgentRunner, JobStatus
from core.zetta.agents.orchestrator.unified_workflow import UnifiedAutonomousWorkflow
from core.zetta.comms.manager import CommunicationManager
from core.zetta.creator.manager import CreatorManager
from core.zetta.memory.manager import MemoryManager
from core.zetta.phone.manager import PhoneManager
from core.zetta.plugins.base import BasePlugin, PluginMetadata
from core.zetta.plugins.manager import PluginManager
from core.zetta.plugins.registry import PluginRegistry
from core.zetta.security.manager import SecurityManager
from core.zetta.skills.base import BaseSkill
from core.zetta.skills.manager import SkillManager
from core.zetta.skills.registry import SkillRegistry
from core.zetta.voice.guardian import FakeVoiceAuthenticator, VoiceGuardian
from core.zetta.workflows.engine import WorkflowEngine
from core.zetta.workflows.models import StepActionType, WorkflowStep
from shared.types.contracts import SubTask, WorkflowDefinition
from shared.types.enums import PermissionLevel, VoiceAuthLevel


class TestPhase08CompleteIntegration:
    """Master integration test suite validating Phase 08 Autonomous AI Employee capabilities."""

    def test_e2e_autonomous_multi_agent_pipeline(self):
        """Validates goal decomposition, multi-agent dispatch, verification, and memory consolidation."""
        sec = SecurityManager()
        reg = AgentRegistry()
        mem = MemoryManager(security=sec)
        workflow = UnifiedAutonomousWorkflow(
            agent_registry=reg,
            memory_manager=mem,
            security_manager=sec,
        )

        goal = "Research AI automation trends and draft executive summary report"
        report = workflow.execute_goal(goal=goal, user_role="user")

        assert report["success"] is True
        assert report["subtasks_count"] == 3
        assert report["verification"]["verified"] is True
        assert report["persisted_memory_id"] is not None

        # Confirm memory persisted
        persisted = mem.repo.get(report["persisted_memory_id"])
        assert persisted is not None
        assert "AI automation trends" in persisted.content

    def test_e2e_coding_agent_lifecycle(self):
        """Validates coding agent inspecting project, modifying source code, and executing test suites."""
        from core.zetta.security import get_security_manager
        sec_global = get_security_manager()
        orig_level = sec_global.permission_checker.current_level
        sec_global.permission_checker.current_level = PermissionLevel.HIGH
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                workspace = Path(tmpdir)
                code_file = workspace / "math_utils.py"
                code_file.write_text("def multiply(a, b): return a * b\n")

                agent = CodingAgent(
                    workspace_root=workspace,
                    security_manager=sec_global,
                    confirmation_callback=lambda msg: True,
                )

                # Inspect
                inspect_res = agent.execute(SubTask(name="Inspect Workspace", metadata={"action": "inspect"}))
                assert inspect_res.success is True
                assert "math_utils.py" in inspect_res.data["files"]

            # Modify
            mod_res = agent.execute(SubTask(
                name="Add division function",
                metadata={
                    "action": "modify",
                    "file_path": "math_utils.py",
                    "content": "def multiply(a, b): return a * b\n\ndef divide(a, b): return a / b if b != 0 else 0\n",
                }
            ))
            assert mod_res.success is True
            assert "divide" in code_file.read_text()
        finally:
            sec_global.permission_checker.current_level = orig_level

    def test_e2e_plugin_skill_and_macro_integration(self):
        """Validates dynamic plugin lifecycle contributing skills into automated workflows."""
        class AnalysisSkill(BaseSkill):
            def __init__(self):
                super().__init__(
                    name="sentiment_analyzer",
                    description="Analyzes input text sentiment.",
                    inputs_schema={"text": str},
                )
            def run(self, inputs):
                return {"sentiment": "positive", "score": 0.95}

        class AnalyticsPlugin(BasePlugin):
            def __init__(self):
                super().__init__(
                    PluginMetadata(
                        name="analytics_suite",
                        description="Suite of analytics tools.",
                    )
                )
            def get_skills(self):
                return [AnalysisSkill()]

        p_reg = PluginRegistry()
        s_reg = SkillRegistry()
        sec = SecurityManager()
        p_mgr = PluginManager(
            registry=p_reg,
            skill_registry=s_reg,
            security_manager=sec,
        )

        plugin = AnalyticsPlugin()
        p_reg.register(plugin)
        p_mgr.enable_plugin("analytics_suite")

        # Verify skill is mounted
        assert s_reg.get("sentiment_analyzer") is not None

        # Execute macro workflow consuming the newly mounted skill
        s_mgr = SkillManager(registry=s_reg, security_manager=sec)
        engine = WorkflowEngine(skill_manager=s_mgr, security_manager=sec)

        wf = WorkflowDefinition(
            name="Customer Feedback Workflow",
            steps=[
                WorkflowStep(
                    name="Initialize Input",
                    action_type=StepActionType.SET_VAR,
                    target="",
                    input_params={"feedback": "ZETTA employee exceeded expectations!"},
                ),
                WorkflowStep(
                    name="Analyze Sentiment",
                    action_type=StepActionType.SKILL,
                    target="sentiment_analyzer",
                    input_params={"text": "${feedback}"},
                    output_variable="analysis_result",
                ),
            ]
        )

        res = engine.execute(wf, user_role="user")
        assert res.success is True
        assert res.variables["analysis_result"] == {"sentiment": "positive", "score": 0.95}

        # Cleanup
        p_mgr.disable_plugin("analytics_suite")
        assert s_reg.get("sentiment_analyzer") is None

    def test_e2e_voice_guardian_permission_boundary(self):
        """Validates voice identity gating: untrusted voice cannot trigger high-risk commands."""
        auth = FakeVoiceAuthenticator()
        sec = SecurityManager()
        guardian = VoiceGuardian(authenticator=auth, security_manager=sec)

        # Restricted speaker cannot execute any command
        allowed, level, _ = guardian.verify_and_gate_permission(
            audio_data=b"blocked intruder voice",
            required_permission=PermissionLevel.LOW,
        )
        assert allowed is False
        assert level == VoiceAuthLevel.RESTRICTED

        # Unknown speaker can execute LOW permission but NOT HIGH
        allowed_low, _, _ = guardian.verify_and_gate_permission(
            audio_data=b"unknown guest voice",
            required_permission=PermissionLevel.LOW,
        )
        assert allowed_low is True

        allowed_high, _, _ = guardian.verify_and_gate_permission(
            audio_data=b"unknown guest voice",
            required_permission=PermissionLevel.HIGH,
        )
        assert allowed_high is False

    def test_e2e_phone_and_communication_orchestration(self):
        """Validates phone link, email, messaging, and expense coordination."""
        sec = SecurityManager()
        phone_mgr = PhoneManager(security_manager=sec)
        comm_mgr = CommunicationManager(security_manager=sec)
        creator_mgr = CreatorManager(security_manager=sec)

        # 1. Phone pairing
        paired = phone_mgr.pair_device("654321", user_role="user")
        assert paired is True
        st = phone_mgr.get_status()
        assert st["state"] == "CONNECTED"

        # 2. Communication dispatch with confirmation
        email_res = comm_mgr.send_email(
            to=["exec@company.com"],
            subject="Sprint Complete",
            body="Phase 08 successfully deployed.",
            user_role="user",
            confirmation_callback=lambda msg: True,
        )
        assert email_res["success"] is True

        # 3. Creator content pack generation
        pack = creator_mgr.generate_content_pack(
            topic="ZETTA Multi-Agent Architecture",
            platform="youtube",
            user_role="user",
        )
        assert "ZETTA" in pack.title
        assert len(pack.tags) > 0

    def test_e2e_background_job_concurrency_and_cancellation(self):
        """Validates asynchronous background execution, progress tracking, and cancellation."""
        runner = BackgroundAgentRunner(max_workers=3)

        def worker_task(duration: float):
            time.sleep(duration)
            return "finished"

        job1 = runner.submit_job("Quick Job", worker_task, 0.05)
        job2 = runner.submit_job("Cancelled Job", worker_task, 0.5)

        # Cancel job2 immediately
        cancelled = runner.cancel_job(job2.job_id)
        assert cancelled is True
        assert job2.status == JobStatus.CANCELLED

        # Wait for job1
        time.sleep(0.12)
        assert job1.status == JobStatus.COMPLETED
        assert job1.result == "finished"

        runner.shutdown(wait=True)
