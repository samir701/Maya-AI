"""ZETTA Creator Suite Architecture."""

from core.zetta.creator.generator import ContentMetadataGenerator
from core.zetta.creator.manager import CreatorManager, get_creator_manager
from core.zetta.creator.models import ContentMetadata, MediaItem
from core.zetta.creator.provider import BaseMediaProcessor, FakeMediaProcessor

__all__ = [
    "BaseMediaProcessor",
    "FakeMediaProcessor",
    "ContentMetadataGenerator",
    "CreatorManager",
    "get_creator_manager",
    "ContentMetadata",
    "MediaItem",
]
