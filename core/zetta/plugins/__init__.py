"""ZETTA Plugin Architecture."""

from core.zetta.plugins.base import BasePlugin, PluginMetadata, PluginStatus
from core.zetta.plugins.manager import PluginManager, get_plugin_manager
from core.zetta.plugins.registry import PluginRegistry, get_plugin_registry

__all__ = [
    "BasePlugin",
    "PluginMetadata",
    "PluginStatus",
    "PluginManager",
    "PluginRegistry",
    "get_plugin_manager",
    "get_plugin_registry",
]
