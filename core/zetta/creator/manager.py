"""ZETTA Creator Manager coordinating media processing and packaging."""

from typing import Optional
from core.zetta.creator.generator import ContentMetadataGenerator
from core.zetta.creator.models import ContentMetadata, MediaItem
from core.zetta.creator.provider import BaseMediaProcessor, FakeMediaProcessor
from core.zetta.security.manager import SecurityManager, get_security_manager
from core.zetta.utils.errors import SecurityError
from core.zetta.utils.logging import get_logger
from shared.types.enums import PermissionLevel

logger = get_logger("creator_manager")


class CreatorManager:
    """Manages content creator workflows, metadata generation, and media processing."""

    def __init__(
        self,
        media_processor: Optional[BaseMediaProcessor] = None,
        generator: Optional[ContentMetadataGenerator] = None,
        security_manager: Optional[SecurityManager] = None,
    ) -> None:
        self.processor = media_processor or FakeMediaProcessor()
        self.generator = generator or ContentMetadataGenerator()
        self.security = security_manager or get_security_manager()

    def process_media(self, file_path: str, user_role: str = "user") -> MediaItem:
        """Inspect media file and extract technical specifications."""
        if not self.security.check_permission(user_role, PermissionLevel.LOW):
            raise SecurityError("Permission denied to inspect media.")

        item = self.processor.extract_metadata(file_path)
        self.security.audit.log_event(
            action="process_media",
            actor=user_role,
            resource=file_path,
            status="SUCCESS",
            details={"media_type": item.media_type, "duration": item.duration_seconds},
        )
        return item

    def generate_content_pack(
        self,
        topic: str,
        transcript: Optional[str] = None,
        platform: str = "youtube",
        user_role: str = "user",
    ) -> ContentMetadata:
        """Produce titles, tags, and descriptions for creators."""
        if not self.security.check_permission(user_role, PermissionLevel.LOW):
            raise SecurityError("Permission denied to generate content metadata.")

        meta = self.generator.generate(topic=topic, transcript=transcript, platform=platform)
        self.security.audit.log_event(
            action="generate_content_pack",
            actor=user_role,
            resource=f"content:{platform}",
            status="SUCCESS",
            details={"title": meta.title, "tags_count": len(meta.tags)},
        )
        return meta


_global_creator_manager: Optional[CreatorManager] = None


def get_creator_manager() -> CreatorManager:
    """Get or initialize global CreatorManager singleton."""
    global _global_creator_manager
    if _global_creator_manager is None:
        _global_creator_manager = CreatorManager()
    return _global_creator_manager
