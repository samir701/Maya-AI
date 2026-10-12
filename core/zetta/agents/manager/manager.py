"""ZETTA High-Level Agent Manager Facade."""

from typing import Any, Dict, List, Optional
from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.agents.manager.registry import AgentRegistry
from core.zetta.events import get_event_bus
from core.zetta.security import get_security_manager
from core.zetta.utils.errors import AgentError
from core.zetta.utils.logging import get_logger
from shared.types.contracts import AgentContext, AgentResult, SubTask
from shared.types.enums import AgentCapability

logger = get_logger("agent_manager")


class AgentManager:
    """Central manager orchestrating agent lifecycle, lookup, task dispatch, and status inspection."""

    def __init__(self, registry: Optional[AgentRegistry] = None) -> None:
        self.registry = registry or AgentRegistry()
        self.security_manager = get_security_manager()
        self.event_bus = get_event_bus()

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the manager's registry."""
        self.registry.register(agent)

    def get_agent(self, name_or_id: str) -> BaseAgent:
        """Get an agent by name or ID."""
        return self.registry.get(name_or_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents and their current status."""
        return self.registry.list_agents()

    def dispatch_task(
        self,
        agent_name_or_id: str,
        task: SubTask,
        context: Optional[AgentContext] = None,
    ) -> AgentResult:
        """Dispatch a task directly to a specified agent."""
        agent = self.get_agent(agent_name_or_id)
        logger.info(f"Dispatching task '{task.name}' [ID: {task.id}] to agent '{agent.name}'")
        return agent.execute(task=task, context=context)

    def pause_agent(self, agent_name_or_id: str) -> bool:
        """Pause a running agent."""
        agent = self.get_agent(agent_name_or_id)
        return agent.pause()

    def resume_agent(self, agent_name_or_id: str) -> bool:
        """Resume a paused agent."""
        agent = self.get_agent(agent_name_or_id)
        return agent.resume()

    def cancel_agent(self, agent_name_or_id: str) -> bool:
        """Cancel a running agent."""
        agent = self.get_agent(agent_name_or_id)
        return agent.cancel()

    def reset_agent(self, agent_name_or_id: str) -> None:
        """Reset an agent to READY state."""
        agent = self.get_agent(agent_name_or_id)
        agent.reset()

    def find_agent_for_capability(self, capability: AgentCapability) -> Optional[BaseAgent]:
        """Find the best available agent for a capability."""
        agents = self.registry.find_by_capability(capability)
        return agents[0] if agents else None

    def status(self) -> Dict[str, Any]:
        """Return aggregate status of the agent subsystem."""
        agents = self.registry.list_agents()
        return {
            "total_agents": len(agents),
            "agents": agents,
            "status": "OK",
        }


_agent_manager_instance: Optional[AgentManager] = None


def get_agent_manager(registry: Optional[AgentRegistry] = None) -> AgentManager:
    """Retrieve or create singleton AgentManager instance."""
    global _agent_manager_instance
    if _agent_manager_instance is None:
        _agent_manager_instance = AgentManager(registry=registry)
    elif registry is not None:
        _agent_manager_instance.registry = registry
    return _agent_manager_instance



def reset_agent_manager() -> None:
    """Reset the singleton instance (primarily for isolated test fixtures)."""
    global _agent_manager_instance
    _agent_manager_instance = None
