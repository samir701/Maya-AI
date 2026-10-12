"""ZETTA Skill Validator for integrity, schema, and security check."""

from typing import Any, Dict
from core.zetta.skills.base import BaseSkill
from core.zetta.utils.errors import ValidationError


class SkillValidator:
    """Validates skill definitions, required metadata fields, and input/output contracts."""

    @staticmethod
    def validate_skill(skill: BaseSkill) -> bool:
        """Verify that a skill satisfies basic structural and metadata requirements."""
        if not isinstance(skill, BaseSkill):
            raise ValidationError(f"Expected BaseSkill instance, got {type(skill)}")

        if not skill.name or not skill.metadata.description:
            raise ValidationError(f"Skill '{skill.name}' must provide both a name and description.")

        if not skill.metadata.version:
            raise ValidationError(f"Skill '{skill.name}' must specify a semver version.")

        return True

    @staticmethod
    def validate_execution_inputs(skill: BaseSkill, inputs: Dict[str, Any]) -> None:
        """Validate input dictionary against skill metadata inputs."""
        skill.validate_inputs(inputs)
