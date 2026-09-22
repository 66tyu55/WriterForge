from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterable

class Priority(IntEnum):
    P0 = 0  # always-light, correctness kernel
    P1 = 1  # reactive, only on relevant deltas
    P2 = 2  # scene/chapter boundary
    P3 = 3  # offline/deep audit only

@dataclass(frozen=True)
class Capability:
    name: str
    priority: Priority
    cost: int
    triggers: tuple[str, ...]
    always_on: bool = False
    cooldown_events: int = 0

@dataclass
class ScheduleDecision:
    event: str
    selected: list[str]
    total_cost: int
    skipped_budget: list[str] = field(default_factory=list)
    skipped_trigger: list[str] = field(default_factory=list)

DEFAULT_CAPABILITIES = (
    # P0: cheap and deterministic
    Capability("runtime_guard", Priority.P0, 1, ("*",), always_on=True),
    Capability("snapshot_guard", Priority.P0, 1, ("*",), always_on=True),
    Capability("delta_detector", Priority.P0, 1, ("write_state_changed","sentence_accepted","scene_boundary","chapter_boundary"), always_on=False),
    Capability("quick_continuity", Priority.P0, 2, ("sentence_accepted","scene_boundary","chapter_boundary")),

    # P1: reactive only
    Capability("xuehai_retrieval", Priority.P1, 3, ("dependency_invalidated","draft_blocked","scene_state_changed")),
    Capability("voice_guard", Priority.P1, 2, ("paragraph_boundary","scene_boundary")),
    Capability("memory_recall", Priority.P1, 2, ("scene_state_changed","scene_boundary","chapter_boundary")),
    Capability("promise_watch", Priority.P1, 2, ("scene_boundary","chapter_boundary")),
    Capability("craft_router", Priority.P1, 2, ("craft_need","dialogue_pressure","description_need","interiority_risk","narrative_restraint_risk")),

    # P2: boundary-only
    Capability("deep_continuity", Priority.P2, 5, ("scene_boundary","chapter_boundary")),
    Capability("causality_audit", Priority.P2, 5, ("scene_boundary","chapter_boundary")),
    Capability("character_audit", Priority.P2, 5, ("scene_boundary","chapter_boundary")),
    Capability("reader_experience_review", Priority.P2, 6, ("chapter_boundary",)),
    Capability("reviewer_board", Priority.P2, 8, ("chapter_boundary","revision_candidate")),
    Capability("cold_reader_review", Priority.P2, 7, ("chapter_boundary","reader_critical_scene")),
    Capability("actual_reader_critic", Priority.P2, 6, ("chapter_boundary","arc_boundary","reader_risk","major_revision")),
    Capability("craft_auditor", Priority.P2, 5, ("craft_review","major_revision")),
    Capability("literary_taste_compare", Priority.P2, 6, ("hard_literary_choice","taste_review","major_revision")),
    Capability("story_sense_router", Priority.P2, 4, ("literary_diagnosis","review_conflict")),

    # P3: offline / expensive
    Capability("full_book_audit", Priority.P3, 20, ("offline_audit",)),
    Capability("cross_work_compare", Priority.P3, 16, ("learn_offline",)),
    Capability("memory_compression", Priority.P3, 12, ("chapter_checkpoint","offline_audit")),
    Capability("structural_rewrite_impact", Priority.P3, 15, ("major_rewrite",)),
    Capability("reader_first_source_pass", Priority.P3, 18, ("learn_reader_pass",)),
    Capability("evolution_failure_cluster", Priority.P3, 8, ("evolution_review",)),
    Capability("evolution_curriculum", Priority.P3, 12, ("skill_training",)),
    Capability("evolution_promotion_gate", Priority.P3, 10, ("promotion_candidate",)),
)

class SkillScheduler:
    """
    Efficiency rule:
    - P0 is cheap and favored.
    - P1 only reacts to actual dependency/state changes.
    - P2 only at scene/chapter boundaries.
    - P3 never runs during ordinary sentence drafting.
    """
    def __init__(self, capabilities: Iterable[Capability] = DEFAULT_CAPABILITIES):
        self.capabilities = tuple(capabilities)

    def select(self, event: str, budget: int, max_priority: Priority = Priority.P3) -> ScheduleDecision:
        selected, skipped_budget, skipped_trigger = [], [], []
        total = 0
        candidates = sorted(self.capabilities, key=lambda c: (c.priority, c.cost, c.name))
        for c in candidates:
            if c.priority > max_priority:
                continue
            triggered = c.always_on or "*" in c.triggers or event in c.triggers
            if not triggered:
                skipped_trigger.append(c.name)
                continue
            if total + c.cost > budget:
                skipped_budget.append(c.name)
                continue
            selected.append(c.name)
            total += c.cost
        return ScheduleDecision(event, selected, total, skipped_budget, skipped_trigger)

    def drafting_decision(self, event: str, budget: int = 8) -> ScheduleDecision:
        # Ordinary drafting must never invoke P2/P3.
        return self.select(event, budget=budget, max_priority=Priority.P1)

    def boundary_decision(self, event: str, budget: int = 24) -> ScheduleDecision:
        return self.select(event, budget=budget, max_priority=Priority.P2)

    def offline_decision(self, event: str, budget: int = 60) -> ScheduleDecision:
        return self.select(event, budget=budget, max_priority=Priority.P3)
