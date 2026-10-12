"""ZETTA Creator Suite Models and Metadata Specifications."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class MediaItem:
    """Descriptor for processed or recorded media content."""
    file_path: str
    media_type: str  # "video", "audio", "image"
    media_id: str = field(default_factory=lambda: str(uuid4()))
    duration_seconds: Optional[float] = None
    resolution: Optional[str] = None
    file_size_bytes: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentMetadata:
    """SEO and publishing metadata for creator deliverables."""
    title: str
    description: str
    tags: List[str] = field(default_factory=list)
    category: str = "Technology"
    target_platform: str = "youtube"
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
