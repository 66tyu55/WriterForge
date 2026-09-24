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


def highest_priority_lane(lanes: Lane) -> Lane:
    """O(1) lowest-set-bit selection, analogous to a lane bitmask scheduler."""
    if lanes == Lane.NONE:
        return Lane.NONE
    value = int(lanes)
    return Lane(value & -value)


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


@dataclass(frozen=True)
class BatchedEvent:
    names: tuple[str, ...]
    scope: str
    dirty: DirtyDomain
    generation: int
    transition_ids: tuple[str, ...] = ()


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
            for event in events:
                if event.name not in seen_names:
                    seen_names.add(event.name)
                    names.append(event.name)
                dirty |= event.dirty
                generation = max(generation, event.generation)
                if event.transition_id and event.transition_id not in seen_transitions:
                    seen_transitions.add(event.transition_id)
                    transition_ids.append(event.transition_id)
            out.append(BatchedEvent(tuple(names), key, dirty, generation, tuple(transition_ids)))
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
    sort_key: tuple[int, int, int, int]
    sequence: int
    task: LaneTask = field(compare=False)
    enqueued_tick: int = field(compare=False)


class LaneTaskQueue:
    """
    Cost-sliced cooperative queue.

    - heap order keeps urgent/expiring work near the front;
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

    def _sort_key(self, task: LaneTask, enqueued_tick: int) -> tuple[int, int, int, int]:
        # deadline is the primary starvation signal. No timeout means "far future".
        deadline = enqueued_tick + task.timeout_ticks if task.timeout_ticks > 0 else 10**9
        return (self._rank(task.lane), deadline, task.cost, 0)

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
        # Correctness and current drafting work are never silently dropped.
        return highest_priority_lane(task.lane) in {Lane.TRANSITION, Lane.OFFLINE, Lane.IDLE}

    def _expired(self, item: _HeapItem, now_tick: int) -> bool:
        return item.task.timeout_ticks > 0 and now_tick >= item.enqueued_tick + item.task.timeout_ticks

    def flush(self, *, budget: int, now_tick: int = 0, allowed: Lane = Lane(~0)) -> DispatchSlice:
        if budget < 0:
            raise ValueError("budget must be >= 0")

        # Re-key at flush time so expired work gets starvation protection.
        items = [heapq.heappop(self._heap) for _ in range(len(self._heap))]
        for item in items:
            task = item.task
            expired = self._expired(item, now_tick)
            rank = -1 if expired else self._rank(task.lane)
            deadline = item.enqueued_tick + task.timeout_ticks if task.timeout_ticks > 0 else 10**9
            item.sort_key = (rank, deadline, task.cost, item.sequence)
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
                # Do not scan indefinitely for cheaper background work; yield to the caller.
                break

            # An expired task may exceed the nominal slice once, preventing starvation.
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
