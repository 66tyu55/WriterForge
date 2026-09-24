from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterator

from .lane_scheduler import Lane, LaneRootState, iter_lanes
from .reactive_runtime import stable_fingerprint


_UNSET = object()


class WorkKind(str, Enum):
    BOOK = "book"
    ARC = "arc"
    CHAPTER = "chapter"
    SCENE = "scene"
    CHARACTER = "character"
    CAUSALITY = "causality"
    PROMISE = "promise"
    READER = "reader"
    CRAFT = "craft"
    LEARN = "learn"
    GENERIC = "generic"


@dataclass(frozen=True)
class PendingUpdate:
    state: Any
    fingerprint: str
    sequence: int


@dataclass
class WorkNode:
    key: str
    kind: WorkKind = WorkKind.GENERIC
    pending_state: Any = None
    memoized_state: Any = None
    pending_fingerprint: str = ""
    memoized_fingerprint: str = ""
    lanes: Lane = Lane.NONE
    child_lanes: Lane = Lane.NONE
    pending_updates: dict[Lane, PendingUpdate] = field(default_factory=dict)

    parent: WorkNode | None = field(default=None, repr=False)
    child: WorkNode | None = field(default=None, repr=False)
    sibling: WorkNode | None = field(default=None, repr=False)
    alternate: WorkNode | None = field(default=None, repr=False)

    did_work: bool = False
    subtree_did_work: bool = False
    generation: int = 0

    def __post_init__(self) -> None:
        if not self.pending_fingerprint and self.pending_state is not None:
            self.pending_fingerprint = stable_fingerprint(self.pending_state)
        if not self.memoized_fingerprint and self.memoized_state is not None:
            self.memoized_fingerprint = stable_fingerprint(self.memoized_state)

    def append_child(self, child: "WorkNode") -> "WorkNode":
        child.parent = self
        child.sibling = None
        if self.child is None:
            self.child = child
            return child
        cursor = self.child
        while cursor.sibling is not None:
            cursor = cursor.sibling
        cursor.sibling = child
        return child

    def children(self) -> Iterator["WorkNode"]:
        child = self.child
        while child is not None:
            yield child
            child = child.sibling


@dataclass(frozen=True)
class BeginResult:
    next_child: WorkNode | None
    bailed_out: bool = False
    subtree_bailout: bool = False


@dataclass(frozen=True)
class WorkLoopResult:
    render_lanes: Lane
    visited: tuple[str, ...]
    completed: tuple[str, ...]
    bailed_subtrees: tuple[str, ...]
    units: int


ComputeFn = Callable[[WorkNode | None, WorkNode], tuple[Any, str] | Any]


def _latest_update(node: WorkNode, lanes: Lane | None = None) -> PendingUpdate | None:
    updates = [
        update
        for lane, update in node.pending_updates.items()
        if lanes is None or bool(lane & lanes)
    ]
    return max(updates, key=lambda x: x.sequence) if updates else None


def _sync_pending_view(node: WorkNode) -> None:
    update = _latest_update(node)
    if update is None:
        node.pending_state = node.memoized_state
        node.pending_fingerprint = node.memoized_fingerprint
    else:
        node.pending_state = update.state
        node.pending_fingerprint = update.fingerprint


def create_work_in_progress(
    current: WorkNode,
    *,
    pending_state: Any = _UNSET,
    pending_fingerprint: str | None = None,
) -> WorkNode:
    wip = current.alternate
    if wip is None:
        wip = WorkNode(key=current.key, kind=current.kind)
        wip.alternate = current
        current.alternate = wip

    wip.key = current.key
    wip.kind = current.kind
    wip.parent = None
    wip.sibling = None
    wip.child = current.child
    wip.memoized_state = current.memoized_state
    wip.memoized_fingerprint = current.memoized_fingerprint
    wip.pending_updates = dict(current.pending_updates)

    if pending_state is _UNSET:
        _sync_pending_view(wip)
    else:
        wip.pending_state = pending_state
        wip.pending_fingerprint = (
            pending_fingerprint
            if pending_fingerprint is not None
            else stable_fingerprint(pending_state)
        )

    wip.lanes = current.lanes
    wip.child_lanes = current.child_lanes
    wip.did_work = False
    wip.subtree_did_work = False
    wip.generation = current.generation
    return wip


