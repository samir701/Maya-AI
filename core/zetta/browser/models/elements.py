"""Interactive Web Element Models for ZETTA Phase 06."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ElementType(str, Enum):
    BUTTON = "button"
    INPUT = "input"
    LINK = "link"
    SELECT = "select"
    TEXTAREA = "textarea"
    IMAGE = "image"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    FORM = "form"
    OTHER = "other"


@dataclass
class ElementLocation:
    """Bounding box coordinates of an interactive element on the page."""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ElementLocation":
        return cls(
            x=d.get("x", 0),
            y=d.get("y", 0),
            width=d.get("width", 0),
            height=d.get("height", 0),
        )


@dataclass
class WebElement:
    """Represents an interactive DOM element detected on a webpage."""
    element_id: str
    tag_name: str
    element_type: ElementType = ElementType.OTHER
    text: str = ""
    selector: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)
    location: ElementLocation = field(default_factory=ElementLocation)
    is_visible: bool = True
    is_enabled: bool = True
    value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "tag_name": self.tag_name,
            "element_type": self.element_type.value,
            "text": self.text,
            "selector": self.selector,
            "attributes": self.attributes,
            "location": self.location.to_dict(),
            "is_visible": self.is_visible,
            "is_enabled": self.is_enabled,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WebElement":
        loc_d = d.get("location", {})
        loc = ElementLocation.from_dict(loc_d) if isinstance(loc_d, dict) else ElementLocation()
        etype_val = d.get("element_type", "other")
        try:
            etype = ElementType(etype_val)
        except Exception:
            etype = ElementType.OTHER
        return cls(
            element_id=d["element_id"],
            tag_name=d["tag_name"],
            element_type=etype,
            text=d.get("text", ""),
            selector=d.get("selector", ""),
            attributes=d.get("attributes", {}),
            location=loc,
            is_visible=d.get("is_visible", True),
            is_enabled=d.get("is_enabled", True),
            value=d.get("value"),
        )

    def to_summary(self) -> str:
        ident = self.attributes.get("id") or self.attributes.get("name") or self.selector or self.element_id
        label = self.text.strip() or self.attributes.get("placeholder") or self.attributes.get("aria-label") or ""
        return f"[{self.element_type.value.upper()}] '{label}' (id={ident}) at ({self.location.x},{self.location.y})"
