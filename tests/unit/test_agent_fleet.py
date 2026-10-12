"""Unit tests for Milestone 08.4 Agent Fleet."""

import pytest
from core.zetta.agents.fleet import (
    BrowserAgent,
    DocumentAgent,
    GeneralAssistantAgent,
    ResearchAgent,
    VisionAgent,
    VoiceAgent,
    register_default_fleet,
)
from core.zetta.agents.manager import AgentRegistry, reset_agent_manager
from shared.types.contracts import SubTask
from shared.types.enums import AgentCapability, TaskStatus


class TestAgentFleet:
    """Validate specialized agents in the agent fleet."""

    def setup_method(self):
        reset_agent_manager()

    def test_general_assistant_agent_execution(self):
        agent = GeneralAssistantAgent()
        task = SubTask(name="Analyze Goal", description="Check basic operation")
        res = agent.execute(task)

        assert res.success is True
        assert "summary" in res.data
        assert task.status == TaskStatus.COMPLETED

    def test_browser_agent_execution(self):
        agent = BrowserAgent(use_fake=True)
        task = SubTask(name="Visit site", description="Navigate to https://example.com")
        res = agent.execute(task)

        assert res.success is True
        assert "url" in res.data
        assert "browser_navigate" in res.tools_called

    def test_vision_agent_execution(self):
        agent = VisionAgent(use_fake=True)
        task = SubTask(name="Observe screen")
        res = agent.execute(task)

        assert res.success is True
        assert "vision_screen_info" in res.tools_called
        assert "ocr" in res.data

    def test_voice_agent_execution(self):
        agent = VoiceAgent(use_fake=True)
        task = SubTask(name="Speak greeting", metadata={"text": "Hello world"})
        res = agent.execute(task)

        assert res.success is True
        assert "voice_synthesize" in res.tools_called

    def test_research_agent_execution(self):
        agent = ResearchAgent()
        task = SubTask(name="Investigate topic", description="Summarize AI advancements")
        res = agent.execute(task)

        assert res.success is True
        assert "findings" in res.data

    def test_document_agent_execution(self):
        agent = DocumentAgent()
        task = SubTask(name="Draft document", description="Create README summary")
        res = agent.execute(task)

        assert res.success is True
        assert "document" in res.data
        assert res.data["length_chars"] > 0

    def test_register_default_fleet(self):
        registry = AgentRegistry()
        register_default_fleet(registry)

        agents = registry.list_agents()
        assert len(agents) >= 6

        browser_agents = registry.find_by_capability(AgentCapability.BROWSER)
        assert len(browser_agents) == 1
        assert browser_agents[0].name == "BrowserAgent"

        voice_agents = registry.find_by_capability(AgentCapability.VOICE)
        assert len(voice_agents) == 1
        assert voice_agents[0].name == "VoiceAgent"
