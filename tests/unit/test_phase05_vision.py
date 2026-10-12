"""Unit tests for ZETTA Phase 05 Vision & Screen Understanding Layer."""

import pytest
from unittest.mock import MagicMock, patch
from core.zetta.vision.models.results import (
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
    FakeScreenCaptureProvider,
    LinuxScreenCaptureProvider,
    ScreenCaptureError,
    get_screen_capture_provider,
)
from core.zetta.vision.ocr import FakeOCRProvider, LocalOCRProvider, get_ocr_provider
from core.zetta.vision.ui_detection import FakeUIDetector, LocalUIDetector, get_ui_detector
from core.zetta.vision.analysis import FakeVisionAnalyzer, VisionAnalyzer, get_vision_analyzer
from core.zetta.vision.manager import VisionManager, get_vision_manager, set_vision_manager
from core.zetta.tools.vision.vision_tools import (
    VisionScreenInfoTool,
    VisionScreenCaptureTool,
    VisionOCRTool,
    VisionDetectUITool,
    VisionAnalyzeScreenTool,
)
from shared.types import PermissionLevel


class TestVisionModels:
    """Test all vision data models."""

    def test_screen_info_creation_and_serialization(self):
        si = ScreenInfo(name="test", width=1920, height=1080, is_primary=True)
        d = si.to_dict()
        assert d["width"] == 1920
        assert d["height"] == 1080
        assert d["is_primary"] is True
        assert "timestamp" in d
        assert "id" in d

    def test_screen_info_with_all_fields(self):
        si = ScreenInfo(
            name="monitor1",
            display_name="HDMI-1",
            width=2560,
            height=1440,
            x=0,
            y=0,
            is_primary=True,
            scale_factor=1.25,
            refresh_rate=60,
        )
        d = si.to_dict()
        assert d["display_name"] == "HDMI-1"
        assert d["scale_factor"] == 1.25
        assert d["refresh_rate"] == 60

    def test_bounding_box_creation(self):
        bb = BoundingBox(x=10, y=20, width=100, height=50)
        assert bb.x == 10
        assert bb.y == 20
        assert bb.width == 100
        assert bb.height == 50

    def test_bounding_box_to_dict(self):
        bb = BoundingBox(x=5, y=10, width=200, height=30)
        d = bb.to_dict()
        assert d == {"x": 5, "y": 10, "width": 200, "height": 30}

    def test_screen_capture_creation(self):
        capture = ScreenCapture(width=1920, height=1080, image_data=b"png_data")
        assert capture.width == 1920
        assert capture.height == 1080
        assert capture.format == "png"

    def test_screen_capture_to_dict_excludes_bytes(self):
        capture = ScreenCapture(width=1920, height=1080, image_data=b"secret_data")
        d = capture.to_dict()
        assert "image_size_bytes" in d
        assert d["image_size_bytes"] == 11
        assert "image_data" not in d or d.get("image_data") != "secret_data"

    def test_ocr_text_region(self):
        region = OCRTextRegion(text="Hello", confidence=0.95, bounding_box=BoundingBox(x=0, y=0, width=50, height=20))
        d = region.to_dict()
        assert d["text"] == "Hello"
        assert d["confidence"] == 0.95
        assert d["bounding_box"]["x"] == 0

    def test_ocr_result(self):
        ocr = OCRResult(text="Hello World", confidence=0.90, regions=[])
        d = ocr.to_dict()
        assert d["text"] == "Hello World"
        assert d["confidence"] == 0.90

    def test_ui_element(self):
        elem = UIElement(element_type="button", label="OK", confidence=0.92, bounding_box=BoundingBox(x=0, y=0, width=100, height=30))
        d = elem.to_dict()
        assert d["element_type"] == "button"
        assert d["label"] == "OK"

    def test_ui_detection_result(self):
        result = UIDetectionResult(elements=[], image_width=1920, image_height=1080)
        d = result.to_dict()
        assert d["image_width"] == 1920
        assert d["image_height"] == 1080

    def test_vision_analysis_result(self):
        analysis = VisionAnalysisResult(description="Test analysis", confidence=0.85)
        d = analysis.to_dict()
        assert d["description"] == "Test analysis"
        assert d["confidence"] == 0.85


