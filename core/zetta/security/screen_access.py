"""ZETTA Screen Access Authorization and Session Manager.

Governs user-authorized screen observation on Linux / Wayland, enforcing:
- DENIED: No screen access permitted.
- ALLOW_ONCE: Single-use snapshot grant (consumed after one capture).
- ALLOW_TASK: Task-scoped authorization (valid only while the specified task is active).
- ALLOW_SESSION: Session-scoped authorization (valid until explicitly revoked).

Crucial Security Guarantees:
1. Screen observation authorization is strictly isolated from Computer Control.
2. Authorization decisions are audited via SecurityManager.audit_logger.
3. No screenshot pixels, OCR contents, or sensitive data are ever logged or persisted.
"""

from enum import Enum
import threading
import time
from typing import Optional, Dict, Any, Callable

from core.zetta.security.manager import get_security_manager
from core.zetta.utils.logging import get_logger

logger = get_logger("screen_access_manager")


class ScreenAccessScope(str, Enum):
    DENIED = "DENIED"
    ALLOW_ONCE = "ALLOW_ONCE"
    ALLOW_TASK = "ALLOW_TASK"
    ALLOW_SESSION = "ALLOW_SESSION"


class ScreenAccessDeniedError(PermissionError):
    """Raised when screen capture or observation is attempted without valid user authorization."""
    pass


