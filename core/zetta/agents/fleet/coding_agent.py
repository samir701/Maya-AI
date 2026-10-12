"""Autonomous Coding Agent with Workspace Inspection, Modification, Testing, and Self-Repair."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.ai.brain import get_ai_brain
from core.zetta.config import get_settings
from core.zetta.tools.registry import get_tool_registry
from core.zetta.utils.logging import get_logger
from shared.types.contracts import AgentContext, AgentResult, ErrorInfo, SubTask
from shared.types.enums import AgentCapability, PermissionLevel

logger = get_logger("agent_coding")


class CodingAgent(BaseAgent):
    """Specialized coding agent with autonomous inspection, code modification, testing, and self-repair loop."""

    def __init__(
        self,
        name: str = "CodingAgent",
        required_permission: PermissionLevel = PermissionLevel.HIGH,
        workspace_root: Optional[Path] = None,
        max_repair_attempts: int = 2,
        confirmation_callback: Optional[Any] = None,
        security_manager: Optional[Any] = None,
    ) -> None:
        super().__init__(
            name=name,
            description="Software engineering agent for workspace inspection, code modification, test execution, and self-repair.",
            capabilities=[AgentCapability.CODING, AgentCapability.GENERAL],
            required_permission=required_permission,
        )
        self.workspace_root = workspace_root or get_settings().root_path
        self.max_repair_attempts = max(0, max_repair_attempts)
        self.confirmation_callback = confirmation_callback
        self.security_manager = security_manager
        self.tool_registry = get_tool_registry()

    def _validate_path(self, target_path: str) -> Path:
        """Enforce strict workspace boundary checks."""
        resolved = (self.workspace_root / target_path).resolve()
        if not str(resolved).startswith(str(self.workspace_root.resolve())):
            raise PermissionError(f"Access denied: Path '{target_path}' lies outside approved workspace root.")
        return resolved

    def _run(self, task: SubTask, context: AgentContext) -> AgentResult:
        """Execute the software engineering lifecycle: Inspect -> Modify -> Test -> Fix -> Verify."""
        tools_called: List[str] = []
        modifications_applied: List[str] = []
        brain = get_ai_brain()

        try:
            action = task.metadata.get("action")
            if action == "inspect":
                files = [p.name for p in self.workspace_root.iterdir()] if self.workspace_root.exists() else []
                return AgentResult(
                    agent_id=self.agent_id,
                    task_id=task.id,
                    success=True,
                    data={"files": files, "workspace": str(self.workspace_root)},
                    steps_executed=1,
                    tools_called=["file_list"],
                )

            # 1. Inspect relevant files
            raw_target = task.metadata.get("target_file") or task.metadata.get("file_path")
            target_file = str(self._validate_path(raw_target)) if raw_target else None
            file_content = ""
            if target_file and Path(target_file).exists():
                read_res = self.tool_registry.execute("file_read", input_data={"path": target_file}, task_id=task.id)
                tools_called.append("file_read")
                if read_res.success:
                    file_content = str(read_res.data)

            # 2. Determine code modification (direct content or AI Brain generation)
            explicit_content = task.metadata.get("content")
            if explicit_content is not None:
                new_code = explicit_content
            else:
                prompt = (
                    f"You are an expert software engineer.\n"
                    f"Task: {task.name}\n"
                    f"Description: {task.description}\n"
                    f"Target File: {target_file}\n"
                    f"Existing Code:\n```\n{file_content}\n```\n"
                    f"Propose the exact new code or modification required."
                )
                response = brain.think(prompt=prompt)
                new_code = response.text

                # If new_code contains markdown code fences, extract the inner block
                if "```python" in new_code:
                    new_code = new_code.split("```python")[1].split("```")[0].strip()
                elif "```" in new_code:
                    new_code = new_code.split("```")[1].split("```")[0].strip()

            # 3. Apply modification if target_file is defined
            if target_file and new_code:
                write_res = self.tool_registry.execute(
                    "file_write",
                    input_data={"path": target_file, "content": new_code},
                    task_id=task.id,
                    confirmation_callback=self.confirmation_callback,
                )
                tools_called.append("file_write")
                if write_res.success:
                    modifications_applied.append(target_file)

            # 4. Run verification tests if a test command is specified
            test_command = task.metadata.get("test_command")
            test_success = True
            test_output = ""

            if test_command:
                test_res = self.tool_registry.execute(
                    "terminal_execute",
                    input_data={"command": test_command},
                    task_id=task.id,
                    confirmation_callback=self.confirmation_callback,
                )
                tools_called.append("terminal_execute")
                test_output = str(test_res.data.get("stdout", "") if test_res.success and isinstance(test_res.data, dict) else test_res.data)
                test_success = test_res.success and test_res.data.get("exit_code", 0) == 0 if isinstance(test_res.data, dict) else test_res.success

                # 5. Self-repair loop if test failed
                repair_count = 0
                while not test_success and repair_count < self.max_repair_attempts:
                    repair_count += 1
                    logger.warning(f"Verification test failed. Initiating self-repair attempt {repair_count}/{self.max_repair_attempts}...")

                    repair_prompt = (
                        f"A code modification caused the following test failure:\n"
                        f"Test Output: {test_output}\n"
                        f"Analyze the failure root cause and provide the corrected code for {target_file}."
                    )
                    fix_resp = brain.think(prompt=repair_prompt)
                    fix_code = fix_resp.text
                    if "```" in fix_code:
                        fix_code = fix_code.split("```")[1].split("```")[0].replace("python\n", "").strip()

                    if target_file and fix_code:
                        self.tool_registry.execute(
                            "file_write",
                            input_data={"path": target_file, "content": fix_code},
                            task_id=task.id,
                            confirmation_callback=self.confirmation_callback,
                        )
                        tools_called.append("file_write")

                    # Re-run test
                    test_res = self.tool_registry.execute(
                        "terminal_execute",
                        input_data={"command": test_command},
                        task_id=task.id,
                        confirmation_callback=self.confirmation_callback,
                    )
                    tools_called.append("terminal_execute")
                    test_output = str(test_res.data.get("stdout", "")) if isinstance(test_res.data, dict) else str(test_res.data)
                    test_success = test_res.success and test_res.data.get("exit_code", 0) == 0 if isinstance(test_res.data, dict) else test_res.success

            data = {
                "modified_files": modifications_applied,
                "verified": test_success,
                "test_command": test_command,
                "summary": f"Completed coding workflow on {target_file or 'workspace'}",
            }

            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=test_success,
                data=data,
                steps_executed=len(tools_called),
                tools_called=tools_called,
            )

        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                task_id=task.id,
                success=False,
                error=ErrorInfo(code="CodingExecutionError", message=str(e)),
                tools_called=tools_called,
            )
