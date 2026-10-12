"""Unit tests for Milestone 08.5 Hermes Autonomous Agent."""

import tempfile
from pathlib import Path
import pytest
from core.zetta.agents.fleet.hermes import Checkpoint, HermesAutonomousAgent
from shared.types.contracts import SubTask
from shared.types.enums import AgentCapability, PermissionLevel, TaskStatus


class TestHermesAgent:
    """Test suite for HermesAutonomousAgent checkpointing and execution loop."""

    def test_hermes_agent_initialization(self):
        agent = HermesAutonomousAgent(required_permission=PermissionLevel.MEDIUM)
        assert agent.name == "HermesAgent"
        assert AgentCapability.AUTONOMOUS in agent.capabilities
        assert len(agent.checkpoints) == 0

    def test_hermes_agent_execution_and_checkpointing(self):
        progress_reports = []

        def on_progress(step, total, msg):
            progress_reports.append((step, total, msg))

        agent = HermesAutonomousAgent(
            required_permission=PermissionLevel.MEDIUM,
            max_steps=5,
            progress_callback=on_progress,
        )
        task = SubTask(name="Autonomous Data Aggregation", description="Gather metrics and report")
        result = agent.execute(task)

        assert result.success is True
        assert result.steps_executed >= 1
        assert len(agent.checkpoints) >= 1
        assert len(progress_reports) >= 1

        last_cp = agent.load_last_checkpoint()
        assert last_cp is not None
        assert last_cp.task_id == task.id
        assert "history" in last_cp.state_snapshot

    def test_hermes_checkpoint_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cp_dir = Path(tmpdir)
            agent = HermesAutonomousAgent(
                required_permission=PermissionLevel.MEDIUM,
                checkpoint_dir=cp_dir,
                max_steps=3,
            )
            task = SubTask(name="Check Disk and Persist")
            result = agent.execute(task)

            assert result.success is True
            # Verify JSON checkpoint files exist in tmpdir
            cp_files = list(cp_dir.glob("*.json"))
            assert len(cp_files) >= 1

    def test_hermes_agent_cancellation(self):
        agent = HermesAutonomousAgent(required_permission=PermissionLevel.MEDIUM)
        task = SubTask(name="Cancellable Long Operation")
        agent._is_cancelled = True

        result = agent.execute(task)
        assert result.success is False
        assert result.error.code in ("AgentCancelled", "HermesCancelled")
