from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum

class MemoryTier(IntEnum):
    L0_SENTENCE = 0
    L1_SCENE = 1
    L2_CHAPTER = 2
    L3_ARC = 3
    L4_CANON = 4
    ARCHIVE = 5

@dataclass
class MemoryRecord:
    key: str
    tier: MemoryTier
    value: str
    relevance: float = 1.0
    unresolved: bool = False

class MemoryBudget:
    """
    Deterministic selector; the LLM never gets the whole project by default.
    """
    def select(self, records: list[MemoryRecord], max_items: int = 24) -> list[MemoryRecord]:
        def score(r: MemoryRecord):
            # Tier locality must dominate raw relevance; otherwise an old Archive
            # record with a large relevance value can crowd out the current scene.
            tier_bonus = {
                MemoryTier.L0_SENTENCE: 50.0,
                MemoryTier.L1_SCENE: 40.0,
                MemoryTier.L2_CHAPTER: 30.0,
                MemoryTier.L3_ARC: 20.0,
                MemoryTier.L4_CANON: 45.0,
                MemoryTier.ARCHIVE: 0.0,
            }[r.tier]
            unresolved_bonus = 10.0 if r.unresolved else 0.0
            bounded_relevance = min(10.0, max(0.0, float(r.relevance)))
            return tier_bonus + unresolved_bonus + bounded_relevance
        return sorted(records, key=score, reverse=True)[:max_items]