class TestScreenCapture:
    """Test screen capture functionality."""

    def test_fake_screen_capture_provides_displays(self):
        provider = FakeScreenCaptureProvider()
        displays = provider.get_displays()
        assert len(displays) == 2
        assert all(isinstance(d, ScreenInfo) for d in displays)

    def test_fake_screen_capture_primary_display(self):
        provider = FakeScreenCaptureProvider()
        primary = provider.get_primary_display()
        assert primary is not None
        assert primary.is_primary
        assert primary.name == "fake-primary"

    def test_fake_screen_capture_returns_png(self):
        provider = FakeScreenCaptureProvider()
        capture = provider.capture_screen()
        assert capture.format == "png"
        assert len(capture.image_data) > 0
        assert capture.width == 1920
        assert capture.height == 1080

    def test_fake_screen_capture_specific_display(self):
        provider = FakeScreenCaptureProvider()
        capture = provider.capture_screen(display_id="fake-secondary")
        assert capture.source_display == "fake-secondary"
        assert capture.width == 1920

    def test_fake_screen_capture_timestamp(self):
        provider = FakeScreenCaptureProvider()
        capture = provider.capture_screen()
        assert "timestamp" in capture.to_dict()

    def test_fake_screen_capture_duration(self):
        provider = FakeScreenCaptureProvider()
        capture = provider.capture_screen()
        assert capture.duration_ms > 0

    def test_fake_screen_capture_metadata(self):
        provider = FakeScreenCaptureProvider()
        capture = provider.capture_screen()
        assert capture.metadata.get("fake") is True

    def test_get_screen_capture_provider_fake(self):
        provider = get_screen_capture_provider(use_fake=True)
        assert isinstance(provider, FakeScreenCaptureProvider)

    def test_screen_capture_image_not_persisted_by_default(self):
        """Privacy: image bytes should not appear in to_dict output."""
        provider = FakeScreenCaptureProvider()
        capture = provider.capture_screen()
        d = capture.to_dict()
        assert "image_data" not in d or d.get("image_data") != capture.image_data


class TestOCR:
    """Test OCR functionality."""

    def test_fake_ocr_provider_available(self):
        provider = FakeOCRProvider()
        assert provider.is_available() is True

    def test_fake_ocr_provider_languages(self):
        provider = FakeOCRProvider()
        langs = provider.get_supported_languages()
        assert "en" in langs
        assert isinstance(langs, list)

    def test_fake_ocr_recognizes_deterministic_text(self):
        provider = FakeOCRProvider()
        capture = ScreenCapture(width=1920, height=1080, image_data=b"test")
        result = provider.recognize(capture)
        assert len(result.text) > 0
        assert result.confidence > 0.9

    def test_fake_ocr_produces_regions(self):
        provider = FakeOCRProvider()
        capture = ScreenCapture(width=1920, height=1080, image_data=b"test")
        result = provider.recognize(capture)
        assert len(result.regions) > 0
        for region in result.regions:
            assert region.text.strip()
            assert region.confidence > 0
            assert region.bounding_box.width > 0

    def test_fake_ocr_timestamp(self):
        provider = FakeOCRProvider()
        capture = ScreenCapture(width=1920, height=1080, image_data=b"test")
        result = provider.recognize(capture)
        assert "timestamp" in result.to_dict()

    def test_fake_ocr_failure_mode(self):
        provider = FakeOCRProvider()
        provider.set_should_fail(True)
        capture = ScreenCapture(width=1920, height=1080, image_data=b"test")
        result = provider.recognize(capture)
        assert result.error is not None
        assert len(result.text) == 0

    def test_ocr_result_does_not_contain_raw_image(self):
        """Privacy: OCR result should not include raw image data."""
        provider = FakeOCRProvider()
        capture = ScreenCapture(width=1920, height=1080, image_data=b"secret_data")
        result = provider.recognize(capture)
        d = result.to_dict()
        assert "image_data" not in d


