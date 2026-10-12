"""ZETTA Interaction Layer Subpackage."""

from core.zetta.interaction.chat import ChatShell
from core.zetta.interaction.commands import CommandProcessor
from core.zetta.interaction.confirmation import ConfirmationInterface
from core.zetta.interaction.formatting import format_banner, format_error, sanitize_text
from core.zetta.interaction.manager import InteractionManager, get_interaction_manager
from core.zetta.interaction.session import Session, SessionManager, get_session_manager

__all__ = [
    "Session",
    "SessionManager",
    "get_session_manager",
    "InteractionManager",
    "get_interaction_manager",
    "ChatShell",
    "CommandProcessor",
    "ConfirmationInterface",
    "format_banner",
    "format_error",
    "sanitize_text",
]
