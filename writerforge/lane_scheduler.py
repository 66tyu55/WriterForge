from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntFlag
import heapq
import itertools
from typing import Iterable


class Lane(IntFlag):
    """WriterForge scheduling lanes, ordered from urgent to deferrable."""

    NONE = 0
    SYNC = 1 << 0          # correctness/commit guards; never deferred
    DRAFT = 1 << 1         # sentence-level continuity and accepted-text bookkeeping
    REACTIVE = 1 << 2      # xuehai/memory/craft routing caused by real deltas
    BOUNDARY = 1 << 3      # scene/chapter structural checks
    TRANSITION = 1 << 4    # reader/taste/reviewer work that may be interrupted
    OFFLINE = 1 << 5       # LEARN synthesis, full-book audit, evolution
    IDLE = 1 << 6          # opportunistic maintenance only


LANE_ORDER: tuple[Lane, ...] = (
    Lane.SYNC,
    Lane.DRAFT,
    Lane.REACTIVE,
    Lane.BOUNDARY,
    Lane.TRANSITION,
    Lane.OFFLINE,
    Lane.IDLE,
)

LANE_RANK = {lane: i for i, lane in enumerate(LANE_ORDER)}
NON_IDLE_LANES = (
    Lane.SYNC | Lane.DRAFT | Lane.REACTIVE | Lane.BOUNDARY |
    Lane.TRANSITION | Lane.OFFLINE
)

# WriterForge uses logical ticks, not browser milliseconds. Values are deliberately
# policy-level and can later be calibrated from real runtime traces.
LANE_EXPIRATION_TICKS: dict[Lane, int | None] = {
    Lane.SYNC: 1,
    Lane.DRAFT: 2,
    Lane.REACTIVE: 5,
    Lane.BOUNDARY: 8,
    Lane.TRANSITION: 13,
    Lane.OFFLINE: None,
    Lane.IDLE: None,
}


def highest_priority_lane(lanes: Lane) -> Lane:
    """O(1) lowest-set-bit selection, analogous to a lane bitmask scheduler."""
    if lanes == Lane.NONE:
        return Lane.NONE
    value = int(lanes)
    return Lane(value & -value)


def iter_lanes(lanes: Lane):
    """Yield concrete lanes from highest to lowest priority."""
    value = int(lanes)
    while value:
        bit = value & -value
        yield Lane(bit)
        value &= ~bit


def merge_lanes(a: Lane, b: Lane) -> Lane:
    return a | b


def remove_lanes(source: Lane, subset: Lane) -> Lane:
    return source & ~subset


def intersect_lanes(a: Lane, b: Lane) -> Lane:
    return a & b


