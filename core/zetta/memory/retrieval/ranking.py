"""ZETTA Memory Ranking Engine."""

import math
from datetime import datetime, timezone
from typing import Dict
from core.zetta.config import get_settings
from shared.types import Memory, MemoryQueryResult, MemorySource

# Source trust mapping
SOURCE_TRUST_WEIGHTS: Dict[MemorySource, float] = {
    MemorySource.USER_EXPLICIT: 1.0,
    MemorySource.SYSTEM: 0.9,
    MemorySource.TASK: 0.85,
    MemorySource.CONVERSATION: 0.8,
    MemorySource.DERIVED: 0.7,
    MemorySource.IMPORTED: 0.6,
}


class MemoryRanker:
    """Configurable scoring engine for ranking memories across multiple signals."""

    def __init__(self) -> None:
        pass

    def compute_recency_score(self, created_at_iso: str, half_life_hours: float = 72.0) -> float:
        """Compute exponential decay recency score between 0.0 and 1.0."""
        try:
            created_dt = datetime.fromisoformat(created_at_iso)
            now_dt = datetime.now(timezone.utc)
            elapsed_hours = max(0.0, (now_dt - created_dt).total_seconds() / 3600.0)
            decay_rate = math.log(2) / max(1.0, half_life_hours)
            return math.exp(-decay_rate * elapsed_hours)
        except Exception:
            return 0.5

    def score_memory(self, memory: Memory, similarity_score: float) -> MemoryQueryResult:
        """Calculate weighted score breakdown and final composite score."""
        settings = get_settings()

        recency_score = self.compute_recency_score(memory.created_at)
        source_trust = SOURCE_TRUST_WEIGHTS.get(memory.source, 0.7)

        w_sim = settings.memory.similarity_weight
        w_imp = settings.memory.importance_weight
        w_rec = settings.memory.recency_weight
        w_conf = settings.memory.confidence_weight
        w_src = settings.memory.source_trust_weight

        composite_score = (
            (similarity_score * w_sim)
            + (memory.importance * w_imp)
            + (recency_score * w_rec)
            + (memory.confidence * w_conf)
            + (source_trust * w_src)
        )

        breakdown = {
            "similarity": round(similarity_score, 4),
            "importance": round(memory.importance, 4),
            "recency": round(recency_score, 4),
            "confidence": round(memory.confidence, 4),
            "source_trust": round(source_trust, 4),
        }

        return MemoryQueryResult(
            memory=memory,
            score=round(composite_score, 4),
            breakdown=breakdown,
        )
