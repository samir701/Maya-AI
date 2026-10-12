"""Display/Screen Information Module for ZETTA Phase 05."""

from typing import List, Optional
from core.zetta.vision.screen.capture import (
    ScreenCaptureProvider,
    LinuxScreenCaptureProvider,
    FakeScreenCaptureProvider,
    get_screen_capture_provider,
)
from core.zetta.vision.models.results import ScreenInfo


class DisplayManager:
    """Manages display/screen enumeration and metadata."""

    def __init__(self, capture_provider: Optional[ScreenCaptureProvider] = None):
        self._capture_provider = capture_provider or get_screen_capture_provider()

    def get_all_displays(self) -> List[ScreenInfo]:
        """Get all available displays."""
        return self._capture_provider.get_displays()

    def get_primary_display(self) -> Optional[ScreenInfo]:
        """Get primary display."""
        return self._capture_provider.get_primary_display()

    def get_display_by_id(self, display_id: str) -> Optional[ScreenInfo]:
        """Get display by ID or name."""
        for display in self.get_all_displays():
            if display.id == display_id or display.name == display_id:
                return display
        return None

    def get_display_count(self) -> int:
        """Get number of available displays."""
        return len(self.get_all_displays())

    def get_total_resolution(self) -> tuple:
        """Get total combined resolution across all displays."""
        displays = self.get_all_displays()
        if not displays:
            return (0, 0)
        
        min_x = min(d.x for d in displays)
        min_y = min(d.y for d in displays)
        max_x = max(d.x + d.width for d in displays)
        max_y = max(d.y + d.height for d in displays)
        
        return (max_x - min_x, max_y - min_y)

    def get_display_summary(self) -> dict:
        """Get summary of all displays."""
        displays = self.get_all_displays()
        return {
            "count": len(displays),
            "primary": self.get_primary_display().to_dict() if self.get_primary_display() else None,
            "displays": [d.to_dict() for d in displays],
            "total_resolution": self.get_total_resolution(),
        }


# Convenience functions
def get_display_manager(use_fake: bool = False) -> DisplayManager:
    """Get display manager instance."""
    provider = get_screen_capture_provider(use_fake=use_fake)
    return DisplayManager(provider)