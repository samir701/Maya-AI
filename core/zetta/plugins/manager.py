"""ZETTA Plugin Manager for secure plugin lifecycle and subsystem registration."""

import importlib.util
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from core.zetta.agents.manager.registry import AgentRegistry, get_agent_registry
from core.zetta.plugins.base import BasePlugin, PluginStatus
from core.zetta.plugins.registry import PluginRegistry, get_plugin_registry
from core.zetta.security.manager import SecurityManager, get_security_manager
from core.zetta.skills.registry import SkillRegistry, get_skill_registry
from core.zetta.tools.registry import ToolRegistry, get_tool_registry
from core.zetta.utils.errors import NotFoundError, SecurityError
from core.zetta.utils.logging import get_logger

logger = get_logger("plugin_manager")


class PluginManager:
    """Orchestrates plugin lifecycle, discovery, and capability mounting."""

    def __init__(
        self,
        registry: Optional[PluginRegistry] = None,
        tool_registry: Optional[ToolRegistry] = None,
        skill_registry: Optional[SkillRegistry] = None,
        agent_registry: Optional[AgentRegistry] = None,
        security_manager: Optional[SecurityManager] = None,
    ) -> None:
        self.registry = registry or get_plugin_registry()
        self.tool_registry = tool_registry or get_tool_registry()
        self.skill_registry = skill_registry or get_skill_registry()
        self.agent_registry = agent_registry or get_agent_registry()
        self.security = security_manager or get_security_manager()

    def enable_plugin(self, name: str, user_role: str = "admin") -> None:
        """Enable a plugin and mount its tools, skills, and agents."""
        plugin = self.registry.get(name)
        if not plugin:
            raise NotFoundError(f"Plugin '{name}' not found.")

        # Security check
        has_perm = self.security.check_permission(user_role, plugin.metadata.required_permission)
        if not has_perm:
            self.security.audit.log_event(
                action="enable_plugin",
                actor=user_role,
                resource=f"plugin:{name}",
                status="DENIED",
            )
            raise SecurityError(
                f"Permission denied to enable plugin '{name}'. Requires {plugin.metadata.required_permission.value}."
            )

        # Enable plugin
        plugin.enable()

        # Mount tools
        for tool in plugin.get_tools():
            try:
                self.tool_registry.register(tool)
            except Exception as e:
                logger.warning("Plugin '%s' failed to register tool '%s': %s", name, getattr(tool, "name", "unknown"), e)

        # Mount skills
        for skill in plugin.get_skills():
            try:
                self.skill_registry.register(skill, override=True)
            except Exception as e:
                logger.warning("Plugin '%s' failed to register skill '%s': %s", name, getattr(skill, "name", "unknown"), e)

        # Mount agents
        for agent in plugin.get_agents():
            try:
                self.agent_registry.register(agent, override=True)
            except Exception as e:
                logger.warning("Plugin '%s' failed to register agent '%s': %s", name, getattr(agent, "name", "unknown"), e)

        self.security.audit.log_event(
            action="enable_plugin",
            actor=user_role,
            resource=f"plugin:{name}",
            status="SUCCESS",
        )
        logger.info("Plugin '%s' enabled and capabilities mounted.", name)

    def disable_plugin(self, name: str, user_role: str = "admin") -> None:
        """Disable a plugin and unmount its tools, skills, and agents."""
        plugin = self.registry.get(name)
        if not plugin:
            raise NotFoundError(f"Plugin '{name}' not found.")

        plugin.disable()

        # Unmount tools
        for tool in plugin.get_tools():
            tool_name = getattr(tool, "name", None)
            if tool_name:
                self.tool_registry.unregister(tool_name)

        # Unmount skills
        for skill in plugin.get_skills():
            skill_name = getattr(skill, "name", None)
            if skill_name:
                self.skill_registry.unregister(skill_name)

        # Unmount agents
        for agent in plugin.get_agents():
            agent_id = getattr(agent, "agent_id", None)
            if agent_id:
                self.agent_registry.unregister(agent_id)

        self.security.audit.log_event(
            action="disable_plugin",
            actor=user_role,
            resource=f"plugin:{name}",
            status="SUCCESS",
        )
        logger.info("Plugin '%s' disabled and capabilities unmounted.", name)

    def discover_and_register(self, dir_path: Path) -> List[str]:
        """Scan directory and register all plugin classes found."""
        registered = []
        if not dir_path.exists() or not dir_path.is_dir():
            return registered

        for file_path in dir_path.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"plugin_{file_path.stem}", file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                            instance = attr()
                            self.registry.register(instance, override=True)
                            registered.append(instance.name)
            except Exception as e:
                logger.warning("Failed discovering plugin from %s: %s", file_path, e)

        return registered


_global_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get or initialize global PluginManager singleton."""
    global _global_plugin_manager
    if _global_plugin_manager is None:
        _global_plugin_manager = PluginManager()
    return _global_plugin_manager
