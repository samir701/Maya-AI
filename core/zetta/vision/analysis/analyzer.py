"""Vision Analysis for ZETTA Phase 05."""

import time
from typing import Optional
from core.zetta.vision.models.results import (
    VisionAnalysisResult,
    ScreenInfo,
    ScreenCapture,
    OCRResult,
    UIDetectionResult,
)
from core.zetta.ai.providers import get_provider
from core.zetta.ai.providers.base import AIProvider
from shared.types import AIProviderType, AIRequest, AIMessage, AIRole


class VisionAnalyzer:
    """Analyzes vision results and produces structured analysis."""

    def __init__(self, ai_provider: Optional[AIProvider] = None):
        self._ai_provider = ai_provider
        self._fake_descriptions = [
            "The screen shows a desktop environment with various application windows.",
            "A text editor window is visible with code content.",
            "A web browser displaying a documentation page.",
            "A terminal window with command output.",
            "A settings dialog with configuration options.",
        ]
        self._call_count = 0

    def analyze(
        self,
        screen_info: Optional[ScreenInfo] = None,
        screen_capture: Optional[ScreenCapture] = None,
        ocr_result: Optional[OCRResult] = None,
        ui_detection_result: Optional[UIDetectionResult] = None,
    ) -> VisionAnalysisResult:
        """Analyze vision data and produce structured result."""
        start = time.perf_counter()
        self._call_count += 1

        # Build description from available data
        description_parts = []
        confidence_factors = []

        if screen_info:
            description_parts.append(
                f"Display: {screen_info.display_name} ({screen_info.width}x{screen_info.height})"
            )
            confidence_factors.append(1.0)

        if screen_capture:
            description_parts.append(
                f"Screenshot captured: {screen_capture.width}x{screen_capture.height} {screen_capture.format.upper()}"
            )
            confidence_factors.append(1.0)

        if ocr_result:
            if ocr_result.text.strip():
                text_preview = ocr_result.text[:200] + ("..." if len(ocr_result.text) > 200 else "")
                description_parts.append(f"Detected text: {text_preview}")
                confidence_factors.append(ocr_result.confidence)
            else:
                description_parts.append("No text detected in screenshot")
                confidence_factors.append(0.5)

        if ui_detection_result:
            if ui_detection_result.elements:
                element_types = {}
                for elem in ui_detection_result.elements:
                    element_types[elem.element_type] = element_types.get(elem.element_type, 0) + 1
                type_summary = ", ".join(f"{count} {typ}(s)" for typ, count in element_types.items())
                description_parts.append(f"UI elements detected: {type_summary}")
                avg_conf = sum(e.confidence for e in ui_detection_result.elements) / len(ui_detection_result.elements)
                confidence_factors.append(avg_conf)
            else:
                description_parts.append("No UI elements detected")
                confidence_factors.append(0.5)

        # If no real data, use fake description
        if not description_parts:
            description_parts.append(self._fake_descriptions[self._call_count % len(self._fake_descriptions)])
            confidence_factors.append(0.7)

        description = ". ".join(description_parts) + "."
        overall_confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.0

        # Try AI-enhanced analysis if provider available
        ai_enhanced = False
        if self._ai_provider:
            try:
                ai_description = self._enhance_with_ai(description, screen_info, ocr_result, ui_detection_result)
                if ai_description:
                    description = ai_description
                    ai_enhanced = True
            except Exception:
                pass  # Fall back to basic analysis

        duration_ms = (time.perf_counter() - start) * 1000

        return VisionAnalysisResult(
            screen_info=screen_info,
            screen_capture=screen_capture,
            ocr_result=ocr_result,
            ui_detection_result=ui_detection_result,
            description=description,
            confidence=overall_confidence,
            processing_duration_ms=duration_ms,
            metadata={
                "call_count": self._call_count,
                "ai_enhanced": ai_enhanced,
                "components_analyzed": sum([
                    screen_info is not None,
                    screen_capture is not None,
                    ocr_result is not None,
                    ui_detection_result is not None,
                ]),
            },
        )

    def _enhance_with_ai(
        self,
        base_description: str,
        screen_info: Optional[ScreenInfo],
        ocr_result: Optional[OCRResult],
        ui_detection_result: Optional[UIDetectionResult],
    ) -> Optional[str]:
        """Enhance analysis with AI provider."""
        if not self._ai_provider:
            return None

        # Build context for AI
        context = f"Screen analysis context:\n{base_description}\n\n"
        
        if ocr_result and ocr_result.text.strip():
            context += f"OCR Text:\n{ocr_result.text[:1000]}\n\n"
        
        if ui_detection_result and ui_detection_result.elements:
            context += "UI Elements:\n"
            for elem in ui_detection_result.elements[:10]:  # Limit to first 10
                context += f"- {elem.element_type}: '{elem.label}' (confidence: {elem.confidence:.2f})\n"
            context += "\n"

        prompt = f"""Analyze this screen capture data and provide a concise, high-level description of what the user is seeing. 
Focus on the main application, task, or content visible. Keep it under 3 sentences.

{context}

Description:"""

        request = AIRequest(
            messages=[AIMessage(role=AIRole.USER, content=prompt)],
            temperature=0.3,
            max_tokens=150,
        )

        try:
            response = self._ai_provider.generate(request)
            return response.text.strip()
        except Exception:
            return None


class FakeVisionAnalyzer(VisionAnalyzer):
    """Deterministic fake vision analyzer for testing."""

    def __init__(self):
        super().__init__(ai_provider=None)
        self._fake_mode = True

    def analyze(
        self,
        screen_info: Optional[ScreenInfo] = None,
        screen_capture: Optional[ScreenCapture] = None,
        ocr_result: Optional[OCRResult] = None,
        ui_detection_result: Optional[UIDetectionResult] = None,
    ) -> VisionAnalysisResult:
        """Return deterministic fake analysis."""
        # Override to ensure deterministic output
        start = time.perf_counter()
        self._call_count += 1

        description = self._fake_descriptions[(self._call_count - 1) % len(self._fake_descriptions)]
        
        if screen_info:
            description += f" Display resolution: {screen_info.width}x{screen_info.height}."
        
        if ocr_result and ocr_result.text.strip():
            description += f" Text content detected ({len(ocr_result.text)} chars)."
        
        if ui_detection_result and ui_detection_result.elements:
            description += f" {len(ui_detection_result.elements)} UI elements found."

        duration_ms = (time.perf_counter() - start) * 1000

        return VisionAnalysisResult(
            screen_info=screen_info,
            screen_capture=screen_capture,
            ocr_result=ocr_result,
            ui_detection_result=ui_detection_result,
            description=description,
            confidence=0.85,
            processing_duration_ms=duration_ms,
            metadata={"call_count": self._call_count, "fake": True},
        )


def get_vision_analyzer(use_fake: bool = False, ai_provider_type: str = "fake") -> VisionAnalyzer:
    """Factory function to get vision analyzer."""
    if use_fake:
        return FakeVisionAnalyzer()
    
    ai_provider = None
    if ai_provider_type != "none":
        try:
            ai_provider = get_provider(AIProviderType(ai_provider_type))
        except Exception:
            pass
    
    return VisionAnalyzer(ai_provider=ai_provider)