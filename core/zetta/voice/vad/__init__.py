"""Voice Activity Detection Module."""

from core.zetta.voice.vad.detector import EnergyVADDetector, VADDetector
from core.zetta.voice.vad.fake import FakeVADDetector

__all__ = [
    "VADDetector",
    "EnergyVADDetector",
    "FakeVADDetector",
]
