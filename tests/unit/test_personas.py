"""Unit tests for Milestone 08.9 Persona System."""

import pytest
from core.zetta.personas import PersonaManager, get_persona_manager
from core.zetta.utils.errors import ConfigurationError
from shared.types.contracts import PersonaConfig
from shared.types.enums import PermissionLevel, PersonaType


class TestPersonas:
    """Test suite for PersonaManager and persona switching."""

    def setup_method(self):
        self.manager = PersonaManager()

    def test_default_persona(self):
        active = self.manager.get_active_persona()
        assert active.persona_type == PersonaType.DEFAULT
        assert "ZETTA Standard" in active.name
        assert len(active.behavior_rules) >= 2

    def test_list_all_standard_personas(self):
        personas = self.manager.list_personas()
        assert len(personas) == 3
        types = {p.persona_type for p in personas}
        assert types == {PersonaType.DEFAULT, PersonaType.PROFESSIONAL, PersonaType.CREATIVE}

    def test_switch_to_professional(self):
        prof = self.manager.set_active_persona(PersonaType.PROFESSIONAL)
        assert prof.persona_type == PersonaType.PROFESSIONAL
        assert "formal" in prof.communication_style
        assert self.manager.get_active_persona() == prof

    def test_switch_to_creative(self):
        creative = self.manager.set_active_persona(PersonaType.CREATIVE)
        assert creative.persona_type == PersonaType.CREATIVE
        assert creative.voice_profile["voice"] == "af_bella"
        assert self.manager.get_active_persona() == creative

    def test_custom_persona_registration(self):
        custom = PersonaConfig(
            persona_type=PersonaType.DEFAULT,
            name="ZETTA Custom",
            behavior_rules=["Rule 1"],
            max_permission=PermissionLevel.MEDIUM,
        )
        self.manager.register_persona(custom)
        assert self.manager.get_active_persona().name == "ZETTA Custom"
