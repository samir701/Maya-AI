"""ZETTA Persona Manager for Multi-Persona Switching and Behavior Adaptation."""

from typing import Dict, List, Optional
from core.zetta.personas.definitions import DEFAULT_PERSONAS
from core.zetta.utils.errors import ConfigurationError
from core.zetta.utils.logging import get_logger
from shared.types.contracts import PersonaConfig
from shared.types.enums import PersonaType

logger = get_logger("persona_manager")


class PersonaManager:
    """Manages persona profiles, dynamic persona switching, and behavioral parameters."""

    def __init__(self) -> None:
        self._personas: Dict[PersonaType, PersonaConfig] = dict(DEFAULT_PERSONAS)
        self._active_persona_type: PersonaType = PersonaType.DEFAULT

    def get_active_persona(self) -> PersonaConfig:
        """Return the currently active persona configuration."""
        return self._personas[self._active_persona_type]

    def set_active_persona(self, persona_type: PersonaType) -> PersonaConfig:
        """Switch the active persona to the specified type."""
        if persona_type not in self._personas:
            raise ConfigurationError(f"Unknown persona type: '{persona_type}'. Available: {[p.value for p in self._personas]}")
        self._active_persona_type = persona_type
        persona = self._personas[persona_type]
        logger.info(f"Switched active persona to '{persona.name}' ({persona_type.value})")
        return persona

    def switch_persona(self, persona_type: PersonaType) -> PersonaConfig:
        """Alias for set_active_persona."""
        return self.set_active_persona(persona_type)


    def list_personas(self) -> List[PersonaConfig]:
        """List all available personas."""
        return list(self._personas.values())

    def register_persona(self, config: PersonaConfig) -> None:
        """Register or override a persona profile."""
        self._personas[config.persona_type] = config
        logger.info(f"Registered persona '{config.name}' [{config.persona_type.value}]")

    def reset(self) -> None:
        """Reset active persona back to DEFAULT."""
        self._active_persona_type = PersonaType.DEFAULT


_persona_manager_instance: Optional[PersonaManager] = None


def get_persona_manager() -> PersonaManager:
    """Retrieve or initialize singleton PersonaManager."""
    global _persona_manager_instance
    if _persona_manager_instance is None:
        _persona_manager_instance = PersonaManager()
    return _persona_manager_instance
