"""ZETTA Communication Manager for email, chat messaging, and expense tracking."""

from typing import Any, Callable, Dict, List, Optional
from core.zetta.comms.email import BaseEmailProvider, EmailMessage, FakeEmailProvider
from core.zetta.comms.expenses import BaseExpenseProvider, ExpenseItem, FakeExpenseProvider
from core.zetta.comms.messaging import BaseMessagingProvider, FakeMessagingProvider, InstantMessage
from core.zetta.security.manager import SecurityManager, get_security_manager
from core.zetta.utils.errors import SecurityError
from core.zetta.utils.logging import get_logger
from shared.types.enums import PermissionLevel

logger = get_logger("communication_manager")


class CommunicationManager:
    """Consolidated communication manager providing security-gated email, messaging, and expenses."""

    def __init__(
        self,
        email_provider: Optional[BaseEmailProvider] = None,
        messaging_provider: Optional[BaseMessagingProvider] = None,
        expense_provider: Optional[BaseExpenseProvider] = None,
        security_manager: Optional[SecurityManager] = None,
    ) -> None:
        self.email = email_provider or FakeEmailProvider()
        self.messaging = messaging_provider or FakeMessagingProvider()
        self.expenses = expense_provider or FakeExpenseProvider()
        self.security = security_manager or get_security_manager()

    def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        user_role: str = "user",
        confirmation_callback: Optional[Callable[[str], bool]] = None,
    ) -> Dict[str, Any]:
        """Send an email with security validation and optional user confirmation."""
        req_perm = PermissionLevel.HIGH
        if not self.security.check_permission(user_role, req_perm):
            self.security.audit.log_event(
                action="send_email",
                actor=user_role,
                resource="email_service",
                status="DENIED",
                details={"to": to, "subject": subject},
            )
            raise SecurityError(f"Permission denied to send email. Requires {req_perm.value}.")

        if self.security.requires_user_confirmation(req_perm):
            confirmed = False
            if confirmation_callback:
                confirmed = confirmation_callback(f"Confirm sending email to {to} with subject '{subject}'?")
            if not confirmed:
                self.security.audit.log_event(
                    action="send_email",
                    actor=user_role,
                    resource="email_service",
                    status="REJECTED_USER",
                )
                raise SecurityError("Send email action rejected by user confirmation policy.")

        msg = EmailMessage(to=to, subject=subject, body=body)
        res = self.email.send_email(msg)
        self.security.audit.log_event(
            action="send_email",
            actor=user_role,
            resource="email_service",
            status="SUCCESS",
            details={"to": to, "subject": subject},
        )
        return res

    def send_message(
        self,
        recipient: str,
        content: str,
        channel: str = "whatsapp",
        user_role: str = "user",
        confirmation_callback: Optional[Callable[[str], bool]] = None,
    ) -> Dict[str, Any]:
        """Send a chat/instant message with security checks."""
        req_perm = PermissionLevel.HIGH
        if not self.security.check_permission(user_role, req_perm):
            self.security.audit.log_event(
                action=f"send_message:{channel}",
                actor=user_role,
                resource="messaging_service",
                status="DENIED",
            )
            raise SecurityError(f"Permission denied to send {channel} message. Requires {req_perm.value}.")

        if self.security.requires_user_confirmation(req_perm):
            confirmed = False
            if confirmation_callback:
                confirmed = confirmation_callback(f"Confirm sending {channel} message to {recipient}?")
            if not confirmed:
                self.security.audit.log_event(
                    action=f"send_message:{channel}",
                    actor=user_role,
                    resource="messaging_service",
                    status="REJECTED_USER",
                )
                raise SecurityError(f"{channel} message rejected by user confirmation policy.")

        msg = InstantMessage(recipient=recipient, content=content, channel=channel)
        res = self.messaging.send_message(msg)
        self.security.audit.log_event(
            action=f"send_message:{channel}",
            actor=user_role,
            resource="messaging_service",
            status="SUCCESS",
            details={"recipient": recipient},
        )
        return res

    def record_expense(
        self,
        category: str,
        amount: float,
        merchant: str = "General Vendor",
        notes: str = "",
        user_role: str = "user",
    ) -> Dict[str, Any]:
        """Record an expense entry."""
        req_perm = PermissionLevel.MEDIUM
        if not self.security.check_permission(user_role, req_perm):
            raise SecurityError(f"Permission denied to record expense. Requires {req_perm.value}.")

        item = ExpenseItem(category=category, amount=amount, merchant=merchant, notes=notes)
        res = self.expenses.record_expense(item)
        self.security.audit.log_event(
            action="record_expense",
            actor=user_role,
            resource="expense_service",
            status="SUCCESS",
            details={"amount": amount, "category": category},
        )
        return res


_global_communication_manager: Optional[CommunicationManager] = None


def get_communication_manager() -> CommunicationManager:
    """Get or initialize global CommunicationManager singleton."""
    global _global_communication_manager
    if _global_communication_manager is None:
        _global_communication_manager = CommunicationManager()
    return _global_communication_manager