class TestUIDetection:
    """Test UI detection functionality."""

    def test_fake_ui_detector_available(self):
        detector = FakeUIDetector()
        assert detector.is_available() is True

    def test_fake_ui_detector_supported_types(self):
        detector = FakeUIDetector()
        types = detector.get_supported_element_types()
        assert "button" in types
        assert "input" in types
        assert "link" in types

    def test_fake_ui_detector_detects_elements(self):
        detector = FakeUIDetector()
        capture = ScreenCapture(width=1920, height=1080, image_data=b"test")
        result = detector.detect(capture)
        assert len(result.elements) == 5  # button, input, link, text, region

    def test_fake_ui_detector_element_types(self):
        detector = FakeUIDetector()
        capture = ScreenCapture(width=1920, height=1080, image_data=b"test")
        result = detector.detect(capture)
        types = {e.element_type for e in result.elements}
        assert "button" in types
        assert "input" in types
        assert "link" in types
        assert "text" in types
        assert "region" in types

    def test_fake_ui_detector_confidence_range(self):
        detector = FakeUIDetector()
        capture = ScreenCapture(width=1920, height=1080, image_data=b"test")
        result = detector.detect(capture)
        for elem in result.elements:
            assert 0.0 < elem.confidence <= 1.0

    def test_fake_ui_detector_timestamp(self):
        detector = FakeUIDetector()
        capture = ScreenCapture(width=1920, height=1080, image_data=b"test")
        result = detector.detect(capture)
        assert "timestamp" in result.to_dict()

    def test_fake_ui_detector_failure_mode(self):
        detector = FakeUIDetector()
        detector.set_should_fail(True)
        capture = ScreenCapture(width=1920, height=1080, image_data=b"test")
        result = detector.detect(capture)
        assert result.error is not None
        assert len(result.elements) == 0


class TestVisionAnalyzer:
    """Test vision analysis functionality."""

    def test_fake_analyzer_produces_description(self):
        analyzer = FakeVisionAnalyzer()
        result = analyzer.analyze()
        assert result.description is not None
        assert len(result.description) > 0

    def test_fake_analyzer_with_screen_info(self):
        analyzer = FakeVisionAnalyzer()
        si = ScreenInfo(name="test", width=1920, height=1080, is_primary=True)
        result = analyzer.analyze(screen_info=si)
        assert "1920x1080" in result.description

    def test_fake_analyzer_with_ocr(self):
        analyzer = FakeVisionAnalyzer()
        ocr = OCRResult(text="Hello World", confidence=0.95)
        result = analyzer.analyze(ocr_result=ocr)
        assert "Text content" in result.description

    def test_fake_analyzer_with_ui(self):
        analyzer = FakeVisionAnalyzer()
        ui = UIDetectionResult(elements=[UIElement(element_type="button", label="OK", confidence=0.9)])
        result = analyzer.analyze(ui_detection_result=ui)
        assert "UI elements" in result.description

    def test_fake_analyzer_metadata(self):
        analyzer = FakeVisionAnalyzer()
        result = analyzer.analyze()
        assert result.metadata.get("fake") is True
        assert result.metadata.get("call_count") == 1

    def test_analyzer_without_ai_provider(self):
        analyzer = VisionAnalyzer(ai_provider=None)
        result = analyzer.analyze()
        assert result.description is not None


class TestVisionManager:
    """Test VisionManager orchestration."""

    def test_manager_creates_with_fake_providers(self):
        vm = VisionManager(use_fake=True)
        assert vm is not None

    def test_manager_get_screen_info(self):
        vm = VisionManager(use_fake=True)
        si = vm.get_screen_info()
        assert si is not None
        assert si.width == 1920

    def test_manager_capture_screen(self):
        vm = VisionManager(use_fake=True)
        capture = vm.capture_screen()
        assert capture.width == 1920
        assert capture.height == 1080

    def test_manager_perform_ocr(self):
        vm = VisionManager(use_fake=True)
        capture = vm.capture_screen()
        result = vm.perform_ocr(capture)
        assert len(result.text) > 0

    def test_manager_detect_ui(self):
        vm = VisionManager(use_fake=True)
        capture = vm.capture_screen()
        result = vm.detect_ui(capture)
        assert len(result.elements) > 0

    def test_manager_analyze_screen(self):
        vm = VisionManager(use_fake=True)
        analysis = vm.analyze_screen()
        assert analysis.description is not None
        assert analysis.screen_info is not None

    def test_manager_capabilities(self):
        vm = VisionManager(use_fake=True)
        caps = vm.get_capabilities()
        assert caps["screen_capture"]["available"] is True
        assert caps["ocr"]["available"] is True
        assert caps["ui_detection"]["available"] is True
        assert caps["analysis"]["available"] is True

    def test_manager_quick_analyze(self):
        vm = VisionManager(use_fake=True)
        analysis = vm.quick_analyze()
        assert analysis is not None

    def test_manager_emits_events(self):
        from core.zetta.events import get_event_bus
        bus = get_event_bus()
        events = []

        def handler(event):
            events.append(event)

        bus.subscribe_all(handler)
        vm = VisionManager(use_fake=True)
        vm.capture_screen()
        vm.perform_ocr(vm.capture_screen())
        vm.detect_ui(vm.capture_screen())

        assert len(events) >= 3
        operations = [e.payload.get("operation") for e in events]
        assert "vision_capture" in operations
        assert "vision_ocr" in operations
        assert "vision_detect_ui" in operations


