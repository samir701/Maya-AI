"""Unit tests for Unified Autonomous Workflow and Background Task Runner (Phase 08.18 - 08.20)."""

import time
import pytest
from core.zetta.agents.manager.registry import AgentRegistry
from core.zetta.agents.orchestrator.background_runner import BackgroundAgentRunner, JobStatus
from core.zetta.agents.orchestrator.unified_workflow import UnifiedAutonomousWorkflow
from core.zetta.memory.manager import MemoryManager
from core.zetta.security.manager import SecurityManager
from core.zetta.utils.errors import SecurityError


class TestUnifiedAutonomousWorkflow:
    """Tests for Milestone 08.18 & 08.20 Unified Workflow & Memory Integration."""

    def test_end_to_end_research_document_workflow(self):
        reg = AgentRegistry()
        sec = SecurityManager()
        mem = MemoryManager(security=sec)

        workflow = UnifiedAutonomousWorkflow(
            agent_registry=reg,
            memory_manager=mem,
            security_manager=sec,
        )

        # Execute a research and document creation request
        report = workflow.execute_goal(
            goal="Research latest AI trends and generate a summary document",
            user_role="user",
        )

        assert report["success"] is True
        assert report["subtasks_count"] >= 2
        assert report["verification"]["verified"] is True
        assert report["persisted_memory_id"] is not None

        # Verify episodic memory was stored
        mems = mem.retrieve_relevant(query="AI trends", limit=5)
        assert len(mems) > 0
        assert "AI trends" in mems[0].memory.content


    def test_workflow_permission_denial(self):
        sec = SecurityManager()
        workflow = UnifiedAutonomousWorkflow(security_manager=sec)

        # An unknown/unsupported role fails permission check
        with pytest.raises(SecurityError):
            workflow.execute_goal("Some goal", user_role="unknown_unprivileged_role")


class TestBackgroundAgentRunner:
    """Tests for Milestone 08.19 Background Tasks."""

    def test_submit_and_complete_job(self):
        runner = BackgroundAgentRunner(max_workers=2)

        def sample_work(x, y):
            time.sleep(0.05)
            return x + y

        job = runner.submit_job("Addition Job", sample_work, 10, 20)
        assert job.name == "Addition Job"
        assert job.status in [JobStatus.PENDING, JobStatus.RUNNING]

        # Wait for completion
        time.sleep(0.15)
        updated_job = runner.get_job(job.job_id)
        assert updated_job is not None
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.result == 30
        assert updated_job.progress == 1.0

        jobs_list = runner.list_jobs()
        assert len(jobs_list) == 1
        assert jobs_list[0]["name"] == "Addition Job"

        runner.shutdown(wait=True)

    def test_cancel_background_job(self):
        runner = BackgroundAgentRunner(max_workers=2)

        def long_work():
            time.sleep(0.5)
            return "done"

        job = runner.submit_job("Long Job", long_work)
        # Immediately cancel
        cancelled = runner.cancel_job(job.job_id)
        assert cancelled is True
        assert job.status == JobStatus.CANCELLED

        runner.shutdown(wait=True)
