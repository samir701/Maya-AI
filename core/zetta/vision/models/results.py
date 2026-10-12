"""Vision Data Models and Contracts for ZETTA Phase 05."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class ScreenInfo:
    """Information about a display/screen/monitor."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    display_name: str = ""
    width: int = 0
    height: int = 0
    x: int = 0
    y: int = 0
    is_primary: bool = False
    scale_factor: float = 1.0
    refresh_rate: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "width": self.width,
            "height": self.height,
            "x": self.x,
            "y": self.y,
            "is_primary": self.is_primary,
            "scale_factor": self.scale_factor,
            "refresh_rate": self.refresh_rate,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class BoundingBox:
    """Bounding box with x, y, width, height."""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BoundingBox":
        return cls(
            x=d.get("x", 0),
            y=d.get("y", 0),
            width=d.get("width", 0),
            height=d.get("height", 0),
        )


@dataclass
class ScreenCapture:
    """Represents a captured screen image."""
    id: str = field(default_factory=lambda: str(uuid4()))
    image_data: bytes = field(default_factory=bytes)
    width: int = 0
    height: int = 0
    format: str = "png"
    source_display: Optional[str] = None
    file_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "source_display": self.source_display,
            "file_path": self.file_path,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "image_size_bytes": len(self.image_data),
        }



@dataclass
class OCRTextRegion:
    """A single text region detected by OCR."""
    text: str = ""
    confidence: float = 0.0
    bounding_box: BoundingBox = field(default_factory=BoundingBox)
    page_number: int = 1
    line_number: int = 0
    word_number: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box.to_dict(),
            "page_number": self.page_number,
            "line_number": self.line_number,
            "word_number": self.word_number,
            "metadata": self.metadata,
        }


@dataclass
class OCRResult:
    """Complete OCR result from processing an image."""
    id: str = field(default_factory=lambda: str(uuid4()))
    text: str = ""
    regions: List[OCRTextRegion] = field(default_factory=list)
    language: str = "en"
    confidence: float = 0.0
    processing_duration_ms: float = 0.0
    image_width: int = 0
    image_height: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "regions": [r.to_dict() for r in self.regions],
            "language": self.language,
            "confidence": self.confidence,
            "processing_duration_ms": self.processing_duration_ms,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "timestamp": self.timestamp,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class UIElement:
    """A detected UI element."""
    element_type: str = ""  # "button", "input", "link", "text", "region", "unknown"
    label: str = ""
    confidence: float = 0.0
    bounding_box: BoundingBox = field(default_factory=BoundingBox)
    attributes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_type": self.element_type,
            "label": self.label,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box.to_dict(),
            "attributes": self.attributes,
            "metadata": self.metadata,
        }


@dataclass
class UIDetectionResult:
    """Result of UI detection on a screenshot."""
    id: str = field(default_factory=lambda: str(uuid4()))
    elements: List[UIElement] = field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    processing_duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "elements": [e.to_dict() for e in self.elements],
            "image_width": self.image_width,
            "image_height": self.image_height,
            "processing_duration_ms": self.processing_duration_ms,
            "timestamp": self.timestamp,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class VisionAnalysisResult:
    """Complete vision analysis result."""
    id: str = field(default_factory=lambda: str(uuid4()))
    screen_info: Optional[ScreenInfo] = None
    screen_capture: Optional[ScreenCapture] = None
    ocr_result: Optional[OCRResult] = None
    ui_detection_result: Optional[UIDetectionResult] = None
    description: str = ""
    confidence: float = 0.0
    processing_duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "screen_info": self.screen_info.to_dict() if self.screen_info else None,
            "screen_capture": self.screen_capture.to_dict() if self.screen_capture else None,
            "ocr_result": self.ocr_result.to_dict() if self.ocr_result else None,
            "ui_detection_result": self.ui_detection_result.to_dict() if self.ui_detection_result else None,
            "description": self.description,
            "confidence": self.confidence,
            "processing_duration_ms": self.processing_duration_ms,
            "timestamp": self.timestamp,
            "error": self.error,
            "metadata": self.metadata,
        }