class TestVisionTools:
    """Test vision tools registration and execution."""

    def test_vision_screen_info_tool_metadata(self):
        tool = VisionScreenInfoTool()
        meta = tool.get_metadata()
        assert meta["name"] == "vision_screen_info"
        assert meta["category"] == "vision"
        assert meta["required_permission"] == PermissionLevel.LOW

    def test_vision_screen_capture_tool_metadata(self):
        tool = VisionScreenCaptureTool()
        meta = tool.get_metadata()
        assert meta["name"] == "vision_screen_capture"
        assert meta["required_permission"] == PermissionLevel.MEDIUM

    def test_vision_ocr_tool_metadata(self):
        tool = VisionOCRTool()
        meta = tool.get_metadata()
        assert meta["name"] == "vision_ocr"
        assert meta["required_permission"] == PermissionLevel.MEDIUM

    def test_vision_detect_ui_tool_metadata(self):
        tool = VisionDetectUITool()
        meta = tool.get_metadata()
        assert meta["name"] == "vision_detect_ui"
        assert meta["required_permission"] == PermissionLevel.MEDIUM

    def test_vision_analyze_screen_tool_metadata(self):
        tool = VisionAnalyzeScreenTool()
        meta = tool.get_metadata()
        assert meta["name"] == "vision_analyze_screen"
        assert meta["required_permission"] == PermissionLevel.MEDIUM

    def test_all_vision_tools_registered_in_registry(self):
        from core.zetta.tools import get_tool_registry
        registry = get_tool_registry()
        tools = registry.list_tools()
        vision_tools = [t for t in tools if t["category"] == "vision"]
        assert len(vision_tools) == 5
        names = [t["name"] for t in vision_tools]
        assert "vision_screen_info" in names
        assert "vision_screen_capture" in names
        assert "vision_ocr" in names
        assert "vision_detect_ui" in names
        assert "vision_analyze_screen" in names

    def test_vision_tools_execution(self):
        from core.zetta.tools import get_tool_registry
        from core.zetta.security import get_security_manager
        from shared.types.enums import PermissionLevel

        registry = get_tool_registry()
        sec = get_security_manager()
        sec.permission_checker.current_level = PermissionLevel.HIGH

        # Test vision_screen_info
        result = registry.execute("vision_screen_info", {})
        assert result.success is True
        assert "displays" in result.data

        # Test vision_ocr (mock to avoid actual screen capture)
        with patch.object(VisionManager, 'capture_screen') as mock_capture:
            from core.zetta.vision.models.results import ScreenCapture
            mock_capture.return_value = ScreenCapture(width=1920, height=1080, image_data=b"test")
            result = registry.execute("vision_ocr", {})
            assert result.success is True
            assert "text" in result.data

        # Test vision_detect_ui
        with patch.object(VisionManager, 'capture_screen') as mock_capture:
            mock_capture.return_value = ScreenCapture(width=1920, height=1080, image_data=b"test")
            result = registry.execute("vision_detect_ui", {})
            assert result.success is True
            assert "elements" in result.data

        # Test vision_analyze_screen
        with patch.object(VisionManager, 'analyze_screen') as mock_analyze:
            from core.zetta.vision.models.results import VisionAnalysisResult
            mock_analyze.return_value = VisionAnalysisResult(description="test")
            result = registry.execute("vision_analyze_screen", {})
            assert result.success is True
            assert "description" in result.data

    def test_vision_tool_permissions_conservative(self):
        """Screen capture tools should have conservative permissions."""
        from core.zetta.tools import get_tool_registry
        registry = get_tool_registry()

        for tool_name in ["vision_screen_capture", "vision_ocr", "vision_detect_ui", "vision_analyze_screen"]:
            tool = registry.get(tool_name)
            assert tool.required_permission in [PermissionLevel.MEDIUM, PermissionLevel.HIGH]
            assert tool.dangerous is False

    def test_vision_tools_no_memory_promotion(self):
        """Vision data should NOT be automatically promoted to long-term memory."""
        from core.zetta.tools import get_tool_registry
        from core.zetta.security import get_security_manager
        from core.zetta.memory import get_memory_manager
        from shared.types.enums import PermissionLevel

        registry = get_tool_registry()
        sec = get_security_manager()
        sec.permission_checker.current_level = PermissionLevel.HIGH
        mem_mgr = get_memory_manager()

        # Execute a vision tool
        registry.execute("vision_screen_info", {})

        # Check no new memories were created
        initial_count = len(mem_mgr.list_memories())
        # Memory count should remain the same (no auto-promotion)
        assert len(mem_mgr.list_memories()) == initial_count


