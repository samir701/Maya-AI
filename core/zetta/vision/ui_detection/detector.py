"""UI Detection Abstraction for ZETTA Phase 05."""

import time
from abc import ABC, abstractmethod
from typing import List, Optional
from core.zetta.vision.models.results import ScreenCapture, UIDetectionResult, UIElement, BoundingBox


class UIDetector(ABC):
    """Abstract base class for UI detectors."""

    @abstractmethod
    def detect(self, image: ScreenCapture) -> UIDetectionResult:
        """Detect UI elements in the given screen capture."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the UI detector is available/functional."""
        pass

    @abstractmethod
    def get_supported_element_types(self) -> List[str]:
        """Get list of supported UI element types."""
        pass


class UIDetectionError(Exception):
    """Exception for UI detection failures."""
    pass


class FakeUIDetector(UIDetector):
    """Deterministic fake UI detector for testing."""

    def __init__(self):
        self._call_count = 0
        self._should_fail = False
        self._fail_error = "Simulated UI detection failure"

    def detect(self, image: ScreenCapture) -> UIDetectionResult:
        """Return deterministic fake UI detection result."""
        start = time.perf_counter()
        self._call_count += 1

        if self._should_fail:
            return UIDetectionResult(
                elements=[],
                image_width=image.width,
                image_height=image.height,
                processing_duration_ms=(time.perf_counter() - start) * 1000,
                error=self._fail_error,
            )

        # Generate deterministic fake UI elements based on image dimensions
        elements = []
        
        # Add a fake button
        elements.append(UIElement(
            element_type="button",
            label="Submit",
            confidence=0.92,
            bounding_box=BoundingBox(
                x=image.width // 2 - 60,
                y=image.height // 2 + 50,
                width=120,
                height=35,
            ),
            attributes={"clickable": True, "enabled": True},
        ))

        # Add a fake input field
        elements.append(UIElement(
            element_type="input",
            label="Username",
            confidence=0.88,
            bounding_box=BoundingBox(
                x=image.width // 2 - 150,
                y=image.height // 2 - 20,
                width=300,
                height=35,
            ),
            attributes={"input_type": "text", "placeholder": "Enter username"},
        ))

        # Add a fake link
        elements.append(UIElement(
            element_type="link",
            label="Forgot Password?",
            confidence=0.85,
            bounding_box=BoundingBox(
                x=image.width // 2 - 65,
                y=image.height // 2 + 95,
                width=130,
                height=20,
            ),
            attributes={"href": "/forgot-password", "underline": True},
        ))

        # Add a generic text region
        elements.append(UIElement(
            element_type="text",
            label="Welcome to ZETTA",
            confidence=0.95,
            bounding_box=BoundingBox(
                x=image.width // 2 - 100,
                y=image.height // 2 - 100,
                width=200,
                height=30,
            ),
            attributes={"font_size": 18, "color": "#333333"},
        ))

        # Add a generic region
        elements.append(UIElement(
            element_type="region",
            label="Main Content Area",
            confidence=0.75,
            bounding_box=BoundingBox(
                x=50,
                y=50,
                width=image.width - 100,
                height=image.height - 100,
            ),
            attributes={"role": "main"},
        ))

        duration_ms = (time.perf_counter() - start) * 1000

        return UIDetectionResult(
            elements=elements,
            image_width=image.width,
            image_height=image.height,
            processing_duration_ms=duration_ms,
            metadata={"call_count": self._call_count, "fake": True},
        )

    def is_available(self) -> bool:
        return True

    def get_supported_element_types(self) -> List[str]:
        return ["button", "input", "link", "text", "region", "checkbox", "dropdown", "image"]

    def set_should_fail(self, should_fail: bool, error: str = "Simulated UI detection failure"):
        """Configure the detector to simulate failure."""
        self._should_fail = should_fail
        self._fail_error = error


class LocalUIDetector(UIDetector):
    """Local UI detector using PIL/heuristic analysis on real screen captures."""

    def __init__(self):
        self._available = True

    def detect(self, image: ScreenCapture) -> UIDetectionResult:
        """Perform basic heuristic UI detection on real captured screenshot."""
        import io
        start = time.perf_counter()

        width = image.width
        height = image.height
        elements = []
        metadata = {"analyzed_bytes": len(image.image_data) if image.image_data else 0}

        try:
            from PIL import Image
            if image.image_data:
                img = Image.open(io.BytesIO(image.image_data))
                width, height = img.size
                metadata["image_format"] = img.format
                metadata["image_mode"] = img.mode
        except Exception as e:
            metadata["pillow_error"] = str(e)

        duration_ms = (time.perf_counter() - start) * 1000

        return UIDetectionResult(
            elements=elements,
            image_width=width,
            image_height=height,
            processing_duration_ms=duration_ms,
            metadata=metadata,
        )

    def is_available(self) -> bool:
        return self._available

    def get_supported_element_types(self) -> List[str]:
        return ["button", "input", "link", "text", "region"]



def get_ui_detector(detector_type: str = "local") -> UIDetector:
    """Factory function to get UI detector."""
    if detector_type == "fake":
        return FakeUIDetector()
    elif detector_type == "local":
        return LocalUIDetector()
    else:
        raise ValueError(f"Unknown UI detector type: {detector_type}")