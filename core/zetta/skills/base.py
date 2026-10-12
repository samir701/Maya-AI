"""ZETTA Base Skill Definition and Interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from core.zetta.utils.errors import ValidationError
from shared.types.contracts import SkillMetadata
from shared.types.enums import PermissionLevel


class BaseSkill(ABC):
    """Abstract base class for all extensible skills in ZETTA."""

    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        required_permission: PermissionLevel = PermissionLevel.LOW,
        inputs_schema: Dict[str, Any] = None,
        outputs_schema: Dict[str, Any] = None,
    ) -> None:
        self.metadata = SkillMetadata(
            name=name,
            description=description,
            version=version,
            required_permission=required_permission,
            inputs=inputs_schema or {},
            outputs=outputs_schema or {},
        )

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def required_permission(self) -> PermissionLevel:
        return self.metadata.required_permission

    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate provided inputs against declared schema."""
        for field, req_type in self.metadata.inputs.items():
            if field not in inputs:
                raise ValidationError(f"Missing required skill input field '{field}' for skill '{self.name}'.")

    @abstractmethod
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Concrete skill logic implemented by subclasses."""
        raise NotImplementedError
