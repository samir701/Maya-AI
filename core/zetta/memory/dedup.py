"""ZETTA Memory Deduplication Engine."""

from typing import List, Optional, Tuple
from core.zetta.memory.embeddings import cosine_similarity, get_embedding_provider
from core.zetta.memory.repository import MemoryRepository, get_memory_repository
from core.zetta.utils.logging import get_logger
from shared.types import Memory, MemoryType

logger = get_logger("memory_dedup")


class MemoryDeduplicator:
    """Detects exact and near-duplicate memories to prevent database flooding."""

    def __init__(self, repository: Optional[MemoryRepository] = None) -> None:
        self.repo = repository or get_memory_repository()
        self.embedder = get_embedding_provider()

    def find_duplicate(
        self,
        candidate_content: str,
        target_type: Optional[MemoryType] = None,
        threshold: float = 0.90,
    ) -> Optional[Memory]:
        """Check if identical or near-duplicate memory exists in repository within the target memory_type."""
        cleaned_content = candidate_content.strip().lower()
        all_memories = self.repo.list(memory_type=target_type, limit=500)

        # 1. Exact match check
        for mem in all_memories:
            if mem.content.strip().lower() == cleaned_content:
                return mem

        # 2. Vector near-duplicate check
        cand_vec = self.embedder.embed(candidate_content)
        for mem in all_memories:
            if not mem.embedding:
                mem.embedding = self.embedder.embed(mem.content)
            sim = cosine_similarity(cand_vec, mem.embedding)
            if sim >= threshold:
                return mem

        return None

    def merge_or_create(self, new_memory: Memory, threshold: float = 0.90) -> Tuple[Memory, bool]:
        """If duplicate exists in same memory_type, merge metadata/importance; otherwise create new memory.

        Returns (Memory, is_new: bool).
        """
        existing = self.find_duplicate(new_memory.content, target_type=new_memory.memory_type, threshold=threshold)
        if existing:
            logger.info(f"Duplicate memory detected [Existing ID: {existing.id}]. Merging attributes.")
            # Merge tags & bump importance
            merged_tags = list(set(existing.tags + new_memory.tags))
            existing.tags = merged_tags
            existing.importance = min(1.0, max(existing.importance, new_memory.importance) + 0.05)
            existing.access_count += 1
            updated = self.repo.update(existing, actor="dedup_merger")
            return updated, False

        saved = self.repo.create(new_memory, actor="dedup_creator")
        return saved, True
