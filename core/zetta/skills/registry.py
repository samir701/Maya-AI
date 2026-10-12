"""ZETTA Skill Registry for managing reusable skills."""

import threading
from typing import Any, Dict, List, Optional
from core.zetta.skills.base import BaseSkill
from core.zetta.skills.validator import SkillValidator
from core.zetta.utils.errors import RegistrationError
from core.zetta.utils.logging import get_logger
from shared.types.enums import PermissionLevel

logger = get_logger("skills_registry")


class SkillRegistry:
    """Thread-safe registry for registering, discovering, and inspecting skills."""

    def __init__(self) -> None:
        self._skills: Dict[str, BaseSkill] = {}
        self._lock = threading.RLock()

    def register(self, skill: BaseSkill, override: bool = False) -> None:
        """Register a new validated skill into the registry."""
        with self._lock:
            SkillValidator.validate_skill(skill)
            if skill.name in self._skills and not override:
                raise RegistrationError(f"Skill '{skill.name}' is already registered.")
            self._skills[skill.name] = skill
            logger.info("Registered skill: %s v%s", skill.name, skill.metadata.version)

    def unregister(self, name: str) -> bool:
        """Unregister a skill by name."""
        with self._lock:
            if name in self._skills:
                del self._skills[name]
                logger.info("Unregistered skill: %s", name)
                return True
            return False

    def get(self, name: str) -> Optional[BaseSkill]:
        """Retrieve a registered skill by name."""
        with self._lock:
            return self._skills.get(name)

    def list_all(self) -> List[Dict[str, Any]]:
        """List summary metadata for all registered skills."""
        with self._lock:
            return [
                {
                    "name": s.name,
                    "description": s.metadata.description,
                    "version": s.metadata.version,
                    "required_permission": s.required_permission.value,
                    "author": s.metadata.author,
                    "inputs": list(s.metadata.inputs.keys()),
                    "outputs": list(s.metadata.outputs.keys()),
                }
                for s in self._skills.values()
            ]

    def find_by_permission(self, max_permission: PermissionLevel) -> List[BaseSkill]:
        """Filter skills callable within a given permission ceiling."""
        hierarchy = [PermissionLevel.LOW, PermissionLevel.MEDIUM, PermissionLevel.HIGH, PermissionLevel.CRITICAL]
        max_idx = hierarchy.index(max_permission)
        with self._lock:
            return [
                s for s in self._skills.values()
                if hierarchy.index(s.required_permission) <= max_idx
            ]


_global_skill_registry: Optional[SkillRegistry] = None
_registry_lock = threading.Lock()


def get_skill_registry() -> SkillRegistry:
    """Get or initialize the global SkillRegistry singleton."""
    global _global_skill_registry
    with _registry_lock:
        if _global_skill_registry is None:
            _global_skill_registry = SkillRegistry()
        return _global_skill_registry
