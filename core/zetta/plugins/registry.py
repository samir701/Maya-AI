"""ZETTA Plugin Registry."""

import threading
from typing import Any, Dict, List, Optional
from core.zetta.plugins.base import BasePlugin, PluginStatus
from core.zetta.utils.errors import NotFoundError, RegistrationError
from core.zetta.utils.logging import get_logger

logger = get_logger("plugin_registry")


class PluginRegistry:
    """Thread-safe registry managing plugins and their lifecycle states."""

    def __init__(self) -> None:
        self._plugins: Dict[str, BasePlugin] = {}
        self._lock = threading.RLock()

    def register(self, plugin: BasePlugin, override: bool = False) -> None:
        """Register a plugin instance."""
        with self._lock:
            if not isinstance(plugin, BasePlugin):
                raise TypeError(f"Expected BasePlugin instance, got {type(plugin)}")
            if plugin.name in self._plugins and not override:
                raise RegistrationError(f"Plugin '{plugin.name}' is already registered.")
            self._plugins[plugin.name] = plugin
            logger.info("Registered plugin: %s v%s", plugin.name, plugin.version)

    def unregister(self, name: str) -> bool:
        """Unregister a plugin by name and teardown if enabled."""
        with self._lock:
            plugin = self._plugins.get(name)
            if plugin:
                if plugin.status == PluginStatus.ENABLED:
                    plugin.disable()
                plugin.teardown()
                del self._plugins[name]
                logger.info("Unregistered plugin: %s", name)
                return True
            return False

    def get(self, name: str) -> Optional[BasePlugin]:
        """Get plugin by name."""
        with self._lock:
            return self._plugins.get(name)

    def list_all(self) -> List[Dict[str, Any]]:
        """List summary of all registered plugins."""
        with self._lock:
            return [
                {
                    "name": p.name,
                    "description": p.metadata.description,
                    "version": p.version,
                    "author": p.metadata.author,
                    "status": p.status.value,
                    "required_permission": p.metadata.required_permission.value,
                    "tools_count": len(p.get_tools()),
                    "skills_count": len(p.get_skills()),
                    "agents_count": len(p.get_agents()),
                }
                for p in self._plugins.values()
            ]

    def enable(self, name: str) -> None:
        """Enable a registered plugin."""
        with self._lock:
            plugin = self.get(name)
            if not plugin:
                raise NotFoundError(f"Plugin '{name}' not found.")
            plugin.enable()
            logger.info("Enabled plugin: %s", name)

    def disable(self, name: str) -> None:
        """Disable a registered plugin."""
        with self._lock:
            plugin = self.get(name)
            if not plugin:
                raise NotFoundError(f"Plugin '{name}' not found.")
            plugin.disable()
            logger.info("Disabled plugin: %s", name)

    def health_all(self) -> Dict[str, Any]:
        """Return health status across all plugins."""
        with self._lock:
            return {name: p.health_check() for name, p in self._plugins.items()}


_global_plugin_registry: Optional[PluginRegistry] = None
_registry_lock = threading.Lock()


def get_plugin_registry() -> PluginRegistry:
    """Get or initialize global PluginRegistry singleton."""
    global _global_plugin_registry
    with _registry_lock:
        if _global_plugin_registry is None:
            _global_plugin_registry = PluginRegistry()
        return _global_plugin_registry
