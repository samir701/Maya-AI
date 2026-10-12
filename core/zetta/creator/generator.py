"""ZETTA Content Metadata Generator for titles, descriptions, and tags."""

import re
from typing import List, Optional
from core.zetta.ai.brain import AIBrain, get_ai_brain
from core.zetta.creator.models import ContentMetadata
from core.zetta.utils.logging import get_logger

logger = get_logger("creator_generator")


class ContentMetadataGenerator:
    """Generates SEO titles, engaging descriptions, and optimized tags."""

    def __init__(self, brain: Optional[AIBrain] = None) -> None:
        self.brain = brain or get_ai_brain()

    def generate(
        self,
        topic: str,
        transcript: Optional[str] = None,
        platform: str = "youtube",
        category: str = "Technology",
    ) -> ContentMetadata:
        """Produce structured content metadata."""
        clean_topic = topic.strip()
        tags: List[str] = []

        # Generate keywords / tags
        words = re.findall(r"\b[A-Za-z0-9_]{3,}\b", clean_topic.lower())
        tags = list(dict.fromkeys(words))[:8]
        if platform.lower() == "youtube" and "shorts" not in tags:
            tags.append("tutorial")

        # Create title and description
        if platform.lower() == "youtube":
            title = f"Mastering {clean_topic} | Complete Guide"
            description = (
                f"Welcome to this comprehensive overview of {clean_topic}.\n\n"
                f"Key Takeaways:\n- Deep dive into core concepts\n- Hands-on demonstration\n"
            )
        elif platform.lower() == "linkedin":
            title = f"Insights on {clean_topic}"
            description = (
                f"Excited to share latest developments in {clean_topic}.\n\n"
                f"How is your team addressing this? Join the discussion below.\n"
            )
        else:
            title = f"{clean_topic} Overview"
            description = f"Essential insights and walkthrough on {clean_topic}."

        if transcript:
            description += f"\n\nTranscript Summary:\n{transcript[:300]}..."

        return ContentMetadata(
            title=title,
            description=description,
            tags=tags,
            category=category,
            target_platform=platform,
        )