@dataclass
class LaneRootState:
    """
    Aggregate scheduling state for one WriterForge root/scope.

    This adapts React's root lane state to long-form fiction:
    - pending: work exists
    - suspended: work is blocked by missing evidence/data
    - pinged: blocked work became runnable
    - warm: blocked work has already explored all currently available siblings
    - expired: non-suspended work has starved past its lane deadline
    - entangled: semantically coupled lanes must render as one logical version
    """

    pending: Lane = Lane.NONE
    suspended: Lane = Lane.NONE
    pinged: Lane = Lane.NONE
    warm: Lane = Lane.NONE
    expired: Lane = Lane.NONE
    entangled: Lane = Lane.NONE
    entanglements: dict[Lane, Lane] = field(default_factory=dict)
    expiration_ticks: dict[Lane, int | None] = field(default_factory=dict)

    def mark_updated(self, lane: Lane, *, now_tick: int = 0) -> None:
        self.pending |= lane
        # A fresh update can unblock prior work in the *same* semantic lane.
        # WriterForge intentionally does not clear unrelated suspended lanes.
        self.suspended &= ~lane
        self.pinged &= ~lane
        self.warm &= ~lane
        for concrete in iter_lanes(lane):
            if concrete not in self.expiration_ticks:
                ttl = LANE_EXPIRATION_TICKS.get(concrete)
                self.expiration_ticks[concrete] = None if ttl is None else now_tick + ttl

    def mark_suspended(self, lanes: Lane, *, attempted_entire_scope: bool = False) -> None:
        lanes &= self.pending
        self.suspended |= lanes
        self.pinged &= ~lanes
        if attempted_entire_scope:
            self.warm |= lanes
        else:
            self.warm &= ~lanes
        # Suspended work is waiting on data, not CPU; clear starvation clocks.
        for concrete in iter_lanes(lanes):
            self.expiration_ticks[concrete] = None

    def mark_pinged(self, lanes: Lane) -> None:
        reopened = self.suspended & lanes
        self.pinged |= reopened
        self.warm &= ~reopened

    def mark_starved_lanes_as_expired(self, *, now_tick: int) -> Lane:
        for concrete in iter_lanes(self.pending):
            if concrete in {Lane.OFFLINE, Lane.IDLE}:
                continue
            if (concrete & self.suspended) and not (concrete & self.pinged):
                continue
            deadline = self.expiration_ticks.get(concrete)
            if deadline is None:
                ttl = LANE_EXPIRATION_TICKS.get(concrete)
                if ttl is not None:
                    self.expiration_ticks[concrete] = now_tick + ttl
            elif deadline <= now_tick:
                self.expired |= concrete
        return self.expired

    def mark_entangled(self, lanes: Lane) -> None:
        """
        Entanglement is transitive:
        if C is already coupled to A, then entangling A with B also couples C/B.
        """
        if lanes == Lane.NONE:
            return
        self.entangled |= lanes
        changed = True
        while changed:
            changed = False
            closure = lanes
            for concrete in iter_lanes(self.entangled):
                linked = self.entanglements.get(concrete, Lane.NONE)
                if concrete & closure or linked & closure:
                    closure |= concrete | linked
            if closure != lanes:
                lanes = closure
                self.entangled |= lanes
                changed = True
        for concrete in iter_lanes(lanes):
            self.entanglements[concrete] = self.entanglements.get(concrete, Lane.NONE) | lanes

    def get_entangled_lanes(self, lanes: Lane) -> Lane:
        out = lanes
        changed = True
        while changed:
            changed = False
            for concrete in iter_lanes(out & self.entangled):
                expanded = out | self.entanglements.get(concrete, Lane.NONE)
                if expanded != out:
                    out = expanded
                    changed = True
        return out & self.pending

    def get_next_lanes(self, *, wip_lanes: Lane = Lane.NONE) -> Lane:
        if self.pending == Lane.NONE:
            return Lane.NONE

        non_idle = self.pending & NON_IDLE_LANES
        pool = non_idle if non_idle != Lane.NONE else self.pending

        unblocked = pool & ~self.suspended
        if unblocked != Lane.NONE:
            expired = unblocked & self.expired
            candidate_pool = expired if expired != Lane.NONE else unblocked
        else:
            pinged = pool & self.pinged
            if pinged == Lane.NONE:
                return Lane.NONE
            candidate_pool = pinged

        next_lanes = highest_priority_lane(candidate_pool)
        next_lanes = self.get_entangled_lanes(next_lanes)

        # Preserve useful in-progress work unless the incoming lane is truly more urgent.
        if (
            wip_lanes != Lane.NONE
            and wip_lanes != next_lanes
            and (wip_lanes & self.suspended) == Lane.NONE
        ):
            next_lane = highest_priority_lane(next_lanes)
            wip_lane = highest_priority_lane(wip_lanes)
            if int(next_lane) >= int(wip_lane):
                return wip_lanes

        return next_lanes

    def mark_finished(self, *, finished: Lane, remaining: Lane) -> None:
        previously_pending = self.pending
        no_longer_pending = previously_pending & ~remaining
        self.pending = remaining
        self.suspended &= remaining
        self.pinged &= remaining
        self.warm &= remaining
        self.expired &= remaining
        self.entangled &= remaining

        for concrete in tuple(iter_lanes(no_longer_pending)):
            self.expiration_ticks.pop(concrete, None)
            self.entanglements.pop(concrete, None)

        # Remove completed lanes from surviving entanglement sets.
        for concrete in tuple(self.entanglements):
            self.entanglements[concrete] &= remaining
            if self.entanglements[concrete] == Lane.NONE:
                self.entanglements.pop(concrete, None)


