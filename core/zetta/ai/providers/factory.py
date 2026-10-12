"""ZETTA AI Provider Factory and Registry."""

from typing import Dict, Optional, Type
from core.zetta.ai.providers.base import AIProvider
from core.zetta.ai.providers.demo_provider import DemoAIProvider
from core.zetta.ai.providers.fake_provider import FakeAIProvider
from core.zetta.ai.providers.gemini_provider import GeminiProvider
from core.zetta.ai.providers.groq_provider import GroqAIProvider
from core.zetta.ai.providers.openai_provider import OpenAIProvider
from core.zetta.config import get_settings
from core.zetta.utils.errors import ConfigurationError
from core.zetta.utils.logging import get_logger
from shared.types import AIProviderType

logger = get_logger("provider_factory")


class ProviderFactory:
    """Factory creating and managing AI provider instances."""

    def __init__(self) -> None:
        self._registry: Dict[AIProviderType, Type[AIProvider]] = {
            AIProviderType.FAKE: FakeAIProvider,
            AIProviderType.DEMO: DemoAIProvider,
            AIProviderType.OPENAI: OpenAIProvider,
            AIProviderType.GROQ: GroqAIProvider,
            AIProviderType.GEMINI: GeminiProvider,
            AIProviderType.LOCAL: OpenAIProvider,  # LocalLLMs use OpenAI-compatible endpoint
        }

    def get_provider(
        self,
        provider_type: Optional[AIProviderType] = None,
        **kwargs,
    ) -> AIProvider:
        """Retrieve or instantiate an AI provider based on configuration or explicit type."""
        settings = get_settings()

        if provider_type is None:
            config_provider_str = settings.ai.default_provider.lower()
            try:
                provider_type = AIProviderType(config_provider_str)
            except ValueError:
                logger.warning(
                    f"Unknown configured provider '{config_provider_str}'. Defaulting to 'fake' provider."
                )
                provider_type = AIProviderType.FAKE

        provider_cls = self._registry.get(provider_type)
        if not provider_cls:
            raise ConfigurationError(f"Unsupported AI Provider Type: {provider_type}")

        logger.info(f"Instantiating AI Provider: '{provider_type.value}'")
        return provider_cls(**kwargs)


_provider_factory_instance: ProviderFactory = ProviderFactory()


def get_provider(provider_type: Optional[AIProviderType] = None, **kwargs) -> AIProvider:
    return _provider_factory_instance.get_provider(provider_type, **kwargs)