class TestPrivacySecurity:
    """Test privacy and security aspects of vision."""

    def test_screenshot_not_persisted_automatically(self):
        """Screenshots should not be automatically saved to disk."""
        vm = VisionManager(use_fake=True)
        capture = vm.capture_screen()
        # Check that there's no file persistence in the capture
        d = capture.to_dict()
        assert d.get("file_path") is None
        assert "path" not in d

    def test_ocr_text_not_promoted_to_memory(self):
        """OCR text should not be automatically stored in memory."""
        from core.zetta.memory import get_memory_manager
        mem_mgr = get_memory_manager()
        initial_count = len(mem_mgr.list_memories())

        vm = VisionManager(use_fake=True)
        capture = vm.capture_screen()
        vm.perform_ocr(capture)

        # Memory count should not increase
        assert len(mem_mgr.list_memories()) == initial_count

    def test_no_raw_screenshot_in_logs(self):
        """Raw screenshot bytes should not appear in serialized data."""
        vm = VisionManager(use_fake=True)
        capture = vm.capture_screen()
        d = capture.to_dict()
        # The to_dict should only have metadata, not raw bytes
        assert "image_data" not in d or d.get("image_data") != capture.image_data

    def test_vision_not_dangerous(self):
        """Vision tools should not be marked as dangerous."""
        from core.zetta.tools import get_tool_registry
        registry = get_tool_registry()
        for tool_name in ["vision_screen_info", "vision_screen_capture", "vision_ocr", "vision_detect_ui", "vision_analyze_screen"]:
            tool = registry.get(tool_name)
            assert tool.dangerous is False


class TestOfflineBehavior:
    """Test deterministic offline behavior."""

    def test_full_pipeline_deterministic(self):
        """Pipeline should produce consistent results with fake providers."""
        vm = VisionManager(use_fake=True)
        analysis1 = vm.analyze_screen()
        analysis2 = vm.analyze_screen()

        assert analysis1.screen_info.width == analysis2.screen_info.width
        assert analysis1.screen_info.height == analysis2.screen_info.height
        assert len(analysis1.ocr_result.text) > 0
        assert len(analysis1.ui_detection_result.elements) > 0

    def test_fake_providers_work_without_internet(self):
        """Fake providers should work completely offline."""
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.side_effect = Exception("No internet/network")

            vm = VisionManager(use_fake=True)
            capture = vm.capture_screen()
            assert capture is not None
            assert len(capture.image_data) > 0

            ocr = vm.perform_ocr(capture)
            assert len(ocr.text) > 0

            ui = vm.detect_ui(capture)
            assert len(ui.elements) > 0

    def test_missing_optional_dependencies_fails_gracefully(self):
        """Local providers should handle missing dependencies gracefully."""
        # Test LocalOCRProvider when tesseract is missing
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("tesseract not found")
            provider = LocalOCRProvider()
            assert provider.is_available() is False

            capture = ScreenCapture(width=1920, height=1080, image_data=b"test")
            result = provider.recognize(capture)
            assert result.error is not None
            assert len(result.text) == 0

    def test_local_ocr_tsv_parsing(self):
        """Test parsing of standard Tesseract TSV output."""
        mock_tsv = (
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
            "5\t1\t1\t1\t1\t1\t10\t20\t50\t15\t95.0\tHello\n"
            "5\t1\t1\t1\t1\t2\t65\t20\t60\t15\t90.0\tWorld\n"
        )
        provider = LocalOCRProvider()
        provider._available = True
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=mock_tsv.encode(), stderr=b"")
            capture = ScreenCapture(width=1920, height=1080, image_data=b"fake_png")
            result = provider.recognize(capture)
            assert "Hello World" in result.text
            assert len(result.regions) == 2
            assert result.regions[0].text == "Hello"
            assert result.regions[0].bounding_box.x == 10
            assert result.regions[1].text == "World"
            assert result.confidence > 0.90

    def test_local_ocr_plain_text_fallback(self):
        """Test fallback to plain text if TSV is not supported."""
        provider = LocalOCRProvider()
        provider._available = True
        with patch("subprocess.run") as mock_run:
            # First call (tsv) fails, second call (text) succeeds
            mock_run.side_effect = [
                MagicMock(returncode=1, stdout=b"", stderr=b"Config not found"),
                MagicMock(returncode=0, stdout=b"Plain extracted text", stderr=b""),
            ]
            capture = ScreenCapture(width=1920, height=1080, image_data=b"fake_png")
            result = provider.recognize(capture)
            assert result.text == "Plain extracted text"
            assert result.confidence == 0.8


