"""ZETTA Workflow and Macro Execution Engine."""

import re
import time
from typing import Any, Callable, Dict, List, Optional
from core.zetta.agents.manager.manager import AgentManager, get_agent_manager
from core.zetta.security.manager import SecurityManager, get_security_manager
from core.zetta.skills.manager import SkillManager, get_skill_manager
from core.zetta.tools.registry import ToolRegistry, get_tool_registry
from core.zetta.utils.errors import ExecutionError, SecurityError
from core.zetta.utils.logging import get_logger
from core.zetta.workflows.models import StepActionType, WorkflowExecutionResult, WorkflowStep
from shared.types.contracts import SubTask, WorkflowDefinition

logger = get_logger("workflow_engine")


class WorkflowEngine:
    """Engine for executing sequential, conditional, and multi-action workflows."""

    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        agent_manager: Optional[AgentManager] = None,
        skill_manager: Optional[SkillManager] = None,
        security_manager: Optional[SecurityManager] = None,
    ) -> None:
        self.tool_registry = tool_registry or get_tool_registry()
        self.agent_manager = agent_manager or get_agent_manager()
        self.skill_manager = skill_manager or get_skill_manager()
        self.security = security_manager or get_security_manager()
        self._cancelled = False

    def cancel(self) -> None:
        """Signal engine to abort execution after current step."""
        self._cancelled = True

    def _interpolate_value(self, val: Any, variables: Dict[str, Any]) -> Any:
        """Resolve ${var_name} patterns against current workflow variable state."""
        if isinstance(val, str):
            pattern = re.compile(r"\$\{([a-zA-Z0-9_]+)\}")
            # If the entire string is just ${var_name}, return the actual typed object
            match = pattern.fullmatch(val)
            if match:
                var_name = match.group(1)
                return variables.get(var_name, val)

            # If it's embedded within a string
            def replace_fn(m):
                k = m.group(1)
                return str(variables.get(k, m.group(0)))

            return pattern.sub(replace_fn, val)
        elif isinstance(val, dict):
            return {k: self._interpolate_value(v, variables) for k, v in val.items()}
        elif isinstance(val, list):
            return [self._interpolate_value(item, variables) for item in val]
        return val

    def _evaluate_condition(self, condition_str: str, variables: Dict[str, Any]) -> bool:
        """Safely evaluate simple conditions like 'var == val' or 'bool(var)'."""
        if not condition_str or not condition_str.strip():
            return True

        cond = condition_str.strip()
        # Check equality 'var == val'
        if "==" in cond:
            parts = cond.split("==")
            lhs = self._interpolate_value(parts[0].strip(), variables)
            rhs = self._interpolate_value(parts[1].strip().strip("'\""), variables)
            return str(lhs).lower() == str(rhs).lower()
        # Check inequality '!= '
        if "!=" in cond:
            parts = cond.split("!=")
            lhs = self._interpolate_value(parts[0].strip(), variables)
            rhs = self._interpolate_value(parts[1].strip().strip("'\""), variables)
            return str(lhs).lower() != str(rhs).lower()

        # Check variable truthiness '${var}' or 'var'
        val = self._interpolate_value(cond, variables)
        return bool(val)

    def execute(
        self,
        workflow: WorkflowDefinition,
        initial_variables: Optional[Dict[str, Any]] = None,
        user_role: str = "user",
        confirmation_callback: Optional[Callable[..., bool]] = None,
    ) -> WorkflowExecutionResult:
        """Execute all steps in the workflow definition sequentially with conditions and retries."""
        self._cancelled = False
        variables: Dict[str, Any] = dict(workflow.variables)
        if initial_variables:
            variables.update(initial_variables)

        result = WorkflowExecutionResult(
            workflow_id=workflow.id,
            variables=variables,
        )

        steps: List[WorkflowStep] = []
        for s in workflow.steps:
            if isinstance(s, WorkflowStep):
                steps.append(s)
            elif isinstance(s, dict):
                action = StepActionType(s.get("action_type", "tool"))
                steps.append(
                    WorkflowStep(
                        name=s.get("name", "unnamed_step"),
                        action_type=action,
                        target=s.get("target", ""),
                        id=s.get("id"),
                        input_params=s.get("input_params", {}),
                        condition=s.get("condition"),
                        output_variable=s.get("output_variable"),
                        max_retries=s.get("max_retries", 1),
                        continue_on_error=s.get("continue_on_error", False),
                    )
                )

        for step in steps:
            if self._cancelled:
                result.error = "Workflow execution cancelled."
                break

            # Evaluate condition
            if step.condition and not self._evaluate_condition(step.condition, variables):
                result.step_results.append({
                    "step_name": step.name,
                    "status": "SKIPPED",
                    "reason": f"Condition '{step.condition}' evaluated to False",
                })
                continue

            # Execute with retry
            step_success = False
            step_output = None
            step_err = None
            start_t = time.perf_counter()

            for attempt in range(max(1, step.max_retries)):
                try:
                    interpolated_inputs = self._interpolate_value(step.input_params, variables)

                    if step.action_type == StepActionType.TOOL:
                        tool_res = self.tool_registry.execute(
                            step.target,
                            input_data=interpolated_inputs,
                            confirmation_callback=confirmation_callback,
                        )
                        if not tool_res.success:
                            raise ExecutionError(tool_res.error.message if tool_res.error else "Tool execution failed")
                        step_output = tool_res.data
                        step_success = True

                    elif step.action_type == StepActionType.SKILL:
                        step_output = self.skill_manager.execute_skill(
                            step.target,
                            inputs=interpolated_inputs,
                            user_role=user_role,
                            confirmation_callback=confirmation_callback,
                        )
                        step_success = True

                    elif step.action_type == StepActionType.AGENT:
                        subtask = SubTask(
                            name=step.name,
                            assigned_agent=step.target,
                            metadata=interpolated_inputs,
                        )
                        agent_res = self.agent_manager.dispatch_task(
                            step.target,
                            subtask,
                            confirmation_callback=confirmation_callback,
                        )
                        if not agent_res.success:
                            raise ExecutionError(agent_res.error.message if agent_res.error else "Agent execution failed")
                        step_output = agent_res.data
                        step_success = True

                    elif step.action_type == StepActionType.SET_VAR:
                        for k, v in interpolated_inputs.items():
                            variables[k] = v
                        step_output = interpolated_inputs
                        step_success = True

                    elif step.action_type == StepActionType.LOG:
                        logger.info("Workflow log [%s]: %s", step.name, interpolated_inputs)
                        step_output = interpolated_inputs
                        step_success = True

                    break  # Success, exit retry loop

                except Exception as e:
                    step_err = str(e)
                    logger.warning("Step '%s' failed on attempt %d: %s", step.name, attempt + 1, e)

            dur_ms = (time.perf_counter() - start_t) * 1000
            result.steps_executed += 1

            if step_success:
                if step.output_variable:
                    variables[step.output_variable] = step_output
                result.step_results.append({
                    "step_name": step.name,
                    "status": "SUCCESS",
                    "duration_ms": dur_ms,
                    "output": step_output,
                })
            else:
                result.step_results.append({
                    "step_name": step.name,
                    "status": "FAILED",
                    "duration_ms": dur_ms,
                    "error": step_err,
                })
                if not step.continue_on_error:
                    result.error = f"Step '{step.name}' failed: {step_err}"
                    result.variables = variables
                    return result

        result.variables = variables
        result.success = (result.error is None)
        return result