def clone_child_chain(current: WorkNode, wip: WorkNode) -> WorkNode | None:
    current_child = current.child
    if current_child is None:
        wip.child = None
        return None

    first: WorkNode | None = None
    previous: WorkNode | None = None
    while current_child is not None:
        cloned = create_work_in_progress(current_child)
        cloned.parent = wip
        if first is None:
            first = cloned
        if previous is not None:
            previous.sibling = cloned
        previous = cloned
        current_child = current_child.sibling

    if previous is not None:
        previous.sibling = None
    wip.child = first
    return first


def mark_update_lane_from_node_to_root(node: WorkNode, lane: Lane) -> WorkNode:
    node.lanes |= lane
    if node.alternate is not None:
        node.alternate.lanes |= lane

    cursor = node
    parent = node.parent
    while parent is not None:
        parent.child_lanes |= lane
        if parent.alternate is not None:
            parent.alternate.child_lanes |= lane
        cursor = parent
        parent = parent.parent
    return cursor


def _has_lane(mask: Lane, render_lanes: Lane) -> bool:
    return bool(mask & render_lanes)


def begin_work(
    current: WorkNode | None,
    wip: WorkNode,
    render_lanes: Lane,
    *,
    compute: ComputeFn | None = None,
) -> BeginResult:
    own_work = _has_lane(wip.lanes, render_lanes)
    selected_update = _latest_update(wip, render_lanes)
    selected_fingerprint = (
        selected_update.fingerprint
        if selected_update is not None
        else wip.pending_fingerprint
    )
    same_input = (
        current is not None
        and selected_fingerprint == current.memoized_fingerprint
    )

    if current is not None and not own_work and same_input:
        if not _has_lane(wip.child_lanes, render_lanes):
            wip.child = current.child
            return BeginResult(None, bailed_out=True, subtree_bailout=True)
        return BeginResult(
            clone_child_chain(current, wip),
            bailed_out=True,
            subtree_bailout=False,
        )

    if own_work or current is None or not same_input:
        if selected_update is not None:
            wip.pending_state = selected_update.state
            wip.pending_fingerprint = selected_update.fingerprint

        if compute is not None:
            computed = compute(current, wip)
            if isinstance(computed, tuple) and len(computed) == 2:
                next_state, fingerprint = computed
            else:
                next_state = computed
                fingerprint = stable_fingerprint(next_state)
            wip.memoized_state = next_state
            wip.memoized_fingerprint = fingerprint
        else:
            wip.memoized_state = wip.pending_state
            wip.memoized_fingerprint = (
                wip.pending_fingerprint
                or stable_fingerprint(wip.pending_state)
            )

        for concrete in tuple(wip.pending_updates):
            if concrete & render_lanes:
                wip.pending_updates.pop(concrete, None)
        wip.lanes &= ~render_lanes
        _sync_pending_view(wip)
        wip.did_work = True

    if current is None:
        child = wip.child
        while child is not None:
            child.parent = wip
            child = child.sibling
        return BeginResult(wip.child)

    if _has_lane(wip.child_lanes, render_lanes):
        return BeginResult(clone_child_chain(current, wip))
    wip.child = current.child
    return BeginResult(None)


def complete_work(wip: WorkNode) -> None:
    child_lanes = Lane.NONE
    subtree_did_work = False
    child = wip.child
    while child is not None:
        child_lanes |= child.lanes | child.child_lanes
        subtree_did_work = subtree_did_work or child.did_work or child.subtree_did_work
        child = child.sibling
    wip.child_lanes = child_lanes
    wip.subtree_did_work = subtree_did_work


def iter_tree(root: WorkNode) -> Iterator[WorkNode]:
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        children = list(node.children())
        stack.extend(reversed(children))


def find_node(root: WorkNode, key: str) -> WorkNode | None:
    for node in iter_tree(root):
        if node.key == key:
            return node
    return None


def repair_parent_links(root: WorkNode) -> None:
    root.parent = None
    stack = [root]
    while stack:
        node = stack.pop()
        child = node.child
        children = []
        while child is not None:
            child.parent = node
            children.append(child)
            child = child.sibling
        stack.extend(reversed(children))


def _recompute_child_lanes(root: WorkNode) -> None:
    nodes = list(iter_tree(root))
    for node in reversed(nodes):
        child_lanes = Lane.NONE
        child = node.child
        while child is not None:
            child_lanes |= child.lanes | child.child_lanes
            child = child.sibling
        node.child_lanes = child_lanes


def _detach_alternates(root: WorkNode) -> None:
    for node in list(iter_tree(root)):
        alt = node.alternate
        node.alternate = None
        if alt is not None and alt.alternate is node:
            alt.alternate = None