class DirtyDomain(IntFlag):
    NONE = 0
    RUNTIME = 1 << 0
    SNAPSHOT = 1 << 1
    CONTINUITY = 1 << 2
    CHARACTER = 1 << 3
    CAUSALITY = 1 << 4
    MEMORY = 1 << 5
    PROMISE = 1 << 6
    READER = 1 << 7
    CRAFT = 1 << 8
    VOICE = 1 << 9
    XUEHAI = 1 << 10
    WORLD = 1 << 11
    TASTE = 1 << 12
    LEARN = 1 << 13
    EVOLUTION = 1 << 14


@dataclass(frozen=True)
class EventEnvelope:
    name: str
    scope: str = "global"
    dirty: DirtyDomain = DirtyDomain.NONE
    generation: int = 0
    transition_id: str | None = None
    priority: int | None = None  # EventPriority value; int avoids import cycle.


@dataclass(frozen=True)
class BatchedEvent:
    names: tuple[str, ...]
    scope: str
    dirty: DirtyDomain
    generation: int
    transition_ids: tuple[str, ...] = ()
    priority: int | None = None


class EventBatcher:
    """
    Coalesces events for the same scope before scheduling.

    This is batching, not object pooling. Multiple deltas in one logical turn become
    one dirty-domain mask so guards/retrieval/review are scheduled once.
    """

    def __init__(self) -> None:
        self._pending: dict[str, list[EventEnvelope]] = {}

    def push(self, event: EventEnvelope) -> None:
        self._pending.setdefault(event.scope, []).append(event)

    @staticmethod
    def _merge_priority(a: int | None, b: int | None) -> int | None:
        if a is None:
            return b
        if b is None:
            return a
        if a == 0:
            return b
        if b == 0:
            return a
        return min(a, b)

    def flush(self, scope: str | None = None) -> tuple[BatchedEvent, ...]:
        scopes = [scope] if scope is not None else list(self._pending)
        out: list[BatchedEvent] = []
        for key in scopes:
            events = self._pending.pop(key, [])
            if not events:
                continue
            names: list[str] = []
            seen_names: set[str] = set()
            dirty = DirtyDomain.NONE
            generation = 0
            transition_ids: list[str] = []
            seen_transitions: set[str] = set()
            priority: int | None = None
            for event in events:
                if event.name not in seen_names:
                    seen_names.add(event.name)
                    names.append(event.name)
                dirty |= event.dirty
                generation = max(generation, event.generation)
                priority = self._merge_priority(priority, event.priority)
                if event.transition_id and event.transition_id not in seen_transitions:
                    seen_transitions.add(event.transition_id)
                    transition_ids.append(event.transition_id)
            out.append(BatchedEvent(
                tuple(names), key, dirty, generation, tuple(transition_ids), priority
            ))
        # Process more urgent source events first across independent scopes.
        out.sort(key=lambda x: (x.priority if x.priority not in (None, 0) else 999, x.scope))
        return tuple(out)


@dataclass(frozen=True)
class LaneTask:
    name: str
    lane: Lane
    cost: int
    scope: str
    generation: int = 0
    dirty: DirtyDomain = DirtyDomain.NONE
    fingerprint: str = ""
    timeout_ticks: int = 0
    transition_id: str | None = None
    cancel_if_stale: bool = True
    source_priority: int | None = None


@dataclass(frozen=True)
class DispatchSlice:
    selected: tuple[LaneTask, ...]
    spent: int
    remaining: int
    yielded: bool
    dropped_stale: tuple[str, ...] = ()
    deferred: tuple[str, ...] = ()


@dataclass(order=True)
class _HeapItem:
    sort_key: tuple[int, int, int, int, int]
    sequence: int
    task: LaneTask = field(compare=False)
    enqueued_tick: int = field(compare=False)


