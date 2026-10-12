"""ZETTA Skill Manager for secure execution and lifecycle of skills."""

import importlib.util
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from core.zetta.security.manager import SecurityManager, get_security_manager
from core.zetta.skills.base import BaseSkill
from core.zetta.skills.registry import SkillRegistry, get_skill_registry
from core.zetta.skills.validator import SkillValidator
from core.zetta.utils.errors import ExecutionError, NotFoundError, SecurityError
from core.zetta.utils.logging import get_logger

logger = get_logger("skills_manager")


class SkillManager:
    """Manages skill execution, security verification, and lifecycle."""

    def __init__(
        self,
        registry: Optional[SkillRegistry] = None,
        security_manager: Optional[SecurityManager] = None,
    ) -> None:
        self.registry = registry or get_skill_registry()
        self.security = security_manager or get_security_manager()

    def execute_skill(
        self,
        name: str,
        inputs: Dict[str, Any],
        user_role: str = "user",
        confirmation_callback: Optional[Callable[..., bool]] = None,
    ) -> Dict[str, Any]:
        """Execute a registered skill under security and permission controls."""
        skill = self.registry.get(name)
        if not skill:
            raise NotFoundError(f"Skill '{name}' not found in registry.")

        # Validate inputs
        SkillValidator.validate_execution_inputs(skill, inputs)

        # Enforce security permission check
        has_perm = self.security.check_permission(user_role, skill.required_permission)
        if not has_perm:
            self.security.audit.log_event(
                action="execute_skill",
                actor=user_role,
                resource=f"skill:{name}",
                status="DENIED",
                details={"required_permission": skill.required_permission.value},
            )
            raise SecurityError(
                f"Permission denied for skill '{name}'. Requires {skill.required_permission.value}, actor is {user_role}."
            )

        # Audit start
        self.security.audit.log_event(
            action="execute_skill",
            actor=user_role,
            resource=f"skill:{name}",
            status="STARTED",
            details={"version": skill.metadata.version},
        )

        try:
            output = skill.run(inputs)

            self.security.audit.log_event(
                action="execute_skill",
                actor=user_role,
                resource=f"skill:{name}",
                status="SUCCESS",
            )
            return output

        except Exception as e:
            self.security.audit.log_event(
                action="execute_skill",
                actor=user_role,
                resource=f"skill:{name}",
                status="FAILED",
                details={"error": str(e)},
            )
            logger.error("Skill '%s' execution failed: %s", name, e)
            raise ExecutionError(f"Skill '{name}' execution error: {e}") from e

    def load_from_directory(self, dir_path: Path) -> List[str]:
        """Discover and dynamically load Python skill files from a directory."""
        loaded_names = []
        if not dir_path.exists() or not dir_path.is_dir():
            return loaded_names

        for file_path in dir_path.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"skill_{file_path.stem}", file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, BaseSkill) and attr is not BaseSkill:
                            skill_instance = attr()
                            self.registry.register(skill_instance, override=True)
                            loaded_names.append(skill_instance.name)
            except Exception as e:
                logger.warning("Failed to load skill from %s: %s", file_path, e)

        return loaded_names


_global_skill_manager: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    """Get or initialize global SkillManager singleton."""
    global _global_skill_manager
    if _global_skill_manager is None:
        _global_skill_manager = SkillManager()
    return _global_skill_manager
