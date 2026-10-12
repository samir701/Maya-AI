"""ZETTA Media Processor Interface and Fake Implementation."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from core.zetta.creator.models import MediaItem


class BaseMediaProcessor(ABC):
    """Abstract interface for video/audio inspection and transformation."""

    @abstractmethod
    def extract_metadata(self, file_path: str) -> MediaItem:
        """Inspect file and return technical metadata."""
        raise NotImplementedError

    @abstractmethod
    def generate_thumbnail(self, video_path: str, timestamp_sec: float = 1.0) -> str:
        """Extract a video frame as an image thumbnail."""
        raise NotImplementedError


class FakeMediaProcessor(BaseMediaProcessor):
    """Deterministic offline media processor."""

    def extract_metadata(self, file_path: str) -> MediaItem:
        p = Path(file_path)
        ext = p.suffix.lower()
        mtype = "video" if ext in [".mp4", ".mkv", ".mov"] else "audio" if ext in [".wav", ".mp3"] else "image"
        size = p.stat().st_size if p.exists() else 1024 * 1024

        return MediaItem(
            file_path=str(file_path),
            media_type=mtype,
            duration_seconds=120.0 if mtype in ["video", "audio"] else None,
            resolution="1920x1080" if mtype in ["video", "image"] else None,
            file_size_bytes=size,
        )

    def generate_thumbnail(self, video_path: str, timestamp_sec: float = 1.0) -> str:
        p = Path(video_path)
        thumb_path = p.with_suffix(".thumb.png")
        return str(thumb_path)
