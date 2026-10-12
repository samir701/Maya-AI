"""Vision Manager - Orchestration Layer for ZETTA Phase 05."""

import time
from typing import Optional
from core.zetta.vision.screen import (
    ScreenCaptureProvider,
    FakeScreenCaptureProvider,
    get_screen_capture_provider,
)
from core.zetta.vision.ocr import (
    OCRProvider,
    FakeOCRProvider,
    get_ocr_provider,
)
from core.zetta.vision.ui_detection import (
    UIDetector,
    FakeUIDetector,
    get_ui_detector,
)
from core.zetta.vision.analysis import (
    VisionAnalyzer,
    FakeVisionAnalyzer,
    get_vision_analyzer,
)
from core.zetta.vision.models.results import (
    ScreenInfo,
    ScreenCapture,
    OCRResult,
    UIDetectionResult,
    VisionAnalysisResult,
)
from core.zetta.events import get_event_bus, Event
from shared.types.enums import EventType
from core.zetta.utils.logging import get_logger

logger = get_logger("vision_manager")


class VisionManager:
    """Orchestrates vision pipeline: capture -> OCR -> UI detection -> analysis."""

    def __init__(
        self,
        screen_provider: Optional[ScreenCaptureProvider] = None,
        ocr_provider: Optional[OCRProvider] = None,
        ui_detector: Optional[UIDetector] = None,
        analyzer: Optional[VisionAnalyzer] = None,
        use_fake: bool = False,
    ):
        self._screen_provider = screen_provider or get_screen_capture_provider(use_fake=use_fake)
        self._ocr_provider = ocr_provider or get_ocr_provider("fake" if use_fake else "local")
        self._ui_detector = ui_detector or get_ui_detector("fake" if use_fake else "local")
        self._analyzer = analyzer or get_vision_analyzer(use_fake=use_fake)
        self._event_bus = get_event_bus()
        self._call_count = 0

    def get_screen_info(self, display_id: Optional[str] = None) -> ScreenInfo:
        """Get screen/display information."""
        if display_id:
            for display in self._screen_provider.get_displays():
                if display.name == display_id or display.id == display_id:
                    return display
            raise ValueError(f"Display not found: {display_id}")
        primary = self._screen_provider.get_primary_display()
        if not primary:
            raise RuntimeError("No primary display found")
        return primary

    def get_all_displays(self) -> list:
        """Get all available displays."""
        return self._screen_provider.get_displays()

    def capture_screen(
        self,
        display_id: Optional[str] = None,
        save_to_disk: bool = False,
        task_id: Optional[str] = None,
        require_auth: Optional[bool] = None,
    ) -> ScreenCapture:
        """Capture screen. Memory-only by default (save_to_disk=False).

        Enforces ScreenAccessManager authorization before capturing.
        """
        from core.zetta.security.screen_access import get_screen_access_manager
        sam = get_screen_access_manager()
        is_fake = isinstance(self._screen_provider, FakeScreenCaptureProvider)

        should_check_auth = (
            require_auth is True
            or (not is_fake and require_auth is not False)
            or (is_fake and getattr(sam, "_enforce_on_fake", False))
        )
        if should_check_auth:
            sam.require_access(task_id=task_id, consume=True)

        self._call_count += 1
        start = time.perf_counter()

        self._event_bus.publish(Event(
            event_type=EventType.TOOL_STARTED,
            payload={"operation": "vision_capture", "display_id": display_id, "save_to_disk": save_to_disk},
            task_id=task_id,
        ))

        try:
            capture = self._screen_provider.capture_screen(display_id=display_id, save_to_disk=save_to_disk)
            duration_ms = (time.perf_counter() - start) * 1000

            self._event_bus.publish(Event(
                event_type=EventType.TOOL_COMPLETED,
                payload={"operation": "vision_capture", "duration_ms": duration_ms, "save_to_disk": save_to_disk},
                task_id=task_id,
            ))

            return capture
        except Exception as e:
            self._event_bus.publish(Event(
                event_type=EventType.TOOL_FAILED,
                payload={"operation": "vision_capture", "error": str(e)},
                task_id=task_id,
            ))
            raise

    def perform_ocr(self, capture: ScreenCapture) -> OCRResult:
        """Perform OCR on screen capture."""
        self._call_count += 1
        start = time.perf_counter()

        self._event_bus.publish(Event(
            event_type=EventType.TOOL_STARTED,
            payload={"operation": "vision_ocr"},
            task_id=None,
        ))

        try:
            result = self._ocr_provider.recognize(capture)
            duration_ms = (time.perf_counter() - start) * 1000

            self._event_bus.publish(Event(
                event_type=EventType.TOOL_COMPLETED,
                payload={"operation": "vision_ocr", "duration_ms": duration_ms, "text_length": len(result.text)},
                task_id=None,
            ))

            return result
        except Exception as e:
            self._event_bus.publish(Event(
                event_type=EventType.TOOL_FAILED,
                payload={"operation": "vision_ocr", "error": str(e)},
                task_id=None,
            ))
            raise

    def detect_ui(self, capture: ScreenCapture) -> UIDetectionResult:
        """Detect UI elements in screen capture."""
        self._call_count += 1
        start = time.perf_counter()

        self._event_bus.publish(Event(
            event_type=EventType.TOOL_STARTED,
            payload={"operation": "vision_detect_ui"},
            task_id=None,
        ))

        try:
            result = self._ui_detector.detect(capture)
            duration_ms = (time.perf_counter() - start) * 1000

            self._event_bus.publish(Event(
                event_type=EventType.TOOL_COMPLETED,
                payload={"operation": "vision_detect_ui", "duration_ms": duration_ms, "elements_count": len(result.elements)},
                task_id=None,
            ))

            return result
        except Exception as e:
            self._event_bus.publish(Event(
                event_type=EventType.TOOL_FAILED,
                payload={"operation": "vision_detect_ui", "error": str(e)},
                task_id=None,
            ))
            raise

    def analyze_screen(
        self,
        display_id: Optional[str] = None,
        capture: Optional[ScreenCapture] = None,
        run_ocr: bool = True,
        run_ui_detection: bool = True,
        save_to_disk: bool = False,
        task_id: Optional[str] = None,
        require_auth: Optional[bool] = None,
    ) -> VisionAnalysisResult:
        """Full vision analysis pipeline."""
        self._call_count += 1
        start = time.perf_counter()

        self._event_bus.publish(Event(
            event_type=EventType.TOOL_STARTED,
            payload={"operation": "vision_analyze", "display_id": display_id},
            task_id=task_id,
        ))

        try:
            # Get screen info
            screen_info = self.get_screen_info(display_id)

            # Capture screen if not provided
            if capture is None:
                capture = self.capture_screen(
                    display_id=display_id,
                    save_to_disk=save_to_disk,
                    task_id=task_id,
                    require_auth=require_auth,
                )

            # Run OCR if requested
            ocr_result = None
            if run_ocr:
                ocr_result = self.perform_ocr(capture)

            # Run UI detection if requested
            ui_detection_result = None
            if run_ui_detection:
                ui_detection_result = self.detect_ui(capture)

            # Analyze
            analysis = self._analyzer.analyze(
                screen_info=screen_info,
                screen_capture=capture,
                ocr_result=ocr_result,
                ui_detection_result=ui_detection_result,
            )

            total_duration = (time.perf_counter() - start) * 1000

            self._event_bus.publish(Event(
                event_type=EventType.TOOL_COMPLETED,
                payload={
                    "operation": "vision_analyze",
                    "duration_ms": total_duration,
                    "has_ocr": ocr_result is not None,
                    "has_ui": ui_detection_result is not None,
                },
                task_id=task_id,
            ))

            return analysis
        except Exception as e:
            self._event_bus.publish(Event(
                event_type=EventType.TOOL_FAILED,
                payload={"operation": "vision_analyze", "error": str(e)},
                task_id=task_id,
            ))
            raise

    def quick_analyze(
        self,
        display_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> VisionAnalysisResult:
        """Quick analysis with minimal processing."""
        return self.analyze_screen(
            display_id=display_id,
            run_ocr=True,
            run_ui_detection=True,
            task_id=task_id,
        )

    def get_capabilities(self) -> dict:
        """Get vision system capabilities."""
        return {
            "screen_capture": {
                "provider": self._screen_provider.__class__.__name__,
                "available": True,
                "displays": len(self._screen_provider.get_displays()),
            },
            "ocr": {
                "provider": self._ocr_provider.__class__.__name__,
                "available": self._ocr_provider.is_available(),
                "languages": self._ocr_provider.get_supported_languages(),
            },
            "ui_detection": {
                "detector": self._ui_detector.__class__.__name__,
                "available": self._ui_detector.is_available(),
                "element_types": self._ui_detector.get_supported_element_types(),
            },
            "analysis": {
                "analyzer": self._analyzer.__class__.__name__,
                "available": True,
            },
        }


# Global instance
_vision_manager_instance: Optional[VisionManager] = None


def get_vision_manager(use_fake: bool = False) -> VisionManager:
    """Get global vision manager instance."""
    global _vision_manager_instance
    if _vision_manager_instance is None:
        _vision_manager_instance = VisionManager(use_fake=use_fake)
    return _vision_manager_instance


def set_vision_manager(manager: VisionManager) -> None:
    """Set global vision manager instance (for testing)."""
    global _vision_manager_instance
    _vision_manager_instance = manager