class LaneTaskQueue:
    """
    Cost-sliced cooperative queue.

    - heap order keeps urgent/expiring work near the front;
    - event priority breaks ties between work in the same execution lane;
    - low-priority tasks gain urgency at their deadline (starvation protection);
    - transition/offline tasks can be dropped when a newer generation supersedes them;
    - duplicate scope/name/fingerprint work is enqueued once.
    """

    def __init__(self) -> None:
        self._heap: list[_HeapItem] = []
        self._sequence = itertools.count()
        self._dedupe: set[tuple[str, str, str, int]] = set()
        self._latest_generation: dict[str, int] = {}

    @staticmethod
    def _rank(lane: Lane) -> int:
        concrete = highest_priority_lane(lane)
        return LANE_RANK.get(concrete, len(LANE_ORDER))

    @staticmethod
    def _source_rank(priority: int | None) -> int:
        return priority if priority not in (None, 0) else 999

    def _sort_key(self, task: LaneTask, enqueued_tick: int) -> tuple[int, int, int, int, int]:
        deadline = enqueued_tick + task.timeout_ticks if task.timeout_ticks > 0 else 10**9
        return (
            self._rank(task.lane),
            self._source_rank(task.source_priority),
            deadline,
            task.cost,
            0,
        )

    def enqueue(self, task: LaneTask, *, now_tick: int = 0) -> bool:
        self._latest_generation[task.scope] = max(
            task.generation, self._latest_generation.get(task.scope, task.generation)
        )
        key = (task.scope, task.name, task.fingerprint, task.generation)
        if key in self._dedupe:
            return False
        self._dedupe.add(key)
        seq = next(self._sequence)
        item = _HeapItem(self._sort_key(task, now_tick), seq, task, now_tick)
        heapq.heappush(self._heap, item)
        return True

    def advance_generation(self, scope: str, generation: int) -> None:
        self._latest_generation[scope] = max(generation, self._latest_generation.get(scope, generation))

    def _is_stale(self, task: LaneTask) -> bool:
        if not task.cancel_if_stale:
            return False
        latest = self._latest_generation.get(task.scope, task.generation)
        if task.generation >= latest:
            return False
        return highest_priority_lane(task.lane) in {Lane.TRANSITION, Lane.OFFLINE, Lane.IDLE}

    def _expired(self, item: _HeapItem, now_tick: int) -> bool:
        return item.task.timeout_ticks > 0 and now_tick >= item.enqueued_tick + item.task.timeout_ticks

    def flush(self, *, budget: int, now_tick: int = 0, allowed: Lane = Lane(~0)) -> DispatchSlice:
        if budget < 0:
            raise ValueError("budget must be >= 0")

        items = [heapq.heappop(self._heap) for _ in range(len(self._heap))]
        for item in items:
            task = item.task
            expired = self._expired(item, now_tick)
            lane_rank = -1 if expired else self._rank(task.lane)
            deadline = item.enqueued_tick + task.timeout_ticks if task.timeout_ticks > 0 else 10**9
            item.sort_key = (
                lane_rank,
                self._source_rank(task.source_priority),
                deadline,
                task.cost,
                item.sequence,
            )
            heapq.heappush(self._heap, item)

        selected: list[LaneTask] = []
        deferred_items: list[_HeapItem] = []
        dropped: list[str] = []
        spent = 0

        while self._heap:
            item = heapq.heappop(self._heap)
            task = item.task
            key = (task.scope, task.name, task.fingerprint, task.generation)

            if self._is_stale(task):
                self._dedupe.discard(key)
                dropped.append(task.name)
                continue

            if not (task.lane & allowed):
                deferred_items.append(item)
                continue

            expired = self._expired(item, now_tick)
            if spent + task.cost > budget and not expired:
                deferred_items.append(item)
                break

            selected.append(task)
            spent += task.cost
            self._dedupe.discard(key)
            if spent >= budget:
                break

        while self._heap:
            deferred_items.append(heapq.heappop(self._heap))
        for item in deferred_items:
            heapq.heappush(self._heap, item)

        deferred_names = tuple(item.task.name for item in sorted(deferred_items))
        return DispatchSlice(
            selected=tuple(selected),
            spent=spent,
            remaining=max(0, budget - spent),
            yielded=bool(deferred_items),
            dropped_stale=tuple(dropped),
            deferred=deferred_names,
        )

    def pending_count(self) -> int:
        return len(self._heap)
