"""Unit tests for Skills, Plugins, and Workflow/Macro subsystems (Phase 08.10 - 08.12)."""

import pytest
from typing import Any, Dict
from core.zetta.plugins.base import BasePlugin, PluginMetadata, PluginStatus
from core.zetta.plugins.manager import PluginManager
from core.zetta.plugins.registry import PluginRegistry
from core.zetta.security.manager import SecurityManager
from core.zetta.skills.base import BaseSkill
from core.zetta.skills.manager import SkillManager
from core.zetta.skills.registry import SkillRegistry
from core.zetta.skills.validator import SkillValidator
from core.zetta.tools.base.base_tool import Tool
from core.zetta.tools.registry import ToolRegistry
from core.zetta.utils.errors import SecurityError, ToolError, ValidationError
from core.zetta.workflows.engine import WorkflowEngine
from core.zetta.workflows.models import StepActionType, WorkflowStep
from shared.types.contracts import WorkflowDefinition
from shared.types.enums import PermissionLevel


class UpperCaseSkill(BaseSkill):
    """Test skill that converts input string to uppercase."""
    def __init__(self) -> None:
        super().__init__(
            name="uppercase_skill",
            description="Converts input text to uppercase.",
            version="1.0.0",
            required_permission=PermissionLevel.LOW,
            inputs_schema={"text": str},
            outputs_schema={"result": str},
        )

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"result": inputs["text"].upper()}


class HighPermSkill(BaseSkill):
    """Test skill requiring HIGH permission."""
    def __init__(self) -> None:
        super().__init__(
            name="high_perm_skill",
            description="Requires high permissions.",
            version="1.0.0",
            required_permission=PermissionLevel.HIGH,
            inputs_schema={"value": int},
        )

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"doubled": inputs["value"] * 2}


class DummyEchoTool(Tool):
    """Test tool provided by a plugin."""
    name = "plugin_echo_tool"
    description = "Echoes input text."
    required_permission = PermissionLevel.LOW
    category = "testing"

    def run(self, input_data: Dict[str, Any]) -> Any:
        return {"echo": input_data.get("msg", "")}


class SamplePlugin(BasePlugin):
    """Test plugin contributing a tool and skill."""
    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="sample_test_plugin",
                description="A test plugin for verification.",
                version="1.0.0",
                required_permission=PermissionLevel.LOW,
            )
        )
        self.enabled_called = False

    def on_enable(self) -> None:
        self.enabled_called = True

    def get_tools(self):
        return [DummyEchoTool()]

    def get_skills(self):
        return [UpperCaseSkill()]


class TestSkillsSubsystem:
    """Tests for Milestone 08.10 Skills System."""

    def test_skill_validation_and_registration(self):
        skill = UpperCaseSkill()
        assert SkillValidator.validate_skill(skill) is True

        registry = SkillRegistry()
        registry.register(skill)
        assert registry.get("uppercase_skill") is not None
        assert len(registry.list_all()) == 1

        with pytest.raises(ValidationError):
            # Invalid inputs (missing 'text')
            SkillValidator.validate_execution_inputs(skill, {})

    def test_skill_execution_and_permission_enforcement(self):
        skill_reg = SkillRegistry()
        skill = UpperCaseSkill()
        high_skill = HighPermSkill()
        skill_reg.register(skill)
        skill_reg.register(high_skill)

        sec = SecurityManager()
        manager = SkillManager(registry=skill_reg, security_manager=sec)

        # Standard execution succeeds
        out = manager.execute_skill("uppercase_skill", {"text": "hello world"}, user_role="user")
        assert out == {"result": "HELLO WORLD"}

        # High perm skill should fail for 'guest'
        with pytest.raises(SecurityError):
            manager.execute_skill("high_perm_skill", {"value": 5}, user_role="guest")

        # High perm skill succeeds for 'admin'
        admin_out = manager.execute_skill("high_perm_skill", {"value": 5}, user_role="admin")
        assert admin_out == {"doubled": 10}


class TestPluginArchitecture:
    """Tests for Milestone 08.11 Plugin Architecture."""

    def test_plugin_lifecycle_and_mounting(self):
        plugin = SamplePlugin()
        p_reg = PluginRegistry()
        p_reg.register(plugin)

        t_reg = ToolRegistry()
        s_reg = SkillRegistry()
        sec = SecurityManager()
        p_mgr = PluginManager(
            registry=p_reg,
            tool_registry=t_reg,
            skill_registry=s_reg,
            security_manager=sec,
        )

        assert plugin.status == PluginStatus.LOADED

        # Enable plugin
        p_mgr.enable_plugin("sample_test_plugin")
        assert plugin.status == PluginStatus.ENABLED
        assert plugin.enabled_called is True
        assert t_reg.get("plugin_echo_tool") is not None
        assert s_reg.get("uppercase_skill") is not None

        # Health check
        health = p_reg.health_all()
        assert health["sample_test_plugin"]["healthy"] is True

        # Disable plugin
        p_mgr.disable_plugin("sample_test_plugin")
        assert plugin.status == PluginStatus.DISABLED
        with pytest.raises(ToolError):
            t_reg.get("plugin_echo_tool")
        assert s_reg.get("uppercase_skill") is None



class TestWorkflowEngine:
    """Tests for Milestone 08.12 Macro / Workflow System."""

    def test_sequential_workflow_execution(self):
        t_reg = ToolRegistry()
        t_reg.register(DummyEchoTool())

        s_reg = SkillRegistry()
        s_reg.register(UpperCaseSkill())
        s_mgr = SkillManager(registry=s_reg)

        engine = WorkflowEngine(
            tool_registry=t_reg,
            skill_manager=s_mgr,
        )

        workflow = WorkflowDefinition(
            name="Test Sequential Workflow",
            steps=[
                WorkflowStep(
                    name="Initialize Variables",
                    action_type=StepActionType.SET_VAR,
                    target="",
                    input_params={"greeting": "hello zetta"},
                ),
                WorkflowStep(
                    name="Transform to Uppercase",
                    action_type=StepActionType.SKILL,
                    target="uppercase_skill",
                    input_params={"text": "${greeting}"},
                    output_variable="loud_greeting",
                ),
                WorkflowStep(
                    name="Echo Output",
                    action_type=StepActionType.TOOL,
                    target="plugin_echo_tool",
                    input_params={"msg": "${loud_greeting}"},
                    output_variable="final_echo",
                ),
            ]
        )

        res = engine.execute(workflow)
        assert res.success is True
        assert res.steps_executed == 3
        assert res.variables["loud_greeting"] == {"result": "HELLO ZETTA"}
        assert res.variables["final_echo"] == {"echo": {"result": "HELLO ZETTA"}}

    def test_workflow_conditional_skipping(self):
        engine = WorkflowEngine()

        workflow = WorkflowDefinition(
            name="Conditional Workflow",
            variables={"mode": "skip"},
            steps=[
                WorkflowStep(
                    name="Step 1 - Should execute",
                    action_type=StepActionType.SET_VAR,
                    target="",
                    input_params={"ran_step_1": True},
                ),
                WorkflowStep(
                    name="Step 2 - Should skip",
                    action_type=StepActionType.SET_VAR,
                    target="",
                    condition="mode == run",
                    input_params={"ran_step_2": True},
                ),
            ]
        )

        res = engine.execute(workflow)
        assert res.success is True
        assert res.variables.get("ran_step_1") is True
        assert "ran_step_2" not in res.variables
        assert res.step_results[1]["status"] == "SKIPPED"
