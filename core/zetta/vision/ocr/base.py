"""OCR Provider Abstraction for ZETTA Phase 05."""

import time
from abc import ABC, abstractmethod
from typing import Optional
from core.zetta.vision.models.results import OCRResult, ScreenCapture


class OCRProvider(ABC):
    """Abstract base class for OCR providers."""

    @abstractmethod
    def recognize(self, image: ScreenCapture) -> OCRResult:
        """Perform OCR on the given screen capture."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the OCR provider is available/functional."""
        pass

    @abstractmethod
    def get_supported_languages(self) -> list:
        """Get list of supported language codes."""
        pass


class OCRError(Exception):
    """Exception for OCR failures."""
    pass


class FakeOCRProvider(OCRProvider):
    """Deterministic fake OCR provider for testing."""

    def __init__(self, default_text: str = "This is fake OCR text from a test image."):
        self._default_text = default_text
        self._call_count = 0
        self._should_fail = False
        self._fail_error = "Simulated OCR failure"

    def recognize(self, image: ScreenCapture) -> OCRResult:
        """Return deterministic fake OCR result."""
        import time
        start = time.perf_counter()
        self._call_count += 1

        if self._should_fail:
            return OCRResult(
                text="",
                confidence=0.0,
                processing_duration_ms=(time.perf_counter() - start) * 1000,
                image_width=image.width,
                image_height=image.height,
                error=self._fail_error,
            )

        # Generate deterministic regions based on image dimensions
        from core.zetta.vision.models.results import OCRTextRegion, BoundingBox
        regions = []
        text_lines = self._default_text.split('. ')
        y_step = max(30, image.height // max(1, len(text_lines)))
        
        for i, line in enumerate(text_lines):
            if line.strip():
                regions.append(OCRTextRegion(
                    text=line.strip() + ('.' if i < len(text_lines) - 1 else ''),
                    confidence=0.95,
                    bounding_box=BoundingBox(
                        x=50,
                        y=50 + i * y_step,
                        width=min(800, image.width - 100),
                        height=25,
                    ),
                    page_number=1,
                    line_number=i,
                    word_number=0,
                ))

        full_text = ' '.join([r.text for r in regions])
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        return OCRResult(
            text=full_text,
            regions=regions,
            language="en",
            confidence=0.95,
            processing_duration_ms=duration_ms,
            image_width=image.width,
            image_height=image.height,
            metadata={"call_count": self._call_count, "fake": True},
        )

    def is_available(self) -> bool:
        return True

    def get_supported_languages(self) -> list:
        return ["en", "fake"]

    def set_should_fail(self, should_fail: bool, error: str = "Simulated OCR failure"):
        """Configure the provider to simulate failure."""
        self._should_fail = should_fail
        self._fail_error = error


class LocalOCRProvider(OCRProvider):
    """Local OCR provider using Tesseract or similar."""

    def __init__(self, tesseract_cmd: str = "tesseract", languages: Optional[list] = None):
        self._tesseract_cmd = tesseract_cmd
        self._languages = languages or ["eng"]
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if Tesseract is available."""
        import subprocess
        try:
            result = subprocess.run(
                [self._tesseract_cmd, "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def recognize(self, image: ScreenCapture) -> OCRResult:
        """Perform OCR using Tesseract."""
        import subprocess
        import tempfile
        import os
        import time

        start = time.perf_counter()

        if not self._available:
            return OCRResult(
                text="",
                confidence=0.0,
                processing_duration_ms=(time.perf_counter() - start) * 1000,
                image_width=image.width,
                image_height=image.height,
                error="Tesseract not available",
            )

        # Save image to temp file if image_data available, or use file_path
        img_path = None
        created_temp = False

        if image.file_path and os.path.exists(image.file_path):
            img_path = image.file_path
        elif image.image_data:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                tmp_img.write(image.image_data)
                img_path = tmp_img.name
                created_temp = True
        else:
            return OCRResult(
                text="",
                confidence=0.0,
                processing_duration_ms=(time.perf_counter() - start) * 1000,
                image_width=image.width,
                image_height=image.height,
                error="No image data or valid file path provided for OCR",
            )

        try:
            # 1. Try standard tsv output first for bounding boxes and confidence
            cmd_tsv = [
                self._tesseract_cmd,
                img_path,
                "stdout",
                "-l", "+".join(self._languages),
                "--psm", "6",
                "tsv"
            ]

            result = subprocess.run(cmd_tsv, capture_output=True, timeout=30)

            if result.returncode == 0 and result.stdout:
                tsv_text = result.stdout.decode(errors="replace")
                return self._parse_tesseract_tsv(tsv_text, image, time.perf_counter() - start)

            # 2. Fallback to standard plain text output
            cmd_txt = [
                self._tesseract_cmd,
                img_path,
                "stdout",
                "-l", "+".join(self._languages),
                "--psm", "6",
            ]
            result_txt = subprocess.run(cmd_txt, capture_output=True, timeout=30)
            if result_txt.returncode == 0:
                text = result_txt.stdout.decode(errors="replace").strip()
                return OCRResult(
                    text=text,
                    confidence=0.8 if text else 0.0,
                    processing_duration_ms=(time.perf_counter() - start) * 1000,
                    image_width=image.width,
                    image_height=image.height,
                )

            err_msg = result_txt.stderr.decode(errors="replace") if result_txt.stderr else "Tesseract OCR failed"
            return OCRResult(
                text="",
                confidence=0.0,
                processing_duration_ms=(time.perf_counter() - start) * 1000,
                image_width=image.width,
                image_height=image.height,
                error=err_msg,
            )

        except subprocess.TimeoutExpired:
            return OCRResult(
                text="",
                confidence=0.0,
                processing_duration_ms=30000,
                image_width=image.width,
                image_height=image.height,
                error="OCR timeout",
            )
        except Exception as e:
            return OCRResult(
                text="",
                confidence=0.0,
                processing_duration_ms=(time.perf_counter() - start) * 1000,
                image_width=image.width,
                image_height=image.height,
                error=str(e),
            )
        finally:
            if created_temp and img_path:
                try:
                    os.unlink(img_path)
                except Exception:
                    pass

    def _parse_tesseract_tsv(self, tsv_output: str, image: ScreenCapture, duration: float) -> OCRResult:
        """Parse Tesseract TSV output into OCRResult with bounding boxes."""
        from core.zetta.vision.models.results import OCRTextRegion, BoundingBox

        regions = []
        lines_text = []
        current_line = []
        current_line_num = -1

        for line in tsv_output.strip().split("\n")[1:]:  # skip header
            parts = line.split("\t")
            if len(parts) >= 12:
                line_num = int(parts[4]) if parts[4].isdigit() else 0
                word_num = int(parts[5]) if parts[5].isdigit() else 0
                left = int(parts[6]) if parts[6].isdigit() else 0
                top = int(parts[7]) if parts[7].isdigit() else 0
                width = int(parts[8]) if parts[8].isdigit() else 0
                height = int(parts[9]) if parts[9].isdigit() else 0
                conf_str = parts[10]
                try:
                    conf_val = float(conf_str)
                    conf = max(0.0, min(1.0, conf_val / 100.0)) if conf_val >= 0 else 0.0
                except ValueError:
                    conf = 0.0
                word = parts[11].strip()

                if word:
                    regions.append(OCRTextRegion(
                        text=word,
                        confidence=conf,
                        bounding_box=BoundingBox(x=left, y=top, width=width, height=height),
                        page_number=1,
                        line_number=line_num,
                        word_number=word_num,
                    ))
                    if current_line_num == line_num:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines_text.append(" ".join(current_line))
                        current_line = [word]
                        current_line_num = line_num

        if current_line:
            lines_text.append(" ".join(current_line))

        full_text = "\n".join(lines_text)
        avg_confidence = sum(r.confidence for r in regions) / len(regions) if regions else 0.0

        return OCRResult(
            text=full_text,
            regions=regions,
            language="+".join(self._languages),
            confidence=avg_confidence,
            processing_duration_ms=duration * 1000,
            image_width=image.width,
            image_height=image.height,
        )

    def _parse_tesseract_json(self, data: dict, image: ScreenCapture, duration: float) -> OCRResult:
        """Parse Tesseract JSON output into OCRResult."""
        from core.zetta.vision.models.results import OCRTextRegion, BoundingBox
        
        regions = []
        full_text_parts = []
        
        # Tesseract JSON structure has 'pages' -> 'blocks' -> 'paragraphs' -> 'lines' -> 'words'
        # We'll extract text from lines
        pages = data.get("pages", [])
        for page_idx, page in enumerate(pages):
            blocks = page.get("blocks", [])
            for block in blocks:
                paragraphs = block.get("paragraphs", [])
                for para in paragraphs:
                    lines = para.get("lines", [])
                    for line_idx, line in enumerate(lines):
                        words = line.get("words", [])
                        line_text = " ".join([w.get("text", "") for w in words if w.get("text", "").strip()])
                        
                        if line_text.strip():
                            bbox = line.get("boundingBox", {})
                            vertices = bbox.get("vertices", [])
                            
                            if len(vertices) >= 4:
                                x = min(v.get("x", 0) for v in vertices)
                                y = min(v.get("y", 0) for v in vertices)
                                max_x = max(v.get("x", 0) for v in vertices)
                                max_y = max(v.get("y", 0) for v in vertices)
                                width = max_x - x
                                height = max_y - y
                            else:
                                x = line.get("x", 0)
                                y = line.get("y", 0)
                                width = line.get("width", 0)
                                height = line.get("height", 0)
                            
                            confidence = line.get("confidence", 0.8)
                            
                            region = OCRTextRegion(
                                text=line_text.strip(),
                                confidence=confidence,
                                bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
                                page_number=page_idx + 1,
                                line_number=line_idx,
                                word_number=0,
                            )
                            regions.append(region)
                            full_text_parts.append(line_text.strip())

        full_text = "\n".join(full_text_parts)
        avg_confidence = sum(r.confidence for r in regions) / len(regions) if regions else 0.0
        
        return OCRResult(
            text=full_text,
            regions=regions,
            language="+".join(self._languages),
            confidence=avg_confidence,
            processing_duration_ms=duration * 1000,
            image_width=image.width,
            image_height=image.height,
        )

    def is_available(self) -> bool:
        return self._available

    def get_supported_languages(self) -> list:
        if not self._available:
            return []
        try:
            import subprocess
            result = subprocess.run(
                [self._tesseract_cmd, "--list-langs"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                langs = result.stdout.strip().split('\n')[1:]  # Skip header
                return [l.strip() for l in langs if l.strip()]
        except Exception:
            pass
        return self._languages


def get_ocr_provider(provider_type: str = "local", **kwargs) -> OCRProvider:
    """Factory function to get OCR provider."""
    if provider_type == "fake":
        return FakeOCRProvider(**kwargs)
    elif provider_type == "local" or provider_type == "tesseract":
        return LocalOCRProvider(**kwargs)
    else:
        raise ValueError(f"Unknown OCR provider type: {provider_type}")