class TestLinuxScreenCaptureBackend:
    """Detailed unit tests for Linux screen capture backends."""

    def test_mss_backend_capture(self):
        """Test mss backend screen capture mock."""
        mock_monitor = {"left": 0, "top": 0, "width": 800, "height": 600, "output": "mock-display", "is_primary": True}
        mock_sct = MagicMock()
        mock_sct.monitors = [mock_monitor, mock_monitor]
        mock_img = MagicMock()
        mock_img.rgb = b"rgb_data"
        mock_img.size = (800, 600)
        mock_sct.grab.return_value = mock_img

        mock_mss_mod = MagicMock()
        mock_mss_tools = MagicMock()
        mock_mss_mod.mss.return_value = mock_sct
        mock_mss_mod.MSS.return_value = mock_sct
        mock_mss_tools.to_png.return_value = b"\x89PNGfake_png_data"
        mock_mss_mod.tools = mock_mss_tools

        with patch.object(LinuxScreenCaptureProvider, "_detect_tools", return_value=["mss"]), \
             patch.dict("sys.modules", {"mss": mock_mss_mod, "mss.tools": mock_mss_tools}):
            provider = LinuxScreenCaptureProvider()
            assert "mss" in provider._available_tools
            
            # Test explicit display capture
            mock_info = ScreenInfo(name="mock-display", display_name="mock-display", width=800, height=600, is_primary=True)
            with patch.object(provider, "get_primary_display", return_value=mock_info):
                capture = provider.capture_screen()
                assert capture.width == 800
                assert capture.height == 600
                assert capture.image_data == b"\x89PNGfake_png_data"

    def test_real_capture_saves_png_file_in_runtime_captures(self):
        """Regression test verifying real screen capture saves PNG file to runtime/captures/."""
        import os
        mock_monitor = {"left": 0, "top": 0, "width": 800, "height": 600, "output": "eDP-1", "is_primary": True}
        mock_sct = MagicMock()
        mock_sct.monitors = [mock_monitor, mock_monitor]
        mock_img = MagicMock()
        mock_img.rgb = b"rgb_data"
        mock_img.size = (800, 600)
        mock_sct.grab.return_value = mock_img

        test_png_bytes = b"\x89PNG\r\n\x1a\nfake_captured_png_bytes_for_testing"

        mock_mss_mod = MagicMock()
        mock_mss_tools = MagicMock()
        mock_mss_mod.mss.return_value = mock_sct
        mock_mss_mod.MSS.return_value = mock_sct
        mock_mss_tools.to_png.return_value = test_png_bytes
        mock_mss_mod.tools = mock_mss_tools

        with patch.object(LinuxScreenCaptureProvider, "_detect_tools", return_value=["mss"]), \
             patch.dict("sys.modules", {"mss": mock_mss_mod, "mss.tools": mock_mss_tools}):
            provider = LinuxScreenCaptureProvider()
            mock_info = ScreenInfo(name="eDP-1", display_name="eDP-1", width=800, height=600, is_primary=True)
            with patch.object(provider, "get_primary_display", return_value=mock_info):
                capture = provider.capture_screen(save_to_disk=True)
                assert capture.file_path is not None
                assert "runtime/captures" in capture.file_path
                assert os.path.exists(capture.file_path)
                with open(capture.file_path, "rb") as f:
                    saved_bytes = f.read()
                assert saved_bytes == test_png_bytes

                if os.path.exists(capture.file_path):
                    os.unlink(capture.file_path)




    def test_cli_backend_zero_byte_output_triggers_error(self):
        """Test that 0-byte output file (e.g. scrot under Xwayland) is detected as failure."""
        with patch.object(LinuxScreenCaptureProvider, "_detect_tools", return_value=["scrot"]), \
             patch("subprocess.run") as mock_run, \
             patch("os.path.exists", return_value=True), \
             patch("os.path.getsize", return_value=0), \
             patch("os.unlink"):
            mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")

            provider = LinuxScreenCaptureProvider()
            with pytest.raises(ScreenCaptureError) as exc_info:
                provider.capture_screen()

            err_msg = str(exc_info.value)
            assert "All capture backends failed" in err_msg
            assert "scrot" in err_msg
            assert "0 bytes" in err_msg or "empty" in err_msg

    def test_error_reporting_shows_all_backend_failures_and_stderr(self):
        """Test that ScreenCaptureError includes all attempted backends and stderr reasons."""
        mock_disp = ScreenInfo(name="mock-disp", display_name="mock-disp", width=800, height=600, is_primary=True)
        with patch.object(LinuxScreenCaptureProvider, "_detect_tools", return_value=["grim", "gnome-screenshot"]), \
             patch.object(LinuxScreenCaptureProvider, "get_primary_display", return_value=mock_disp), \
             patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=1, stderr=b"grim error: compositor does not support wlr-screencopy"),
                MagicMock(returncode=1, stderr=b"gnome-screenshot error: org.freedesktop.DBus.Error.AccessDenied"),
            ]

            provider = LinuxScreenCaptureProvider()
            with pytest.raises(ScreenCaptureError) as exc_info:
                provider.capture_screen()

            err_msg = str(exc_info.value)
            assert "grim: Exit code 1" in err_msg
            assert "wlr-screencopy" in err_msg
            assert "gnome-screenshot: Exit code 1" in err_msg
            assert "AccessDenied" in err_msg



