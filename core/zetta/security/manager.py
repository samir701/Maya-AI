"""Central ZETTA Security Manager."""

from core.zetta.config.settings import get_settings
from core.zetta.security.audit.audit import AuditLogger
from core.zetta.security.confirmation.confirmation import ConfirmationPolicy
from core.zetta.security.permissions.permissions import PermissionChecker
from core.zetta.security.sandbox.sandbox import SandboxPolicy
from core.zetta.security.secrets.secrets import SecretManager
from shared.types.enums import PermissionLevel


class SecurityManager:
    """Consolidated security service for authentication, authorization, audit, and sandboxing."""

    def __init__(self, current_level: PermissionLevel = PermissionLevel.MEDIUM) -> None:
        settings = get_settings()
        threshold = getattr(PermissionLevel, settings.security.confirmation_threshold, PermissionLevel.HIGH)

        self.permission_checker = PermissionChecker(current_level=current_level)
        self.confirmation_policy = ConfirmationPolicy(threshold=threshold)
        self.audit_logger = AuditLogger()
        self.sandbox_policy = SandboxPolicy(enabled=settings.security.sandbox_enabled)
        self.secret_manager = SecretManager()

    @property
    def confirmation(self) -> ConfirmationPolicy:
        return self.confirmation_policy

    @property
    def audit(self) -> AuditLogger:
        return self.audit_logger

    def check_permission(self, user_role: str, required_permission: PermissionLevel) -> bool:
        """Evaluate if user_role satisfies required permission level."""
        role_levels = {
            "guest": PermissionLevel.LOW,
            "user": PermissionLevel.HIGH,
            "operator": PermissionLevel.HIGH,
            "admin": PermissionLevel.CRITICAL,
            "system": PermissionLevel.CRITICAL,
        }
        if user_role.lower() not in role_levels:
            return False
        user_max = role_levels[user_role.lower()]
        weights = {
            PermissionLevel.LOW: 1,
            PermissionLevel.MEDIUM: 2,
            PermissionLevel.HIGH: 3,
            PermissionLevel.CRITICAL: 4,
        }
        return weights.get(user_max, 1) >= weights.get(required_permission, 99)

    def check_tool_permission(self, required_permission: PermissionLevel) -> bool:
        return self.permission_checker.is_granted(required_permission)

    def requires_user_confirmation(self, required_permission: PermissionLevel) -> bool:
        return self.confirmation_policy.requires_confirmation(required_permission)



_security_manager_instance: SecurityManager = SecurityManager()


def get_security_manager() -> SecurityManager:
    return _security_manager_instance
