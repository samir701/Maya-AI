"""ZETTA Vision & Screen Understanding Layer - Phase 05."""

from core.zetta.vision.models import (
    ScreenInfo,
    ScreenCapture,
    OCRTextRegion,
    OCRResult,
    UIElement,
    UIDetectionResult,
    VisionAnalysisResult,
    BoundingBox,
)

from core.zetta.vision.screen import (
    ScreenCaptureProvider,
    LinuxScreenCaptureProvider,
    FakeScreenCaptureProvider,
    ScreenCaptureError,
    get_screen_capture_provider,
    DisplayManager,
    get_display_manager,
)

from core.zetta.vision.ocr import (
    OCRProvider,
    FakeOCRProvider,
    LocalOCRProvider,
    OCRError,
    get_ocr_provider,
)

from core.zetta.vision.ui_detection import (
    UIDetector,
    FakeUIDetector,
    LocalUIDetector,
    UIDetectionError,
    get_ui_detector,
    UIElement as UIDetUIElement,
    UIDetectionResult as UIDetUIDetectionResult,
)

from core.zetta.vision.analysis import (
    VisionAnalyzer,
    FakeVisionAnalyzer,
    get_vision_analyzer,
)

from core.zetta.vision.manager import (
    VisionManager,
    get_vision_manager,
    set_vision_manager,
)

__all__ = [
    # Models
    "ScreenInfo",
    "ScreenCapture",
    "OCRTextRegion",
    "OCRResult",
    "UIElement",
    "UIDetectionResult",
    "VisionAnalysisResult",
    "BoundingBox",
    # Screen
    "ScreenCaptureProvider",
    "LinuxScreenCaptureProvider",
    "FakeScreenCaptureProvider",
    "ScreenCaptureError",
    "get_screen_capture_provider",
    "DisplayManager",
    "get_display_manager",
    # OCR
    "OCRProvider",
    "FakeOCRProvider",
    "LocalOCRProvider",
    "OCRError",
    "get_ocr_provider",
    # UI Detection
    "UIDetector",
    "FakeUIDetector",
    "LocalUIDetector",
    "UIDetectionError",
    "get_ui_detector",
    "UIDetUIElement",
    "UIDetUIDetectionResult",
    # Analysis
    "VisionAnalyzer",
    "FakeVisionAnalyzer",
    "get_vision_analyzer",
    # Manager
    "VisionManager",
    "get_vision_manager",
    "set_vision_manager",
]