@dataclass
class StoryWorkRoot:
    current: WorkNode
    lane_state: LaneRootState = field(default_factory=LaneRootState)
    work_in_progress: WorkNode | None = None
    finished_work: WorkNode | None = None
    render_lanes: Lane = Lane.NONE
    _update_sequence: int = 0

    def schedule_update(
        self,
        node: WorkNode,
        lane: Lane,
        *,
        pending_state: Any = _UNSET,
        pending_fingerprint: str | None = None,
        now_tick: int = 0,
    ) -> None:
        self._update_sequence += 1

        if pending_state is _UNSET:
            update_state = node.memoized_state
            update_fingerprint = (
                pending_fingerprint
                if pending_fingerprint is not None
                else node.memoized_fingerprint
            )
        else:
            update_state = pending_state
            update_fingerprint = (
                pending_fingerprint
                if pending_fingerprint is not None
                else stable_fingerprint(pending_state)
            )

        update = PendingUpdate(update_state, update_fingerprint, self._update_sequence)
        for concrete in iter_lanes(lane):
            node.pending_updates[concrete] = update
        _sync_pending_view(node)

        tree_root = mark_update_lane_from_node_to_root(node, lane)
        if tree_root is not self.current:
            raise ValueError("scheduled node does not belong to current root")
        self.lane_state.mark_updated(lane, now_tick=now_tick)

    def prepare(self, render_lanes: Lane | None = None) -> WorkNode:
        lanes = self.lane_state.get_next_lanes() if render_lanes is None else render_lanes
        if lanes == Lane.NONE:
            raise ValueError("no render lanes available")
        self.render_lanes = lanes
        self.work_in_progress = create_work_in_progress(self.current)
        self.work_in_progress.parent = None
        self.finished_work = None
        return self.work_in_progress

    def mark_finished(self, root: WorkNode) -> None:
        self.finished_work = root

    def finished_fingerprint(self) -> str:
        if self.finished_work is None:
            raise ValueError("no finished work")
        records = [
            (
                node.key,
                node.kind.value,
                node.memoized_fingerprint,
                int(node.lanes),
                int(node.child_lanes),
            )
            for node in iter_tree(self.finished_work)
        ]
        return stable_fingerprint(records)

    def discard_finished(self, *, drop_rendered_updates: bool = True) -> None:
        rendered = self.render_lanes
        if drop_rendered_updates and rendered != Lane.NONE:
            for node in iter_tree(self.current):
                for concrete in tuple(node.pending_updates):
                    if concrete & rendered:
                        node.pending_updates.pop(concrete, None)
                node.lanes &= ~rendered
                _sync_pending_view(node)
            _recompute_child_lanes(self.current)
            remaining = self.current.lanes | self.current.child_lanes
            self.lane_state.mark_finished(finished=rendered, remaining=remaining)

        _detach_alternates(self.current)
        self.work_in_progress = None
        self.finished_work = None
        self.render_lanes = Lane.NONE

    def adopt_after_commit(self) -> WorkNode:
        if self.finished_work is None:
            raise ValueError("no finished work to adopt")
        finished = self.finished_work
        remaining = finished.lanes | finished.child_lanes
        self.current = finished
        repair_parent_links(self.current)
        self.lane_state.mark_finished(finished=self.render_lanes, remaining=remaining)
        self.work_in_progress = None
        self.finished_work = None
        self.render_lanes = Lane.NONE
        return self.current


class StoryWorkLoop:
    def render(
        self,
        root: StoryWorkRoot,
        *,
        render_lanes: Lane | None = None,
        compute: ComputeFn | None = None,
    ) -> WorkLoopResult:
        work = root.prepare(render_lanes)
        lanes = root.render_lanes
        unit: WorkNode | None = work
        visited: list[str] = []
        completed: list[str] = []
        bailed: list[str] = []
        units = 0

        while unit is not None:
            units += 1
            visited.append(unit.key)
            current = unit.alternate
            result = begin_work(current, unit, lanes, compute=compute)
            if result.subtree_bailout:
                bailed.append(unit.key)

            if result.next_child is not None:
                unit = result.next_child
                continue

            unit = self._complete_unit(unit, completed)

        root.mark_finished(work)
        return WorkLoopResult(lanes, tuple(visited), tuple(completed), tuple(bailed), units)

    @staticmethod
    def _complete_unit(unit: WorkNode, completed: list[str]) -> WorkNode | None:
        node: WorkNode | None = unit
        while node is not None:
            complete_work(node)
            completed.append(node.key)
            if node.sibling is not None:
                return node.sibling
            node = node.parent
        return None
