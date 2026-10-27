from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Iterable, Mapping

from .evolution import OptionalExecutionPermit, SkillRegistry

from .lane_scheduler import (
    Lane, DirtyDomain, EventEnvelope, EventBatcher,
    LaneTask, LaneTaskQueue,
)
from .event_priorities import priority_for_event


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
    lane: Lane = Lane.REACTIVE
    domains: DirtyDomain = DirtyDomain.NONE
    timeout_ticks: int = 0
    cancel_if_stale: bool = True
    # Deliberate opt-in ONLY; never reinterpret old core capabilities as habits.
    optional_habit: bool = False


@dataclass
class ScheduleDecision:
    event: str
    selected: list[str]
    total_cost: int
    skipped_budget: list[str] = field(default_factory=list)
    skipped_trigger: list[str] = field(default_factory=list)
    skipped_dirty: list[str] = field(default_factory=list)
    deferred: list[str] = field(default_factory=list)
    dropped_stale: list[str] = field(default_factory=list)
    skipped_authority: dict[str, str] = field(default_factory=dict)
    dropped_unauthorized: list[str] = field(default_factory=list)
    # Execution receipts are internal revalidation bindings, not permissions.
    optional_receipts: dict[str, str] = field(default_factory=dict)


DEFAULT_CAPABILITIES = (
    # P0 / app shell: cheap and deterministic
    Capability("runtime_guard", Priority.P0, 1, ("*",), always_on=True,
               lane=Lane.SYNC, domains=DirtyDomain.RUNTIME, cancel_if_stale=False),
    Capability("snapshot_guard", Priority.P0, 1, ("*",), always_on=True,
               lane=Lane.SYNC, domains=DirtyDomain.SNAPSHOT, cancel_if_stale=False),
    Capability("delta_detector", Priority.P0, 1,
               ("write_state_changed", "sentence_accepted", "scene_boundary", "chapter_boundary"),
               lane=Lane.DRAFT, domains=DirtyDomain.CONTINUITY | DirtyDomain.CHARACTER |
               DirtyDomain.CAUSALITY | DirtyDomain.MEMORY | DirtyDomain.PROMISE |
               DirtyDomain.READER | DirtyDomain.CRAFT | DirtyDomain.WORLD),
    Capability("quick_continuity", Priority.P0, 2,
               ("sentence_accepted", "scene_boundary", "chapter_boundary"),
               lane=Lane.DRAFT, domains=DirtyDomain.CONTINUITY),

    # P1 / lazy feature chunks
    Capability("xuehai_retrieval", Priority.P1, 3,
               ("dependency_invalidated", "draft_blocked", "scene_state_changed"),
               lane=Lane.REACTIVE, domains=DirtyDomain.XUEHAI | DirtyDomain.CRAFT |
               DirtyDomain.WORLD | DirtyDomain.CHARACTER),
    Capability("voice_guard", Priority.P1, 2, ("paragraph_boundary", "scene_boundary"),
               lane=Lane.REACTIVE, domains=DirtyDomain.VOICE),
    Capability("memory_recall", Priority.P1, 2,
               ("scene_state_changed", "scene_boundary", "chapter_boundary"),
               lane=Lane.REACTIVE, domains=DirtyDomain.MEMORY),
    Capability("promise_watch", Priority.P1, 2, ("scene_boundary", "chapter_boundary"),
               lane=Lane.REACTIVE, domains=DirtyDomain.PROMISE),
    Capability("craft_router", Priority.P1, 2,
               ("craft_need", "dialogue_pressure", "description_need", "interiority_risk", "narrative_restraint_risk"),
               lane=Lane.REACTIVE, domains=DirtyDomain.CRAFT),

    # P2 / route-boundary chunks. Dirty-domain routing chooses which deep checker loads.
    Capability("deep_continuity", Priority.P2, 5, ("scene_boundary", "chapter_boundary"),
               lane=Lane.BOUNDARY, domains=DirtyDomain.CONTINUITY, timeout_ticks=3),
    Capability("causality_audit", Priority.P2, 5, ("scene_boundary", "chapter_boundary"),
               lane=Lane.BOUNDARY, domains=DirtyDomain.CAUSALITY, timeout_ticks=3),
    Capability("character_audit", Priority.P2, 5, ("scene_boundary", "chapter_boundary"),
               lane=Lane.BOUNDARY, domains=DirtyDomain.CHARACTER, timeout_ticks=3),
    Capability("reader_experience_review", Priority.P2, 6, ("chapter_boundary",),
               lane=Lane.BOUNDARY, domains=DirtyDomain.READER, timeout_ticks=4),
    Capability("reviewer_board", Priority.P2, 8, ("chapter_boundary", "revision_candidate"),
               lane=Lane.TRANSITION, domains=DirtyDomain.READER | DirtyDomain.CRAFT |
               DirtyDomain.CHARACTER | DirtyDomain.CAUSALITY, timeout_ticks=8),
    Capability("cold_reader_review", Priority.P2, 7, ("chapter_boundary", "reader_critical_scene"),
               lane=Lane.TRANSITION, domains=DirtyDomain.READER, timeout_ticks=6),
    Capability("actual_reader_critic", Priority.P2, 6,
               ("chapter_boundary", "arc_boundary", "reader_risk", "major_revision"),
               lane=Lane.TRANSITION, domains=DirtyDomain.READER, timeout_ticks=8),
    Capability("craft_auditor", Priority.P2, 5, ("craft_review", "major_revision"),
               lane=Lane.TRANSITION, domains=DirtyDomain.CRAFT, timeout_ticks=8),
    Capability("literary_taste_compare", Priority.P2, 6,
               ("hard_literary_choice", "taste_review", "major_revision"),
               lane=Lane.TRANSITION, domains=DirtyDomain.TASTE, timeout_ticks=10),
    Capability("story_sense_router", Priority.P2, 4, ("literary_diagnosis", "review_conflict"),
               lane=Lane.BOUNDARY, domains=DirtyDomain.READER | DirtyDomain.CRAFT |
               DirtyDomain.CHARACTER | DirtyDomain.CAUSALITY | DirtyDomain.CONTINUITY),

    # P3 / background workers
    Capability("full_book_audit", Priority.P3, 20, ("offline_audit",),
               lane=Lane.OFFLINE, domains=DirtyDomain.LEARN | DirtyDomain.READER |
               DirtyDomain.CHARACTER | DirtyDomain.CAUSALITY, timeout_ticks=20),
    Capability("cross_work_compare", Priority.P3, 16, ("learn_offline",),
               lane=Lane.OFFLINE, domains=DirtyDomain.LEARN, timeout_ticks=20),
    Capability("memory_compression", Priority.P3, 12, ("chapter_checkpoint", "offline_audit"),
               lane=Lane.OFFLINE, domains=DirtyDomain.MEMORY, timeout_ticks=16),
    Capability("structural_rewrite_impact", Priority.P3, 15, ("major_rewrite",),
               lane=Lane.OFFLINE, domains=DirtyDomain.CAUSALITY | DirtyDomain.CHARACTER |
               DirtyDomain.CONTINUITY, timeout_ticks=16),
    Capability("reader_first_source_pass", Priority.P3, 18, ("learn_reader_pass",),
               lane=Lane.OFFLINE, domains=DirtyDomain.LEARN | DirtyDomain.READER, timeout_ticks=20),
    Capability("evolution_failure_cluster", Priority.P3, 8, ("evolution_review",),
               lane=Lane.OFFLINE, domains=DirtyDomain.EVOLUTION, timeout_ticks=24),
    Capability("evolution_curriculum", Priority.P3, 12, ("skill_training",),
               lane=Lane.OFFLINE, domains=DirtyDomain.EVOLUTION, timeout_ticks=24),
    Capability("evolution_promotion_gate", Priority.P3, 10, ("promotion_candidate",),
               lane=Lane.OFFLINE, domains=DirtyDomain.EVOLUTION, timeout_ticks=24),
)