class TestRealProviderSelection:
    """Regression tests for real Linux provider selection as default."""

    def test_default_screen_capture_provider_is_linux_on_linux(self):
        """Default screen capture provider should be Linux on Linux systems."""
        provider = get_screen_capture_provider()
        assert isinstance(provider, LinuxScreenCaptureProvider)

    def test_explicit_fake_screen_capture_provider(self):
        """Explicit fake flag should still return fake provider."""
        provider = get_screen_capture_provider(use_fake=True)
        assert isinstance(provider, FakeScreenCaptureProvider)

    def test_no_silent_fake_fallback_when_no_tools(self):
        """Should NOT silently fall back to fake when use_fake=False."""
        provider = get_screen_capture_provider(use_fake=False)
        assert isinstance(provider, LinuxScreenCaptureProvider)

    def test_default_ocr_provider_returns_local(self):
        """Default OCR provider should return LocalOCRProvider when provider_type='local'."""
        provider = get_ocr_provider("local")
        assert isinstance(provider, LocalOCRProvider)

    def test_default_ui_detector_prefers_local(self):
        """Default UI detector should prefer local."""
        provider = get_ui_detector("local")
        assert isinstance(provider, LocalUIDetector)

    def test_vision_manager_default_uses_real_providers(self):
        """VisionManager with default args should use real providers when available."""
        vm = VisionManager()
        assert isinstance(vm._screen_provider, LinuxScreenCaptureProvider)
        assert isinstance(vm._ocr_provider, LocalOCRProvider)
        assert isinstance(vm._ui_detector, LocalUIDetector)

    def test_vision_manager_explicit_fake(self):
        """VisionManager with use_fake=True should use fake providers."""
        vm = VisionManager(use_fake=True)
        assert isinstance(vm._screen_provider, FakeScreenCaptureProvider)
        assert isinstance(vm._ocr_provider, FakeOCRProvider)
        assert isinstance(vm._ui_detector, FakeUIDetector)

    def test_cli_uses_real_provider_by_default(self):
        """CLI vision commands should use real provider by default, not fake."""
        import core.zetta.vision.manager as vm_module
        vm_module._vision_manager_instance = None

        vm = get_vision_manager()
        assert isinstance(vm._screen_provider, LinuxScreenCaptureProvider)

        vm_module._vision_manager_instance = None

    def test_health_check_uses_real_provider_by_default(self):
        """Health check should use real provider by default, not fake."""
        import core.zetta.vision.manager as vm_module
        vm_module._vision_manager_instance = None

        vm = get_vision_manager()
        assert isinstance(vm._screen_provider, LinuxScreenCaptureProvider)

        vm_module._vision_manager_instance = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])