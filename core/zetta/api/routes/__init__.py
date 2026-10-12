"""API Route definitions for ZETTA Desktop UI."""

from core.zetta.api.routes.system import router as system_router
from core.zetta.api.routes.chat import router as chat_router
from core.zetta.api.routes.agents import router as agents_router
from core.zetta.api.routes.tasks import router as tasks_router
from core.zetta.api.routes.workflows import router as workflows_router
from core.zetta.api.routes.computer import router as computer_router
from core.zetta.api.routes.browser import router as browser_router
from core.zetta.api.routes.vision import router as vision_router
from core.zetta.api.routes.voice import router as voice_router
from core.zetta.api.routes.memory import router as memory_router
from core.zetta.api.routes.skills_plugins import router as skills_plugins_router
from core.zetta.api.routes.confirmations import router as confirmations_router
from core.zetta.api.routes.settings import router as settings_router
from core.zetta.api.routes.documents import router as documents_router

__all__ = [
    "system_router",
    "chat_router",
    "agents_router",
    "tasks_router",
    "workflows_router",
    "computer_router",
    "browser_router",
    "vision_router",
    "voice_router",
    "memory_router",
    "skills_plugins_router",
    "confirmations_router",
    "settings_router",
    "documents_router",
]
