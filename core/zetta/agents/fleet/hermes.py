"""Hermes-Style Autonomous Agent with Incremental Checkpoints and State Recovery."""

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.ai.brain import get_ai_brain
from core.zetta.events import Event, get_event_bus
from core.zetta.tools.registry import get_tool_registry
from core.zetta.utils.errors import AgentError
from core.zetta.utils.logging import get_logger
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, EventType, PermissionLevel

logger = get_logger("agent_hermes")


@dataclass
class Checkpoint:
    """Snapshot of agent execution state at a discrete step."""
    checkpoint_id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    step_index: int = 0
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HermesAutonomousAgent(BaseAgent):
    """Hermes-style autonomous agent for multi-turn, long-running tasks with checkpointing and state recovery."""

    def __init__(
        self,
        name: str = "HermesAgent",
        required_permission: PermissionLevel = PermissionLevel.HIGH,
        max_steps: int = 20,
        checkpoint_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> None:
        super().__init__(
            name=name,
            description="Autonomous multi-step runtime agent with isolated context, checkpoints, and recovery.",
            capabilities=[AgentCapability.AUTONOMOUS, AgentCapability.GENERAL],
            required_permission=required_permission,
        )
        self.max_steps = max_steps
        self.checkpoint_dir = checkpoint_dir
        self.progress_callback = progress_callback
        self.checkpoints: List[Checkpoint] = []
        self.tool_registry = get_tool_registry()

    def save_checkpoint(self, task_id: str, step_index: int, state: Dict[str, Any]) -> Checkpoint:
        """Record an in-memory and optionally on-disk checkpoint."""
        cp = Checkpoint(
            task_id=task_id,
            step_index=step_index,
            state_snapshot=state,
        )
        self.checkpoints.append(cp)

        if self.checkpoint_dir:
            try:
                self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
                cp_file = self.checkpoint_dir / f"checkpoint_{task_id}_{step_index}.json"
                with open(cp_file, "w", encoding="utf-8") as f:
                    json.dump(asdict(cp), f, indent=2)
            except Exception as e:
                logger.warning(f"Failed to persist checkpoint to disk: {e}")

        logger.debug(f"Saved Checkpoint {cp.checkpoint_id} at step {step_index} for task {task_id}")
        return cp

    def load_last_checkpoint(self) -> Optional[Checkpoint]:
        """Return the most recent execution checkpoint if available."""
        return self.checkpoints[-1] if self.checkpoints else None

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        """Execute autonomous step loop with incremental checkpoints."""
        tools_called = []
        state: Dict[str, Any] = {"history": [], "accumulated_data": {}}
        brain = get_ai_brain()

        # Check for checkpoint resume request in metadata
        resume_cp_id = task.metadata.get("resume_checkpoint_id")
        start_step = 0
        if resume_cp_id:
            for cp in self.checkpoints:
                if cp.checkpoint_id == resume_cp_id:
                    state = dict(cp.state_snapshot)
                    start_step = cp.step_index + 1
                    logger.info(f"Resuming task '{task.name}' from checkpoint at step {start_step}")
                    break

        steps_executed = 0
        for step in range(start_step, self.max_steps):
            if self._is_cancelled:
                return AgentResult(
                    agent_id=self.agent_id,
                    task_id=task.id,
                    success=False,
                    error=ErrorInfo(code="HermesCancelled", message="Autonomous execution cancelled by user."),
                    steps_executed=steps_executed,
                    tools_called=tools_called,
                )

            steps_executed += 1
            progress_msg = f"Executing autonomous step {step + 1}/{self.max_steps} for: {task.name}"
            if self.progress_callback:
                self.progress_callback(step + 1, self.max_steps, progress_msg)

            # Determine next step via AI brain or heuristic
            step_prompt = (
                f"Goal: {task.name}\n"
                f"Details: {task.description}\n"
                f"Step: {step + 1} of {self.max_steps}\n"
                f"Current State: {state}\n"
                f"Decide whether to execute a tool from {task.required_tools} or finish.\n"
                f"If finished, reply with 'TASK_COMPLETE: <summary>'."
            )
            thought_resp = brain.think(prompt=step_prompt)
            thought_text = thought_resp.text.strip()

            state["history"].append(f"Step {step + 1}: {thought_text[:100]}")

            # Check for completion condition
            if "TASK_COMPLETE:" in thought_text or step >= len(task.required_tools):
                # Save final checkpoint
                self.save_checkpoint(task.id, step, state)
                final_summary = thought_text.replace("TASK_COMPLETE:", "").strip() or "Task completed autonomously."
                return AgentResult(
                    agent_id=self.agent_id,
                    task_id=task.id,
                    success=True,
                    data={"summary": final_summary, "steps": steps_executed, "final_state": state},
                    steps_executed=steps_executed,
                    tools_called=tools_called,
                )

            # Otherwise execute next available tool
            if task.required_tools and step < len(task.required_tools):
                tool_to_call = task.required_tools[step]
                if self.tool_registry.get(tool_to_call):
                    res = self.tool_registry.execute(tool_to_call, input_data={}, task_id=task.id)
                    tools_called.append(tool_to_call)
                    state["accumulated_data"][tool_to_call] = res.data if res.success else str(res.error)

            # Record checkpoint
            self.save_checkpoint(task.id, step, state)

        # Reached max steps
        return AgentResult(
            agent_id=self.agent_id,
            task_id=task.id,
            success=True,
            data={"summary": f"Completed after reaching max steps ({self.max_steps})", "final_state": state},
            steps_executed=steps_executed,
            tools_called=tools_called,
        )
