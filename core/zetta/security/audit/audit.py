"""ZETTA Security Audit Logging."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from core.zetta.utils.logging import get_logger

logger = get_logger("security_audit")


class AuditLogger:
    """Records security-critical actions for compliance and verification."""

    def log_event(
        self,
        action: str,
        actor: str,
        resource: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "actor": actor,
            "resource": resource,
            "status": status,
            "details": details or {},
        }
        logger.info(f"AUDIT [{status}] Action: '{action}' by '{actor}' on '{resource}'")
        return record
