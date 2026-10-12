"""ZETTA Security Permission Checking."""

from shared.types.contracts import Permission
from shared.types.enums import PermissionLevel
from core.zetta.utils.errors.exceptions import AuthorizationError

_PERMISSION_WEIGHTS = {
    PermissionLevel.LOW: 1,
    PermissionLevel.MEDIUM: 2,
    PermissionLevel.HIGH: 3,
    PermissionLevel.CRITICAL: 4,
}


class PermissionChecker:
    """Evaluates component permissions against granted security context levels."""

    def __init__(self, current_level: PermissionLevel = PermissionLevel.MEDIUM) -> None:
        self.current_level = current_level

    def is_granted(self, required_permission: PermissionLevel) -> bool:
        """Check if current granted level satisfies required permission."""
        current_weight = _PERMISSION_WEIGHTS.get(self.current_level, 0)
        required_weight = _PERMISSION_WEIGHTS.get(required_permission, 99)
        return current_weight >= required_weight

    def validate_permission(self, permission: Permission) -> None:
        """Enforce permission check, raising AuthorizationError if denied."""
        if not self.is_granted(permission.level):
            raise AuthorizationError(
                f"Permission denied for '{permission.name}'. Requires level {permission.level.value}, current level is {self.current_level.value}."
            )
