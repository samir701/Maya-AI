"""ZETTA Accessibility Package."""

from core.zetta.accessibility.capabilities import AccessibilityCapabilityType, AccessibilityActionResult
from core.zetta.accessibility.manager import AccessibilityManager, get_accessibility_manager
from core.zetta.accessibility.agent import AccessibilityAgent

__all__ = [
    "AccessibilityCapabilityType",
    "AccessibilityActionResult",
    "AccessibilityManager",
    "get_accessibility_manager",
    "AccessibilityAgent",
]
