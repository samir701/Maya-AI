"""ZETTA Confirmation Policy."""

from shared.types.enums import PermissionLevel
from core.zetta.config.settings import get_settings


class ConfirmationPolicy:
    """Determines when high-risk operations require explicit human confirmation."""

    def __init__(self, threshold: PermissionLevel = PermissionLevel.HIGH) -> None:
        self.threshold = threshold

    def requires_confirmation(self, level: PermissionLevel) -> bool:
        weights = {
            PermissionLevel.LOW: 1,
            PermissionLevel.MEDIUM: 2,
            PermissionLevel.HIGH: 3,
            PermissionLevel.CRITICAL: 4,
        }
        return weights.get(level, 0) >= weights.get(self.threshold, 3)
