"""ZETTA Interaction Manager Orchestrator."""

import re
from typing import Any, Dict, Iterator, Optional, Tuple
from core.zetta.ai.brain import AIBrain, get_ai_brain
from core.zetta.ai.context import ContextBuilder
from core.zetta.ai.prompts.registry import get_prompt_registry
from core.zetta.events import Event, EventBus, get_event_bus
from core.zetta.interaction.confirmation import ConfirmationInterface
from core.zetta.interaction.formatting import normalize_user_input
from core.zetta.interaction.session import Session, SessionManager, get_session_manager
from core.zetta.memory.manager import MemoryManager, get_memory_manager
from core.zetta.security import SecurityManager, get_security_manager
from core.zetta.tasks import TaskManager, get_task_manager
from core.zetta.tools import ToolRegistry, get_tool_registry
from core.zetta.utils.errors import ZettaError
from core.zetta.utils.logging import get_logger
from shared.types import AIProviderType, AIRole, AIRequest, EventType, MemorySource, MemoryType

logger = get_logger("interaction_manager")

# Task intent extraction regex (e.g., "create a task to review ZETTA architecture")
TASK_INTENT_REGEX = re.compile(
    r"^(?:create|add|schedule|new)\s+(?:a\s+)?task\s+(?:to|for)?\s*(.+)",
    re.IGNORECASE,
)


