"""Webpage information models for ZETTA Phase 06."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PageInfo:
    """Represents extracted information from a loaded browser webpage."""
    url: str
    title: str = ""
    visible_text: str = ""
    status_code: int = 200
    viewport_width: int = 1280
    viewport_height: int = 800
    links_count: int = 0
    buttons_count: int = 0
    inputs_count: int = 0
    load_time_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "visible_text_snippet": (self.visible_text[:300] + "...") if len(self.visible_text) > 300 else self.visible_text,
            "text_length": len(self.visible_text),
            "status_code": self.status_code,
            "viewport": {
                "width": self.viewport_width,
                "height": self.viewport_height,
            },
            "elements_summary": {
                "links": self.links_count,
                "buttons": self.buttons_count,
                "inputs": self.inputs_count,
            },
            "load_time_ms": round(self.load_time_ms, 2),
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PageInfo":
        viewport = d.get("viewport", {})
        summary = d.get("elements_summary", {})
        return cls(
            url=d.get("url", "about:blank"),
            title=d.get("title", ""),
            visible_text=d.get("visible_text", d.get("visible_text_snippet", "")),
            status_code=d.get("status_code", 200),
            viewport_width=viewport.get("width", d.get("viewport_width", 1280)),
            viewport_height=viewport.get("height", d.get("viewport_height", 800)),
            links_count=summary.get("links", d.get("links_count", 0)),
            buttons_count=summary.get("buttons", d.get("buttons_count", 0)),
            inputs_count=summary.get("inputs", d.get("inputs_count", 0)),
            load_time_ms=d.get("load_time_ms", 0.0),
            timestamp=d.get("timestamp", time.time()),
            metadata=d.get("metadata", {}),
        )
