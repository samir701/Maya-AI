import re
from typing import List, Optional
from core.zetta.config import get_settings
from core.zetta.memory.embeddings import LocalVectorStore
from core.zetta.memory.repository import MemoryRepository, get_memory_repository
from core.zetta.memory.retrieval.ranking import MemoryRanker
from core.zetta.security import SecurityManager, get_security_manager
from core.zetta.utils.logging import get_logger
from shared.types import Memory, MemoryQueryResult, MemorySensitivity, MemoryType, PermissionLevel

logger = get_logger("retrieval_engine")

GENERIC_GREETING_PATTERN = re.compile(
    r"^(?:hello|hi|hey|greetings|howdy|good\s+(?:morning|afternoon|evening)|thanks|thank\s+you|okay|ok|how\s+are\s+you|what\'?s\s+up)(?:\s+zetta)?[\.!\?]*$",
    re.IGNORECASE,
)


class RetrievalEngine:
    """Retrieval pipeline for querying, scoring, security-filtering, and ranking relevant memories."""

    def __init__(
        self,
        repository: Optional[MemoryRepository] = None,
        security: Optional[SecurityManager] = None,
    ) -> None:
        self.repo = repository or get_memory_repository()
        self.security = security or get_security_manager()
        self.vector_store = LocalVectorStore()
        self.ranker = MemoryRanker()

    def query(
        self,
        query_text: str,
        limit: Optional[int] = None,
        max_sensitivity: MemorySensitivity = MemorySensitivity.NORMAL,
        min_score: Optional[float] = None,
        session_id: Optional[str] = None,
    ) -> List[MemoryQueryResult]:
        """Execute candidate retrieval, similarity scoring, security/session filtering, and composite ranking."""
        settings = get_settings()
        max_results = limit or settings.memory.retrieval_limit
        cutoff_score = min_score if min_score is not None else settings.memory.similarity_threshold
        min_sim = settings.memory.min_similarity_threshold

        is_generic_greeting = bool(GENERIC_GREETING_PATTERN.match(query_text.strip()))
        if is_generic_greeting:
            # Raise min similarity requirement for generic greetings so unrelated memories are not retrieved
            min_sim = max(min_sim, 0.85)

        # 1. Fetch candidate memories
        candidates = self.repo.list(limit=200)
        if not candidates:
            return []

        # 2. Security, Sensitivity, Assistant-Mock & Session Filtering
        allowed_sensitivity_levels = self._get_allowed_sensitivities(max_sensitivity)
        filtered_candidates: List[Memory] = []

        for m in candidates:
            if m.sensitivity not in allowed_sensitivity_levels:
                continue

            # Exclude assistant responses/mock outputs from semantic retrieval
            if m.content.startswith("Mock response to:") or m.provenance.get("role") == "assistant":
                continue

            # Enforce session isolation for short-term memories
            if m.memory_type == MemoryType.SHORT_TERM:
                mem_sess = m.provenance.get("session_id")
                if session_id is None or str(mem_sess) != str(session_id):
                    continue

            filtered_candidates.append(m)

        if not filtered_candidates:
            return []

        # 3. Vector Similarity Scoring
        similarities = self.vector_store.search_similar(query_text, filtered_candidates, top_k=len(filtered_candidates))

        # 4. Composite Scoring & Ranking
        results: List[MemoryQueryResult] = []
        for mem, sim in similarities:
            if sim < min_sim:
                # Filter out memories with negligible similarity to query
                continue
            scored_res = self.ranker.score_memory(mem, sim)
            if scored_res.score >= cutoff_score:
                results.append(scored_res)

        # 5. Sort descending by composite score
        results.sort(key=lambda r: r.score, reverse=True)

        final_results = results[:max_results]
        for r in final_results:
            self.repo.touch_access(r.memory.id)

        if final_results:
            logger.info(f"Retrieval query '{query_text[:30]}...' matched {len(final_results)} relevant memories.")
        else:
            logger.info(f"Retrieval query '{query_text[:30]}...' matched 0 relevant memories.")

        return final_results

    def _get_allowed_sensitivities(self, max_sensitivity: MemorySensitivity) -> List[MemorySensitivity]:
        sensitivity_weights = {
            MemorySensitivity.PUBLIC: 1,
            MemorySensitivity.NORMAL: 2,
            MemorySensitivity.PRIVATE: 3,
            MemorySensitivity.SENSITIVE: 4,
        }
        allowed_level = sensitivity_weights.get(max_sensitivity, 2)
        return [s for s, weight in sensitivity_weights.items() if weight <= allowed_level]

