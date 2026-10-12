"""ZETTA Prompt Registry."""

from typing import Dict, Optional
from core.zetta.ai.prompts.template import PromptTemplate
from core.zetta.utils.errors import ValidationError
from core.zetta.utils.logging import get_logger

logger = get_logger("prompt_registry")


class PromptRegistry:
    """Registry managing reusable system and user prompt templates."""

    def __init__(self) -> None:
        self._templates: Dict[str, PromptTemplate] = {}
        self._register_default_prompts()

    def register(self, template: PromptTemplate) -> None:
        self._templates[template.name] = template
        logger.info(f"Registered prompt template '{template.name}' [v{template.version}]")

    def get(self, name: str) -> PromptTemplate:
        if name not in self._templates:
            raise ValidationError(f"Prompt template '{name}' not found in registry.")
        return self._templates[name]

    def _register_default_prompts(self) -> None:
        """Register built-in system prompt templates."""
        self.register(
            PromptTemplate(
                name="system_default",
                system_prompt="You are ZETTA, an intelligent, helpful, local-first AI assistant.",
                template="{user_input}",
                version="1.0.0",
            )
        )
        self.register(
            PromptTemplate(
                name="structured_json",
                system_prompt="You are ZETTA. Respond strictly in valid JSON format matching the schema.",
                template="Request: {user_input}\nSchema: {schema}",
                version="1.0.0",
            )
        )


_prompt_registry_instance: PromptRegistry = PromptRegistry()


def get_prompt_registry() -> PromptRegistry:
    return _prompt_registry_instance