DEFAULT_EVENT_DIRTY: dict[str, DirtyDomain] = {
    "sentence_accepted": DirtyDomain.CONTINUITY,
    "write_state_changed": DirtyDomain.CONTINUITY,
    "paragraph_boundary": DirtyDomain.VOICE,
    "scene_state_changed": DirtyDomain.MEMORY | DirtyDomain.XUEHAI,
    "dependency_invalidated": DirtyDomain.XUEHAI,
    "draft_blocked": DirtyDomain.XUEHAI,
    "craft_need": DirtyDomain.CRAFT,
    "dialogue_pressure": DirtyDomain.CRAFT,
    "description_need": DirtyDomain.CRAFT,
    "interiority_risk": DirtyDomain.CRAFT,
    "narrative_restraint_risk": DirtyDomain.CRAFT,
    # Safe fallback: boundary itself does not imply every deep domain is dirty.
    "scene_boundary": DirtyDomain.CONTINUITY | DirtyDomain.CAUSALITY | DirtyDomain.CHARACTER | DirtyDomain.MEMORY | DirtyDomain.PROMISE | DirtyDomain.VOICE,
    "chapter_boundary": DirtyDomain.MEMORY | DirtyDomain.PROMISE | DirtyDomain.READER,
    "reader_critical_scene": DirtyDomain.READER,
    "reader_risk": DirtyDomain.READER,
    "arc_boundary": DirtyDomain.READER,
    "craft_review": DirtyDomain.CRAFT,
    "hard_literary_choice": DirtyDomain.TASTE,
    "taste_review": DirtyDomain.TASTE,
    "literary_diagnosis": DirtyDomain.READER | DirtyDomain.CRAFT | DirtyDomain.CHARACTER |
                          DirtyDomain.CAUSALITY | DirtyDomain.CONTINUITY,
    "review_conflict": DirtyDomain.READER | DirtyDomain.CRAFT | DirtyDomain.CHARACTER |
                       DirtyDomain.CAUSALITY | DirtyDomain.CONTINUITY,
    "learn_reader_pass": DirtyDomain.LEARN | DirtyDomain.READER,
    "learn_offline": DirtyDomain.LEARN,
    "evolution_review": DirtyDomain.EVOLUTION,
    "skill_training": DirtyDomain.EVOLUTION,
    "promotion_candidate": DirtyDomain.EVOLUTION,
}


