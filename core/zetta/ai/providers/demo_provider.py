"""ZETTA Demo AI Provider — Intelligent offline responses for development & exploration.

This provider is NOT for unit tests (use FakeAIProvider for that).
It is designed to give realistic, human-like responses while remaining
100% offline and deterministic — no API key required.

Used automatically by the CLI when no real API key is configured.
"""

import re
from typing import Iterator, List, Optional
from core.zetta.ai.providers.base import AIProvider
from shared.types import (
    AIChoice,
    AIMessage,
    AIProviderType,
    AIRequest,
    AIResponse,
    AIRole,
    AIStreamChunk,
    AIUsage,
)


class DemoAIProvider(AIProvider):
    """Offline demo provider with keyword-aware, context-sensitive responses.

    Gives realistic responses for common ZETTA interaction patterns without
    requiring any API key or network connection. Suitable for exploring the
    CLI and demonstrating the full pipeline end-to-end.
    """

    provider_name = AIProviderType.FAKE  # Re-uses FAKE type so factory still works
    model = "demo-v1"
    capabilities: List[str] = ["text", "streaming"]

    # Response catalogue: (regex_pattern, response_template)
    _RESPONSE_CATALOGUE = [
        # Greetings
        (
            r"\b(hello|hi|hey|good (morning|afternoon|evening)|greetings|howdy)\b",
            "Hello! I'm ZETTA, your AI employee. I'm currently running in offline demo mode — "
            "no real API calls are being made. I can help you explore my capabilities, manage tasks, "
            "search memories, and more. What would you like to do today?",
        ),
        # Who are you / what are you
        (
            r"\b(who are you|what are you|tell me about yourself|what is zetta|introduce yourself)\b",
            "I'm ZETTA — a local-first, privacy-preserving AI employee. I'm built to understand "
            "natural language, maintain persistent memory, manage tasks, and eventually control "
            "your desktop, browser, and applications.\n\n"
            "Right now I'm running in offline demo mode with DemoAIProvider. "
            "Switch to a real provider (OpenAI or Gemini) by setting your API key in .env.",
        ),
        # What can you do / capabilities
        (
            r"\b(what can you do|capabilities|features|help me|how can you help|what do you offer)\b",
            "Here's what I can do in the current Phase 03 build:\n\n"
            "  • Natural language conversation (this session)\n"
            "  • Persistent memory — I remember important facts across sessions\n"
            "  • Task management — create, list, cancel tasks via `/tasks` or CLI\n"
            "  • Slash commands — `/help`, `/status`, `/memory`, `/tasks`, `/exit`\n"
            "  • System status reporting via `/status`\n\n"
            "Future phases will add: desktop control, browser automation, voice, vision, "
            "file management, and autonomous multi-step execution.",
        ),
        # Memory related
        (
            r"\b(remember|memory|memories|store|recall|forget|memorize)\b",
            "My memory system is active and storing information across sessions. "
            "You can save a fact explicitly by typing:\n\n"
            "  remember that [your fact here]\n\n"
            "To view stored memories: `/memory`\n"
            "To search memories: `/memory search [query]`\n"
            "To clear session memory: `/memory clear`",
        ),
        # Task related
        (
            r"\b(task|tasks|todo|to-do|schedule|create a task|add a task)\b",
            "I can manage tasks for you. Try:\n\n"
            "  • 'Create a task to review the ZETTA architecture'\n"
            "  • `/tasks` — to see all current tasks\n"
            "  • `python core/zetta/cli.py task list` — from the terminal\n\n"
            "Tasks are tracked with IDs, statuses (CREATED, RUNNING, COMPLETED), "
            "and can be cancelled at any time.",
        ),
        # Status
        (
            r"\b(status|health|system|running|how are you|are you working)\b",
            "All systems are operational. Here's my current state:\n\n"
            "  • AI Core:        ONLINE (demo mode)\n"
            "  • Memory System:  ONLINE\n"
            "  • Task Manager:   ONLINE\n"
            "  • Security:       SANDBOXED\n"
            "  • Event Bus:      ACTIVE\n\n"
            "For a detailed report, type `/status`.",
        ),
        # Python / programming
        (
            r"\b(python|programming|code|coding|developer|software|script)\b",
            "ZETTA is built with Python 3.12 and follows a strict modular architecture:\n\n"
            "  core/zetta/ai/        — AI Brain, Providers, Context Builder\n"
            "  core/zetta/memory/    — Short/Long-term memory, Retrieval Engine\n"
            "  core/zetta/interaction/ — Chat shell, Session Manager, Commands\n"
            "  core/zetta/security/  — Permissions, Sandboxing, Audit Log\n\n"
            "The project uses Pydantic for type safety, SQLite for local persistence, "
            "and a pub/sub EventBus for inter-module communication.",
        ),
        # Phase / development
        (
            r"\b(phase|phases|development|progress|roadmap|next|future|plan)\b",
            "ZETTA is being built incrementally through locked phases:\n\n"
            "  ✓ Phase 00 — Foundation & Architecture\n"
            "  ✓ Phase 01 — AI Core\n"
            "  ✓ Phase 02 — Memory & Context Intelligence\n"
            "  ✓ Phase 03 — Interaction Shell (current)\n"
            "  ○ Phase 04 — Tools & System Capabilities (next)\n"
            "  ○ Phase 05 — Desktop & Browser Automation\n"
            "  ○ Phase 06 — Voice & Vision\n"
            "  ○ Phase 07 — Autonomous Agents\n\n"
            "Each phase is tested, verified, and locked before moving forward.",
        ),
        # How to use real AI
        (
            r"\b(real ai|openai|gemini|api key|api_key|gpt|claude|actual ai|real response)\b",
            "To connect ZETTA to a real AI provider:\n\n"
            "  1. Edit your .env file:\n"
            "       ZETTA_AI_DEFAULT_PROVIDER=gemini\n"
            "       ZETTA_AI_API_KEY=your-api-key-here\n"
            "       ZETTA_AI_MODEL=gemini-2.0-flash\n\n"
            "  2. Run with the --real flag:\n"
            "       python core/zetta/cli.py chat --real\n\n"
            "Supported providers: openai, gemini",
        ),
        # Thanks / appreciation
        (
            r"\b(thank|thanks|thank you|appreciate|great|awesome|good job|nice|well done)\b",
            "You're welcome! I'm here whenever you need me. "
            "Remember, I'm running in offline demo mode right now — "
            "add a real API key to .env and use `--real` for full intelligent responses.",
        ),
        # Goodbye / exit
        (
            r"\b(bye|goodbye|exit|quit|see you|later|done|stop)\b",
            "Goodbye! Your session data has been saved to memory. "
            "Type `/exit` to close the session cleanly, or Ctrl+C to terminate.",
        ),
    ]

    def __init__(self) -> None:
        self.last_request: Optional[AIRequest] = None
        self.call_count: int = 0

    def _build_response_text(self, messages: List[AIMessage]) -> str:
        """Generate a context-aware response based on the last user message."""
        # Find last user message
        user_text = ""
        for msg in reversed(messages):
            if msg.role == AIRole.USER:
                user_text = msg.content.strip()
                break

        if not user_text:
            return "I'm ready to help. What would you like to work on?"

        lower = user_text.lower()

        # Check response catalogue
        for pattern, response in self._RESPONSE_CATALOGUE:
            if re.search(pattern, lower):
                return response

        # Check for question pattern
        if user_text.endswith("?") or lower.startswith(("what", "how", "why", "where", "when", "who", "can", "could", "would", "should", "is", "are", "do", "does")):
            return (
                f"That's a good question: \"{user_text}\"\n\n"
                "In offline demo mode, I can only provide scripted responses for common topics. "
                "For fully intelligent answers, connect a real AI provider:\n\n"
                "  ZETTA_AI_DEFAULT_PROVIDER=gemini\n"
                "  ZETTA_AI_API_KEY=your-key\n\n"
                "Then run: python core/zetta/cli.py chat --real"
            )

        # Generic statement response
        return (
            f"Understood: \"{user_text}\"\n\n"
            "I'm processing your input in offline demo mode. My responses are based on "
            "pre-defined patterns rather than true language understanding.\n\n"
            "Try asking about: capabilities, memory, tasks, status, phases, or how to connect a real AI."
        )

    def generate(self, request: AIRequest) -> AIResponse:
        self.call_count += 1
        self.last_request = request

        text = self._build_response_text(request.messages or [])

        message = AIMessage(role=AIRole.ASSISTANT, content=text)
        choice = AIChoice(index=0, message=message, finish_reason="stop")
        usage = AIUsage(
            prompt_tokens=len(" ".join(m.content for m in (request.messages or []))),
            completion_tokens=len(text.split()),
            total_tokens=len(text.split()) + 10,
            duration_ms=2.0,
        )

        return AIResponse(
            provider=self.provider_name,
            model=request.model or self.model,
            choices=[choice],
            usage=usage,
            raw_response={"status": "demo_ok"},
        )

    def stream(self, request: AIRequest) -> Iterator[AIStreamChunk]:
        self.call_count += 1
        self.last_request = request

        text = self._build_response_text(request.messages or [])

        words = text.split(" ")
        for i, word in enumerate(words):
            is_last = i == len(words) - 1
            chunk_text = word if is_last else word + " "
            yield AIStreamChunk(
                id=f"demo_chunk_{i}",
                content=chunk_text,
                finish_reason="stop" if is_last else None,
                is_final=is_last,
            )

    def health_check(self) -> bool:
        return True