class ScreenAccessManager:
    """Thread-safe manager for desktop screen access authorization and lifecycle."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._scope: ScreenAccessScope = ScreenAccessScope.DENIED
        self._active_task_id: Optional[str] = None
        self._once_tokens: int = 0
        self._granted_at: Optional[float] = None
        self._grant_reason: Optional[str] = None
        self._enforce_on_fake: bool = False

    @property
    def current_scope(self) -> ScreenAccessScope:
        with self._lock:
            return self._scope

    def is_authorized(self, task_id: Optional[str] = None) -> bool:
        """Check if screen access is currently authorized without raising an exception."""
        with self._lock:
            if self._scope == ScreenAccessScope.ALLOW_SESSION:
                return True
            if self._scope == ScreenAccessScope.ALLOW_TASK:
                return task_id is not None and task_id == self._active_task_id
            if self._scope == ScreenAccessScope.ALLOW_ONCE:
                return self._once_tokens > 0
            return False

    def require_access(self, task_id: Optional[str] = None, consume: bool = True) -> bool:
        """Validate that screen access is authorized; consume ALLOW_ONCE token if present.

        Raises:
            ScreenAccessDeniedError: If access is currently DENIED or unauthorized.
        """
        with self._lock:
            if self._scope == ScreenAccessScope.ALLOW_SESSION:
                return True

            if self._scope == ScreenAccessScope.ALLOW_TASK:
                if task_id and task_id == self._active_task_id:
                    return True
                raise ScreenAccessDeniedError(
                    f"Screen access denied: task '{task_id}' not authorized for screen access (authorized task: '{self._active_task_id}')."
                )

            if self._scope == ScreenAccessScope.ALLOW_ONCE:
                if self._once_tokens > 0:
                    if consume:
                        self._once_tokens -= 1
                        if self._once_tokens <= 0:
                            self._scope = ScreenAccessScope.DENIED
                            logger.info("ALLOW_ONCE screen access grant consumed.")
                    return True
                self._scope = ScreenAccessScope.DENIED
                raise ScreenAccessDeniedError("Screen access denied: ALLOW_ONCE token expired.")

            raise ScreenAccessDeniedError(
                "Screen access denied: explicit user authorization is required before capturing screen."
            )

    def grant_access(
        self,
        scope: ScreenAccessScope,
        task_id: Optional[str] = None,
        reason: str = "User authorized screen access",
    ) -> None:
        """Explicitly grant screen access under a specific scope."""
        with self._lock:
            self._scope = scope
            self._active_task_id = task_id if scope == ScreenAccessScope.ALLOW_TASK else None
            self._once_tokens = 1 if scope == ScreenAccessScope.ALLOW_ONCE else 0
            self._granted_at = time.time()
            self._grant_reason = reason

            logger.info(f"Screen access granted [Scope: {scope.value}, Task: {task_id}, Reason: {reason}]")

            # Audit event without recording screen data
            try:
                sec = get_security_manager()
                sec.audit.log_event(
                    action="screen_access:grant",
                    actor="user",
                    resource="screen",
                    status="GRANTED",
                    details={"scope": scope.value, "task_id": task_id, "reason": reason},
                )
            except Exception as e:
                logger.debug(f"Audit log error: {e}")

    def revoke_access(self, reason: str = "User revoked screen access") -> None:
        """Immediately revoke all screen access authorizations."""
        with self._lock:
            prev_scope = self._scope.value
            self._scope = ScreenAccessScope.DENIED
            self._active_task_id = None
            self._once_tokens = 0
            self._granted_at = None
            self._grant_reason = None

            logger.info(f"Screen access revoked. Previous scope: {prev_scope}. Reason: {reason}")

            try:
                sec = get_security_manager()
                sec.audit.log_event(
                    action="screen_access:revoke",
                    actor="user",
                    resource="screen",
                    status="REVOKED",
                    details={"previous_scope": prev_scope, "reason": reason},
                )
            except Exception as e:
                logger.debug(f"Audit log error: {e}")

    def request_interactive_authorization(
        self,
        task_id: Optional[str] = None,
        scope: ScreenAccessScope = ScreenAccessScope.ALLOW_SESSION,
        reason: str = "ZETTA requested screen observation for visual understanding",
        confirmation_callback: Optional[Callable[[str], bool]] = None,
    ) -> bool:
        """Request user confirmation for screen access using confirmation subsystem."""
        if self.is_authorized(task_id):
            return True

        prompt = f"ZETTA is requesting permission to access and observe your screen ({reason}). Authorize?"
        confirmed = False

        if confirmation_callback:
            confirmed = confirmation_callback(f"Authorize screen access for: {reason}?")
        else:
            try:
                from core.zetta.interaction.confirmation import ConfirmationInterface
                from shared.types.enums import PermissionLevel
                ci = ConfirmationInterface()
                confirmed = ci.request_confirmation(
                    action=f"screen_access: {reason}",
                    permission_level=PermissionLevel.MEDIUM,
                    details={"scope": scope.value, "task_id": task_id, "reason": reason},
                )
            except Exception as e:
                logger.debug(f"Confirmation interface request failed: {e}")
                confirmed = False

        if confirmed:
            self.grant_access(scope=scope, task_id=task_id, reason=reason)
            return True
        else:
            self.revoke_access(reason="User rejected screen access prompt")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Return public status of screen access authorization without sensitive data."""
        with self._lock:
            return {
                "scope": self._scope.value,
                "is_authorized": self._scope != ScreenAccessScope.DENIED and (
                    self._scope != ScreenAccessScope.ALLOW_ONCE or self._once_tokens > 0
                ),
                "active_task_id": self._active_task_id,
                "once_tokens": self._once_tokens,
                "granted_at": self._granted_at,
                "reason": self._grant_reason,
            }


_screen_access_manager_instance: Optional[ScreenAccessManager] = None
_instance_lock = threading.Lock()


def get_screen_access_manager() -> ScreenAccessManager:
    """Singleton getter for ScreenAccessManager."""
    global _screen_access_manager_instance
    with _instance_lock:
        if _screen_access_manager_instance is None:
            _screen_access_manager_instance = ScreenAccessManager()
        return _screen_access_manager_instance


def reset_screen_access_manager() -> None:
    """Reset screen access manager instance (for test isolation)."""
    global _screen_access_manager_instance
    with _instance_lock:
        if _screen_access_manager_instance is not None:
            _screen_access_manager_instance.revoke_access(reason="Resetting for test isolation")
        _screen_access_manager_instance = ScreenAccessManager()
