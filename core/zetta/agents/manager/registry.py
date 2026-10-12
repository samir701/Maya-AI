"""ZETTA Agent Registry for discovery, lookup, and capability indexing."""

from typing import Any, Dict, List, Optional
from core.zetta.agents.base.base_agent import BaseAgent
from core.zetta.utils.errors import AgentError
from core.zetta.utils.logging import get_logger
from shared.types.enums import AgentCapability, PermissionLevel

logger = get_logger("agent_registry")


class AgentRegistry:
    """Central registry maintaining active agent instances with capability and permission indexing."""

    def __init__(self) -> None:
        self._agents_by_id: Dict[str, BaseAgent] = {}
        self._agents_by_name: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance."""
        if not isinstance(agent, BaseAgent):
            raise AgentError(f"Cannot register agent: expected BaseAgent instance, got {type(agent)}.")

        existing_by_id = self._agents_by_id.get(agent.agent_id)
        existing_by_name = self._agents_by_name.get(agent.name.lower())
        if (existing_by_id and type(existing_by_id) is type(agent)) or (existing_by_name and type(existing_by_name) is type(agent)):
            logger.debug(f"Agent '{agent.name}' already registered; updating registration idempotently.")
            self._agents_by_id[agent.agent_id] = agent
            self._agents_by_name[agent.name.lower()] = agent
            return

        if agent.agent_id in self._agents_by_id:
            logger.warning(f"Overwriting existing agent registration for ID '{agent.agent_id}'")

        self._agents_by_id[agent.agent_id] = agent
        self._agents_by_name[agent.name.lower()] = agent
        logger.info(f"Registered agent '{agent.name}' [ID: {agent.agent_id}, Permission: {agent.required_permission.value}]")

    def unregister(self, name_or_id: str) -> bool:
        """Unregister an agent by ID or name."""
        agent = self._agents_by_id.pop(name_or_id, None)
        if not agent:
            agent = self._agents_by_name.pop(name_or_id.lower(), None)
            if agent:
                self._agents_by_id.pop(agent.agent_id, None)
        else:
            self._agents_by_name.pop(agent.name.lower(), None)

        if agent:
            logger.info(f"Unregistered agent '{agent.name}' [ID: {agent.agent_id}]")
            return True
        return False

    def get(self, name_or_id: str) -> BaseAgent:
        """Retrieve an agent by ID or case-insensitive name."""
        if name_or_id in self._agents_by_id:
            return self._agents_by_id[name_or_id]
        lower_name = name_or_id.lower()
        if lower_name in self._agents_by_name:
            return self._agents_by_name[lower_name]
        raise AgentError(f"Agent '{name_or_id}' is not registered in AgentRegistry.")

    def has(self, name_or_id: str) -> bool:
        """Return True if an agent is registered."""
        return (name_or_id in self._agents_by_id) or (name_or_id.lower() in self._agents_by_name)

    def list_agents(self) -> List[Dict[str, Any]]:
        """Return metadata dictionaries for all registered agents."""
        return [agent.to_dict() for agent in self._agents_by_id.values()]

    def find_by_capability(self, capability: AgentCapability) -> List[BaseAgent]:
        """Find all registered agents supporting a specified capability."""
        return [
            agent for agent in self._agents_by_id.values()
            if capability in agent.capabilities
        ]

    def find_by_permission(self, max_permission: PermissionLevel) -> List[BaseAgent]:
        """Find agents whose required permission does not exceed max_permission."""
        permission_order = {
            PermissionLevel.LOW: 1,
            PermissionLevel.MEDIUM: 2,
            PermissionLevel.HIGH: 3,
            PermissionLevel.CRITICAL: 4,
        }
        max_level = permission_order.get(max_permission, 2)
        return [
            agent for agent in self._agents_by_id.values()
            if permission_order.get(agent.required_permission, 2) <= max_level
        ]

    def clear(self) -> None:
        """Clear all registered agents."""
        self._agents_by_id.clear()
        self._agents_by_name.clear()
        logger.debug("AgentRegistry cleared.")


_global_agent_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """Get or initialize global AgentRegistry singleton."""
    global _global_agent_registry
    if _global_agent_registry is None:
        _global_agent_registry = AgentRegistry()
    return _global_agent_registry