class InteractionManager:
    """Central orchestrator connecting UI shell, sessions, memory, context, brain, tasks, and security."""

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        memory_manager: Optional[MemoryManager] = None,
        ai_brain: Optional[AIBrain] = None,
        task_manager: Optional[TaskManager] = None,
        security_manager: Optional[SecurityManager] = None,
        tool_registry: Optional[ToolRegistry] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.session_mgr = session_manager or get_session_manager()
        self.mem_mgr = memory_manager or get_memory_manager()
        self.brain = ai_brain or get_ai_brain()
        self.task_mgr = task_manager or get_task_manager()
        self.security = security_manager or get_security_manager()
        self.tool_reg = tool_registry or get_tool_registry()
        self.event_bus = event_bus or get_event_bus()
        self.confirmation = ConfirmationInterface(self.security, self.event_bus)

    def detect_task_intent(self, user_input: str) -> Optional[str]:
        """Check if user input requests creation of a task."""
        match = TASK_INTENT_REGEX.search(user_input.strip())
        if match:
            return match.group(1).strip()
        return None

    def process_user_message(
        self,
        session_id: str,
        user_input: str,
        provider_type: Optional[AIProviderType] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Process user input synchronously through Memory -> Context -> AIBrain -> Persistence."""
        user_text = normalize_user_input(user_input)
        if not user_text:
            return ""

        # 1. Publish User Message Event
        self.event_bus.publish(
            Event(
                event_type=EventType.USER_MESSAGE_RECEIVED,
                payload={"session_id": session_id, "content": user_text},
            )
        )

        # 2. Append User Message to Session History
        self.session_mgr.append_message(session_id, AIRole.USER, user_text)

        # 3. Check for Task Intent
        task_description = self.detect_task_intent(user_text)
        if task_description:
            task = self.task_mgr.create_task(name=task_description)
            response_text = f"Task created successfully.\n  ID: {task.id}\n  Status: {task.status.value}\n  Title: {task.name}"
            self.session_mgr.append_message(session_id, AIRole.ASSISTANT, response_text)
            self.event_bus.publish(
                Event(
                    event_type=EventType.ASSISTANT_RESPONSE_GENERATED,
                    payload={"session_id": session_id, "content": response_text, "is_task": True},
                )
            )
            return response_text

        # 4. Check for Tool Intent
        from core.zetta.tools.routing import ToolRouter
        tool_router = ToolRouter()
        tool_intent = tool_router.detect_intent(user_text)
        if tool_intent:
            tool_result = tool_router.execute_intent(tool_intent)
            if tool_result.success:
                import json
                formatted_data = json.dumps(tool_result.data, indent=2) if isinstance(tool_result.data, (dict, list)) else str(tool_result.data)
                response_text = f"Executed Tool '{tool_result.tool_name}':\n```json\n{formatted_data}\n```"
            else:
                err_msg = tool_result.error.message if tool_result.error else "Execution failed."
                response_text = f"Tool Execution Failed ('{tool_result.tool_name}'): {err_msg}"

            self.session_mgr.append_message(session_id, AIRole.ASSISTANT, response_text)
            self.event_bus.publish(
                Event(
                    event_type=EventType.ASSISTANT_RESPONSE_GENERATED,
                    payload={"session_id": session_id, "content": response_text, "is_tool": True},
                )
            )
            return response_text

        # 5. Check for explicit fact saving instruction ("remember that ...")
        if user_text.lower().startswith("remember that "):
            fact_content = user_text[14:].strip()
            if fact_content:
                mem = self.mem_mgr.add_memory(
                    content=fact_content,
                    memory_type=MemoryType.LONG_TERM,
                    source=MemorySource.USER_EXPLICIT,
                    importance=0.85,
                )
                logger.info(f"Explicit memory saved via chat: '{mem.content}'")

        # 6. Build Context with Memory Retrieval & Conversation History
        builder = ContextBuilder()
        if system_prompt:
            builder.set_system_instructions(system_prompt)
        else:
            default_tmpl = get_prompt_registry().get("system_default")
            builder.set_system_instructions(default_tmpl.system_prompt)

        # Inject Memory Context
        builder.inject_relevant_memories(
            user_prompt=user_text,
            memory_manager=self.mem_mgr,
            session_id=session_id,
        )

        # Inject Conversation History
        history = self.session_mgr.get_history(session_id, limit=10)

        # Build complete messages payload
        messages = builder.build_messages(
            user_prompt=user_text,
            history=history[:-1] if history else None,  # Exclude current prompt (already appended by builder)
        )

        try:
            # 7. Execute AI Generation through AIBrain
            request = AIRequest(messages=messages)
            ai_response = self.brain.generate(request, provider_type=provider_type)
            response_text = ai_response.text

        except ZettaError as ze:
            logger.error(f"Zetta system error during chat thinking: {ze}")
            response_text = f"An error occurred: {ze.message}"
        except Exception as e:
            logger.error(f"Unexpected error during chat thinking: {e}")
            response_text = f"AI Service Error: {str(e)}"

        # 8. Append Assistant Response to Session History
        self.session_mgr.append_message(session_id, AIRole.ASSISTANT, response_text)

        # 9. Publish Assistant Event
        self.event_bus.publish(
            Event(
                event_type=EventType.ASSISTANT_RESPONSE_GENERATED,
                payload={"session_id": session_id, "content": response_text},
            )
        )

        return response_text


    def stream_user_message(
        self,
        session_id: str,
        user_input: str,
        provider_type: Optional[AIProviderType] = None,
        system_prompt: Optional[str] = None,
    ) -> Iterator[str]:
        """Stream user input response chunk by chunk."""
        user_text = normalize_user_input(user_input)
        if not user_text:
            return

        self.event_bus.publish(
            Event(
                event_type=EventType.USER_MESSAGE_RECEIVED,
                payload={"session_id": session_id, "content": user_text},
            )
        )
        self.session_mgr.append_message(session_id, AIRole.USER, user_text)

        # Check for Task Intent
        task_description = self.detect_task_intent(user_text)
        if task_description:
            task = self.task_mgr.create_task(name=task_description)
            response_text = f"Task created successfully.\n  ID: {task.id}\n  Status: {task.status.value}\n  Title: {task.name}"
            self.session_mgr.append_message(session_id, AIRole.ASSISTANT, response_text)
            yield response_text
            return

        # Check for Tool Intent
        from core.zetta.tools.routing import ToolRouter
        tool_router = ToolRouter()
        tool_intent = tool_router.detect_intent(user_text)
        if tool_intent:
            tool_result = tool_router.execute_intent(tool_intent)
            if tool_result.success:
                import json
                formatted_data = json.dumps(tool_result.data, indent=2) if isinstance(tool_result.data, (dict, list)) else str(tool_result.data)
                response_text = f"Executed Tool '{tool_result.tool_name}':\n```json\n{formatted_data}\n```"
            else:
                err_msg = tool_result.error.message if tool_result.error else "Execution failed."
                response_text = f"Tool Execution Failed ('{tool_result.tool_name}'): {err_msg}"

            self.session_mgr.append_message(session_id, AIRole.ASSISTANT, response_text)
            self.event_bus.publish(
                Event(
                    event_type=EventType.ASSISTANT_RESPONSE_GENERATED,
                    payload={"session_id": session_id, "content": response_text, "is_tool": True},
                )
            )
            yield response_text
            return

        # Explicit Fact Saving
        if user_text.lower().startswith("remember that "):
            fact_content = user_text[14:].strip()
            if fact_content:
                self.mem_mgr.add_memory(
                    content=fact_content,
                    memory_type=MemoryType.LONG_TERM,
                    source=MemorySource.USER_EXPLICIT,
                    importance=0.85,
                )

        # Build Context
        builder = ContextBuilder()
        if system_prompt:
            builder.set_system_instructions(system_prompt)
        else:
            default_tmpl = get_prompt_registry().get("system_default")
            builder.set_system_instructions(default_tmpl.system_prompt)

        builder.inject_relevant_memories(
            user_prompt=user_text,
            memory_manager=self.mem_mgr,
            session_id=session_id,
        )
        history = self.session_mgr.get_history(session_id, limit=10)
        messages = builder.build_messages(user_prompt=user_text, history=history[:-1] if history else None)

        # Execute Stream
        full_response_chunks = []
        try:
            for chunk in self.brain.stream_messages(messages, provider_type=provider_type):
                if chunk.content:
                    full_response_chunks.append(chunk.content)
                    yield chunk.content
        except Exception as e:
            logger.warning(f"Streaming failed, falling back to generate: {e}")
            fallback_text = self.process_user_message(session_id, user_text, provider_type, system_prompt)
            yield fallback_text
            return

        full_text = "".join(full_response_chunks)
        self.session_mgr.append_message(session_id, AIRole.ASSISTANT, full_text)
        self.event_bus.publish(
            Event(
                event_type=EventType.ASSISTANT_RESPONSE_GENERATED,
                payload={"session_id": session_id, "content": full_text},
            )
        )


_interaction_manager_instance: Optional[InteractionManager] = None


def get_interaction_manager(reload: bool = False) -> InteractionManager:
    global _interaction_manager_instance
    if _interaction_manager_instance is None or reload:
        _interaction_manager_instance = InteractionManager()
    return _interaction_manager_instance