class SkillScheduler:
    """
    V15 hybrid scheduler.

    Compatibility methods (`drafting_decision`, `boundary_decision`,
    `offline_decision`) remain stateless. Production runtimes can use
    `enqueue_event` + `flush_pending` to gain event batching, stale-work
    cancellation, starvation protection and transition yielding.
    """

    def __init__(
        self, capabilities: Iterable[Capability] = DEFAULT_CAPABILITIES, *,
        registry: SkillRegistry | None = None,
        optional_permits: Mapping[str, OptionalExecutionPermit] | None = None,
        execution_verifier_key: bytes | None = None,
        artifact_loader: Callable[[str], bytes] | None = None,
        host_capabilities: Callable[[], Iterable[str]] | None = None,
        enable_optional_habits: bool = False,
    ):
        self.capabilities = tuple(capabilities)
        self.event_batcher = EventBatcher()
        self.task_queue = LaneTaskQueue()
        # A sealed core cannot be disabled or shadowed by naming an optional
        # Skill after it. The registry is not a dependency of the old kernel.
        core_names = frozenset(c.name for c in DEFAULT_CAPABILITIES)
        seen: dict[str, Capability] = {}
        for cap in self.capabilities:
            if cap.optional_habit and cap.name in core_names:
                raise ValueError("OPTIONAL_HABIT_CANNOT_SHADOW_CORE")
            if cap.name in seen and (cap.optional_habit or seen[cap.name].optional_habit):
                raise ValueError("OPTIONAL_HABIT_DUPLICATE_CAPABILITY")
            seen[cap.name] = cap
        self._caps_by_name = seen
        self._has_optional = any(c.optional_habit for c in self.capabilities)
        self.registry = registry
        self._optional_permits = dict(optional_permits or {})
        self._execution_verifier_key = execution_verifier_key
        self._artifact_loader = artifact_loader
        self._host_capabilities = host_capabilities
        self._enable_optional_habits = enable_optional_habits

    def _optional_reason(self, cap: Capability) -> str | None:
        if not cap.optional_habit:
            return None
        if not self._enable_optional_habits:
            return "OPTIONAL_HABIT_DISABLED"
        if not isinstance(self.registry, SkillRegistry):
            return "OPTIONAL_HABIT_AUTHORITY_UNAVAILABLE"
        permit = self._optional_permits.get(cap.name)
        if permit is None:
            return "OPTIONAL_HABIT_APPROVAL_MISSING"
        if not isinstance(permit, OptionalExecutionPermit) or permit.name != cap.name:
            return "OPTIONAL_HABIT_ATTESTATION_INVALID"
        if self._artifact_loader is None or not callable(self._artifact_loader):
            return "OPTIONAL_HABIT_CAPSULE_UNAVAILABLE"
        try:
            # Re-read the actual approved artifact; don't trust the descriptor
            # or a digest echoed by the host's model.
            raw = self._artifact_loader(cap.name)
        except Exception:
            return "OPTIONAL_HABIT_CAPSULE_UNAVAILABLE"
        try:
            rights = (self._host_capabilities() if callable(self._host_capabilities)
                      else ())
        except Exception:
            return "OPTIONAL_HABIT_HOST_PERMISSION_MISSING"
        return self.registry.optional_execution_reason(
            permit, verifier_key=self._execution_verifier_key,
            capsule_bytes=raw, host_capabilities=rights)

    def _optional_binding(self, name: str) -> str:
        permit = self._optional_permits.get(name)
        return permit.fingerprint() if isinstance(permit, OptionalExecutionPermit) else ""

    def _optional_receipts(self, names: Iterable[str]) -> dict[str, str]:
        return {name: self._optional_binding(name) for name in names
                if name in self._caps_by_name and
                self._caps_by_name[name].optional_habit}

    def execute_optional(
        self, decision: ScheduleDecision, name: str, executor: Callable[[], object],
    ) -> object:
        """Only entry for invoking a selected *optional* habit through WF.

        The selection receipt is never enough: trust, artifact, permissions and
        dependencies must still be valid just before the host callback starts.
        This cannot sandbox arbitrary third-party Python or stop a callback
        already running when an external process revokes its permissions.
        """
        cap = self._caps_by_name.get(name)
        if (not isinstance(decision, ScheduleDecision) or
                cap is None or not cap.optional_habit or
                name not in decision.selected or
                name not in decision.optional_receipts or
                not callable(executor)):
            raise PermissionError("OPTIONAL_HABIT_DISPATCH_NOT_SELECTED")
        reason = self._optional_reason(cap)
        if reason is not None:
            raise PermissionError(reason)
        if decision.optional_receipts[name] != self._optional_binding(name):
            raise PermissionError("OPTIONAL_HABIT_DISPATCH_BINDING_CHANGED")
        return executor()

    @staticmethod
    def _allowed_for_priority(max_priority: Priority) -> Lane:
        lanes = Lane.SYNC | Lane.DRAFT
        if max_priority >= Priority.P1:
            lanes |= Lane.REACTIVE
        if max_priority >= Priority.P2:
            lanes |= Lane.BOUNDARY | Lane.TRANSITION
        if max_priority >= Priority.P3:
            lanes |= Lane.OFFLINE | Lane.IDLE
        return lanes

    @staticmethod
    def _event_dirty(event: str, dirty_domains: DirtyDomain | None) -> DirtyDomain:
        return DEFAULT_EVENT_DIRTY.get(event, DirtyDomain.NONE) if dirty_domains is None else dirty_domains

    @staticmethod
    def _triggered(capability: Capability, event_names: set[str]) -> bool:
        return capability.always_on or "*" in capability.triggers or bool(event_names.intersection(capability.triggers))

    @staticmethod
    def _dirty_relevant(capability: Capability, dirty: DirtyDomain) -> bool:
        if capability.always_on:
            return True
        if capability.domains == DirtyDomain.NONE or dirty == DirtyDomain.NONE:
            return True
        return bool(capability.domains & dirty)

    def _matching(
        self,
        *,
        event_names: set[str],
        dirty: DirtyDomain,
        max_priority: Priority,
    ) -> tuple[list[Capability], list[str], list[str], dict[str, str]]:
        selected: list[Capability] = []
        skipped_trigger: list[str] = []
        skipped_dirty: list[str] = []
        skipped_authority: dict[str, str] = {}
        for c in self.capabilities:
            if c.priority > max_priority:
                continue
            if not self._triggered(c, event_names):
                skipped_trigger.append(c.name)
                continue
            if not self._dirty_relevant(c, dirty):
                skipped_dirty.append(c.name)
                continue
            reason = self._optional_reason(c)
            if reason is not None:
                skipped_authority[c.name] = reason
                continue
            selected.append(c)
        return selected, skipped_trigger, skipped_dirty, skipped_authority

    @staticmethod
    def _static_rank(c: Capability, dirty: DirtyDomain) -> tuple[int, int, int, int, str]:
        lane_rank = {
            Lane.SYNC: 0, Lane.DRAFT: 1, Lane.REACTIVE: 2,
            Lane.BOUNDARY: 3, Lane.TRANSITION: 4, Lane.OFFLINE: 5, Lane.IDLE: 6,
        }.get(c.lane, 7)
        relevance = int((c.domains & dirty).bit_count()) if dirty else 0
        return (c.priority, lane_rank, -relevance, c.cost, c.name)

    def select(
        self,
        event: str,
        budget: int,
        max_priority: Priority = Priority.P3,
        *,
        dirty_domains: DirtyDomain | None = None,
    ) -> ScheduleDecision:
        dirty = self._event_dirty(event, dirty_domains)
        matches, skipped_trigger, skipped_dirty, skipped_authority = self._matching(
            event_names={event}, dirty=dirty, max_priority=max_priority
        )
        matches.sort(key=lambda c: self._static_rank(c, dirty))
        selected: list[str] = []
        skipped_budget: list[str] = []
        total = 0
        for c in matches:
            if total + c.cost > budget:
                skipped_budget.append(c.name)
                continue
            selected.append(c.name)
            total += c.cost
        return ScheduleDecision(
            event, selected, total,
            skipped_budget=skipped_budget,
            skipped_trigger=skipped_trigger,
            skipped_dirty=skipped_dirty,
            skipped_authority=skipped_authority,
            optional_receipts=self._optional_receipts(selected),
        )

    def batch_decision(
        self,
        events: Iterable[EventEnvelope],
        *,
        budget: int,
        max_priority: Priority = Priority.P3,
    ) -> ScheduleDecision:
        batcher = EventBatcher()
        for event in events:
            batcher.push(event)
        batches = batcher.flush()
        if not batches:
            return ScheduleDecision("batch", [], 0)

        event_names: set[str] = set()
        dirty = DirtyDomain.NONE
        for batch in batches:
            event_names.update(batch.names)
            dirty |= batch.dirty
        matches, skipped_trigger, skipped_dirty, skipped_authority = self._matching(
            event_names=event_names, dirty=dirty, max_priority=max_priority
        )
        matches.sort(key=lambda c: self._static_rank(c, dirty))
        selected, skipped_budget = [], []
        total = 0
        for c in matches:
            if total + c.cost > budget:
                skipped_budget.append(c.name)
                continue
            selected.append(c.name)
            total += c.cost
        return ScheduleDecision(
            "batch:" + "+".join(sorted(event_names)), selected, total,
            skipped_budget=skipped_budget,
            skipped_trigger=skipped_trigger,
            skipped_dirty=skipped_dirty,
            skipped_authority=skipped_authority,
            optional_receipts=self._optional_receipts(selected),
        )

    def enqueue_event(self, event: EventEnvelope) -> None:
        # Business callers may omit priority. Keep the public event API small and
        # infer urgency here instead of forcing every caller to know lane details.
        if event.priority is None:
            event = EventEnvelope(
                name=event.name,
                scope=event.scope,
                dirty=event.dirty,
                generation=event.generation,
                transition_id=event.transition_id,
                priority=int(priority_for_event(event.name)),
            )
        self.event_batcher.push(event)

    def flush_pending(
        self,
        *,
        budget: int,
        now_tick: int,
        max_priority: Priority = Priority.P3,
    ) -> ScheduleDecision:
        batches = self.event_batcher.flush()
        skipped_trigger: list[str] = []
        skipped_dirty: list[str] = []
        skipped_authority: dict[str, str] = {}
        for batch in batches:
            self.task_queue.advance_generation(batch.scope, batch.generation)
            event_names = set(batch.names)
            matches, st, sd, sa = self._matching(
                event_names=event_names,
                dirty=batch.dirty,
                max_priority=max_priority,
            )
            skipped_trigger.extend(st)
            skipped_dirty.extend(sd)
            skipped_authority.update(sa)
            fingerprint = f"{'+'.join(sorted(event_names))}:{int(batch.dirty)}"
            transition_id = batch.transition_ids[-1] if batch.transition_ids else None
            for c in matches:
                self.task_queue.enqueue(LaneTask(
                    name=c.name,
                    lane=c.lane,
                    cost=c.cost,
                    scope=batch.scope,
                    generation=batch.generation,
                    dirty=c.domains & batch.dirty,
                    fingerprint=fingerprint,
                    timeout_ticks=c.timeout_ticks,
                    transition_id=transition_id,
                    cancel_if_stale=c.cancel_if_stale,
                    source_priority=batch.priority,
                    execution_grant_id=(self._optional_binding(c.name)
                                        if c.optional_habit else ""),
                ), now_tick=now_tick)

        def authorize_queued(task: LaneTask) -> bool:
            cap = self._caps_by_name.get(task.name)
            if cap is None:
                skipped_authority[task.name] = "OPTIONAL_HABIT_UNKNOWN_QUEUED_TASK"
                return False
            if not cap.optional_habit:
                return True  # Historical core scheduling is unchanged.
            reason = self._optional_reason(cap)
            if reason is None and (
                not task.execution_grant_id or
                task.execution_grant_id != self._optional_binding(task.name)
            ):
                reason = "OPTIONAL_HABIT_QUEUED_BINDING_CHANGED"
            if reason is not None:
                skipped_authority[task.name] = reason
                return False
            return True

        out = self.task_queue.flush(
            budget=budget,
            now_tick=now_tick,
            allowed=self._allowed_for_priority(max_priority),
            authorize_task=authorize_queued if self._has_optional else None,
        )
        return ScheduleDecision(
            "pending",
            [x.name for x in out.selected],
            out.spent,
            skipped_trigger=skipped_trigger,
            skipped_dirty=skipped_dirty,
            deferred=list(out.deferred),
            dropped_stale=list(out.dropped_stale),
            skipped_authority=skipped_authority,
            dropped_unauthorized=list(out.dropped_unauthorized),
            optional_receipts=self._optional_receipts(x.name for x in out.selected),
        )

    def drafting_decision(
        self, event: str, budget: int = 8, *, dirty_domains: DirtyDomain | None = None
    ) -> ScheduleDecision:
        return self.select(event, budget=budget, max_priority=Priority.P1, dirty_domains=dirty_domains)

    def boundary_decision(
        self, event: str, budget: int = 24, *, dirty_domains: DirtyDomain | None = None
    ) -> ScheduleDecision:
        return self.select(event, budget=budget, max_priority=Priority.P2, dirty_domains=dirty_domains)

    def offline_decision(
        self, event: str, budget: int = 60, *, dirty_domains: DirtyDomain | None = None
    ) -> ScheduleDecision:
        return self.select(event, budget=budget, max_priority=Priority.P3, dirty_domains=dirty_domains)
