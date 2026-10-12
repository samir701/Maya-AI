"""ZETTA Workflow and Macro Models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from shared.types.contracts import WorkflowDefinition


class StepActionType(str, Enum):
    """Action types executable within a workflow step."""
    TOOL = "tool"
    AGENT = "agent"
    SKILL = "skill"
    LOG = "log"
    SET_VAR = "set_var"


@dataclass
class WorkflowStep:
    """Individual executable step in a macro/workflow."""
    name: str
    action_type: StepActionType
    target: str
    id: str = field(default_factory=lambda: str(uuid4()))
    input_params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None
    output_variable: Optional[str] = None
    max_retries: int = 1
    continue_on_error: bool = False


@dataclass
class WorkflowExecutionResult:
    """Outcome of running a workflow."""
    workflow_id: str
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    success: bool = False
    variables: Dict[str, Any] = field(default_factory=dict)
    steps_executed: int = 0
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
