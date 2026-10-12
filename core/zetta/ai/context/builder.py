"""ZETTA AI Context Builder with Memory Context Injection."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from core.zetta.config import get_settings
from shared.types import AIMessage, AIRole, MemoryQueryResult


@dataclass
class ContextBuilder:
    """Assembles prompt contexts (system, user, conversation, task, env, relevant memories) into AIMessage lists."""

    system_instructions: Optional[str] = None
    environment_info: Dict[str, Any] = field(default_factory=dict)
    task_info: Optional[Dict[str, Any]] = None
    conversation_history: List[AIMessage] = field(default_factory=list)
    retrieved_memories: List[MemoryQueryResult] = field(default_factory=list)

    def set_system_instructions(self, instructions: str) -> "ContextBuilder":
        self.system_instructions = instructions
        return self

    def add_conversation_message(self, role: AIRole, content: str) -> "ContextBuilder":
        self.conversation_history.append(AIMessage(role=role, content=content))
        return self

    def set_task_context(self, task_id: str, task_name: str, details: Dict[str, Any]) -> "ContextBuilder":
        self.task_info = {"task_id": task_id, "name": task_name, "details": details}
        return self

    def inject_relevant_memories(
        self,
        user_prompt: str,
        memory_manager: Optional[Any] = None,
        max_memories: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> "ContextBuilder":
        """Retrieve and budget relevant memories for inclusion in prompt context."""
        settings = get_settings()
        if not settings.memory.memory_enabled:
            return self

        if memory_manager is None:
            # Lazy import to avoid circular dependencies
            from core.zetta.memory import get_memory_manager
            mem_mgr = get_memory_manager()
        else:
            mem_mgr = memory_manager

        limit = max_memories or settings.memory.max_context_memories

        results = mem_mgr.retrieve_relevant(query=user_prompt, limit=limit, session_id=session_id)
        self.retrieved_memories = results
        return self

    def build_messages(
        self,
        user_prompt: str,
        history: Optional[List[AIMessage]] = None,
    ) -> List[AIMessage]:
        """Construct ordered messages list for AI requests adhering to Memory Budget."""
        settings = get_settings()
        messages: List[AIMessage] = []

        # 1. System Prompt & Context Sections
        sys_parts = []
        if self.system_instructions:
            sys_parts.append(self.system_instructions)

        # 2. Inject Budgeted Relevant Memories
        if self.retrieved_memories:
            mem_lines = []
            current_chars = 0
            max_chars = settings.memory.max_context_memory_tokens * 4  # ~4 chars per token estimate

            for res in self.retrieved_memories:
                line = f"- [{res.memory.memory_type.value.upper()}] (Score: {res.score:.2f}) {res.memory.content}"
                if current_chars + len(line) > max_chars:
                    break
                mem_lines.append(line)
                current_chars += len(line)

            if mem_lines:
                sys_parts.append("[Retrieved Relevant Memory Context]:\n" + "\n".join(mem_lines))

        if self.task_info:
            sys_parts.append(f"[Active Task Context]: {self.task_info}")
        if self.environment_info:
            sys_parts.append(f"[System Environment]: {self.environment_info}")

        if sys_parts:
            messages.append(AIMessage(role=AIRole.SYSTEM, content="\n\n".join(sys_parts)))

        # 3. Conversation History
        if history:
            messages.extend(history)
        else:
            messages.extend(self.conversation_history)

        # 4. Current User Request
        messages.append(AIMessage(role=AIRole.USER, content=user_prompt))

        return messages
