from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterator

from .lane_scheduler import Lane, LaneRootState
from .reactive_runtime import stable_fingerprint


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


@dataclass
class WorkNode:
    """
    One node in WriterForge's Story Work Tree.

    current and alternate form a two-version buffer. The tree is purely
    computational: creating/reconciling a work-in-progress tree must never
    mutate accepted prose, Canon, or durable story state.
    """

    key: str
    kind: WorkKind = WorkKind.GENERIC
    pending_state: Any = None
    memoized_state: Any = None
    pending_fingerprint: str = ""
    memoized_fingerprint: str = ""
    lanes: Lane = Lane.NONE
    child_lanes: Lane = Lane.NONE

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


def create_work_in_progress(
    current: WorkNode,
    *,
    pending_state: Any = None,
    pending_fingerprint: str | None = None,
) -> WorkNode:
    """
    Create or reuse the alternate node.

    The alternate is lazily allocated and then reused. Per-render fields are
    reset while memoized state, lanes, and current child pointers are copied.
    Children are cloned lazily only when their subtree actually needs work.
    """
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

    # Carry an already-scheduled pending input from current into WIP. If the
    # current node has no explicit pending input, fall back to its memoized
    # accepted computation state.
    if pending_state is None:
        wip.pending_state = (
            current.pending_state
            if current.pending_state is not None
            else current.memoized_state
        )
        wip.pending_fingerprint = (
            current.pending_fingerprint
            or current.memoized_fingerprint
        )
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
    """
    Mark one node dirty and bubble only child-lane metadata through its ancestors.
    Unrelated sibling subtrees remain clean.
    """
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
    """
    Begin phase: decide whether this node needs work and whether its subtree can
    be skipped. No durable side effects are allowed here.
    """
    own_work = _has_lane(wip.lanes, render_lanes)
    same_input = (
        current is not None
        and wip.pending_fingerprint == current.memoized_fingerprint
    )

    if current is not None and not own_work and same_input:
        if not _has_lane(wip.child_lanes, render_lanes):
            wip.child = current.child
            return BeginResult(None, bailed_out=True, subtree_bailout=True)
        child = clone_child_chain(current, wip)
        return BeginResult(child, bailed_out=True, subtree_bailout=False)

    if own_work or current is None or not same_input:
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
        # Once this speculative node has consumed its pending input, keep its
        # pending/memoized views aligned. A later update will replace pending.
        wip.pending_state = wip.memoized_state
        wip.pending_fingerprint = wip.memoized_fingerprint
        wip.did_work = True
        wip.lanes &= ~render_lanes

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
    """
    Complete phase: bubble surviving child lanes and a cheap subtree-work flag.
    This prepares metadata only; Story/Canon mutation belongs to the later
    transactional commit phase.
    """
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
    """Repair parent pointers after a finished tree becomes current."""
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


@dataclass
class StoryWorkRoot:
    """
    Owns accepted computation tree current and one speculative WIP tree.
    adopt_after_commit must only be called after the outer Story Commit succeeds.
    """

    current: WorkNode
    lane_state: LaneRootState = field(default_factory=LaneRootState)
    work_in_progress: WorkNode | None = None
    finished_work: WorkNode | None = None
    render_lanes: Lane = Lane.NONE

    def schedule_update(
        self,
        node: WorkNode,
        lane: Lane,
        *,
        pending_state: Any = None,
        pending_fingerprint: str | None = None,
        now_tick: int = 0,
    ) -> None:
        if pending_state is not None:
            node.pending_state = pending_state
            node.pending_fingerprint = (
                pending_fingerprint
                if pending_fingerprint is not None
                else stable_fingerprint(pending_state)
            )
        elif pending_fingerprint is not None:
            node.pending_fingerprint = pending_fingerprint
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

    def discard_finished(self) -> None:
        self.work_in_progress = None
        self.finished_work = None
        self.render_lanes = Lane.NONE

    def adopt_after_commit(self) -> WorkNode:
        """
        Swap the computation tree only after the caller's durable Commit succeeds.
        This method does not itself write prose, Canon, DB state, or files.
        """
        if self.finished_work is None:
            raise ValueError("no finished work to adopt")
        finished = self.finished_work
        remaining = finished.lanes | finished.child_lanes
        self.current = finished
        repair_parent_links(self.current)
        self.lane_state.mark_finished(
            finished=self.render_lanes,
            remaining=remaining,
        )
        self.work_in_progress = None
        self.finished_work = None
        self.render_lanes = Lane.NONE
        return self.current


class StoryWorkLoop:
    """
    Deterministic depth-first begin/complete loop.

    V17 intentionally does not implement wall-clock yielding or durable effects.
    Those belong to later scheduler/commit phases.
    """

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
        return WorkLoopResult(
            render_lanes=lanes,
            visited=tuple(visited),
            completed=tuple(completed),
            bailed_subtrees=tuple(bailed),
            units=units,
        )

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
