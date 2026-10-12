"""ZETTA Plugin Architecture Base Definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from shared.types.enums import PermissionLevel


class PluginStatus(str, Enum):
    """Lifecycle states of a plugin."""
    LOADED = "LOADED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


@dataclass
class PluginMetadata:
    """Descriptor metadata for a ZETTA plugin."""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "ZETTA"
    required_permission: PermissionLevel = PermissionLevel.LOW
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)


class BasePlugin(ABC):
    """Abstract base class for all ZETTA plugins."""

    def __init__(self, metadata: PluginMetadata) -> None:
        self.metadata = metadata
        self.status = PluginStatus.LOADED
        self.config: Dict[str, Any] = {}
        self.error_message: Optional[str] = None

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def version(self) -> str:
        return self.metadata.version

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize plugin configuration and state."""
        self.config = config or {}

    def enable(self) -> None:
        """Activate the plugin."""
        self.on_enable()
        self.status = PluginStatus.ENABLED

    def disable(self) -> None:
        """Deactivate the plugin."""
        self.on_disable()
        self.status = PluginStatus.DISABLED

    def teardown(self) -> None:
        """Release any acquired resources."""
        self.disable()

    def on_enable(self) -> None:
        """Subclasses override to perform custom activation hooks."""
        pass

    def on_disable(self) -> None:
        """Subclasses override to perform cleanup."""
        pass

    def health_check(self) -> Dict[str, Any]:
        """Inspect health status of the plugin."""
        return {
            "name": self.name,
            "status": self.status.value,
            "healthy": self.status != PluginStatus.ERROR,
            "error": self.error_message,
        }

    def get_tools(self) -> List[Any]:
        """Optional list of tools contributed by this plugin."""
        return []

    def get_skills(self) -> List[Any]:
        """Optional list of skills contributed by this plugin."""
        return []

    def get_agents(self) -> List[Any]:
        """Optional list of agents contributed by this plugin."""
        return []
