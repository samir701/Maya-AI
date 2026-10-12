"""ZETTA Specialized Agent Fleet."""

from core.zetta.agents.fleet.general import GeneralAssistantAgent
from core.zetta.agents.fleet.browser_agent import BrowserAgent
from core.zetta.agents.fleet.vision_agent import VisionAgent
from core.zetta.agents.fleet.voice_agent import VoiceAgent
from core.zetta.agents.fleet.research_agent import ResearchAgent
from core.zetta.agents.fleet.document_agent import DocumentAgent
from core.zetta.agents.fleet.hermes import HermesAutonomousAgent, Checkpoint
from core.zetta.agents.fleet.coding_agent import CodingAgent
from core.zetta.agents.fleet.computer_agent import UnifiedComputerAgent
from core.zetta.accessibility.agent import AccessibilityAgent
from core.zetta.agents.manager.manager import get_agent_manager
from core.zetta.agents.manager.registry import AgentRegistry

__all__ = [
    "GeneralAssistantAgent",
    "BrowserAgent",
    "VisionAgent",
    "VoiceAgent",
    "ResearchAgent",
    "DocumentAgent",
    "HermesAutonomousAgent",
    "CodingAgent",
    "UnifiedComputerAgent",
    "AccessibilityAgent",
    "Checkpoint",
    "register_default_fleet",
]


def register_default_fleet(registry: AgentRegistry = None) -> AgentRegistry:
    """Register the standard agent fleet into the target registry (defaults to singleton manager's registry)."""
    if registry is None:
        registry = get_agent_manager().registry

    fleet = [
        GeneralAssistantAgent(),
        BrowserAgent(use_fake=True),
        VisionAgent(use_fake=True),
        VoiceAgent(use_fake=True),
        ResearchAgent(),
        DocumentAgent(),
    ]
    for agent in fleet:
        if not registry.has(agent.name):
            registry.register(agent)

    return registry
