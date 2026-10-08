"""Durable, verified WorkTree checkpoints for crash recovery.

A checkpoint records accepted computation state and any outstanding lane updates.
It is NOT a substitute for canonical prose/character/reader tables: the SQLite
story effects remain the source of truth, and this checkpoint is written in the
same transaction as their receipt. No alternates or speculative buffers persist.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from .db import WriterForgeDB
from .lane_scheduler import Lane
from .story_work_tree import PendingUpdate, StoryWorkRoot, WorkKind, WorkNode, _sync_pending_view


SCHEMA_VERSION = 1


class WorkTreeCheckpointError(ValueError):
    """The durable checkpoint is missing, stale, invalid or unrepresentable."""


def _check_json_native(value: Any) -> None:
    """Reject lossy JSON conversions (tuples, integer mapping keys, NaN, etc.)."""
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for child in value:
            _check_json_native(child)
        return
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise WorkTreeCheckpointError("WorkTree state requires string JSON keys")
            _check_json_native(child)
        return
    raise WorkTreeCheckpointError(
        f"WorkTree state must be native JSON data, got {type(value).__name__}"
    )


def encode_finished_tree(root: StoryWorkRoot) -> tuple[str, str]:
    """Produce canonical JSON and its checksum from a finished computation tree."""
    if root.finished_work is None:
        raise WorkTreeCheckpointError("cannot checkpoint unfinished WorkTree")

    nodes: list[dict[str, Any]] = []
    stack: list[tuple[WorkNode, int | None]] = [(root.finished_work, None)]
    seen_objects: set[int] = set()
    seen_keys: set[str] = set()

    while stack:
        node, parent_index = stack.pop()
        if id(node) in seen_objects:
            raise WorkTreeCheckpointError("WorkTree has a cycle or shared child")
        seen_objects.add(id(node))
        if not isinstance(node.key, str) or not node.key or node.key in seen_keys:
            raise WorkTreeCheckpointError("WorkTree node keys must be unique nonempty strings")
        seen_keys.add(node.key)
        _check_json_native(node.memoized_state)

        pending = []
        for lane, update in sorted(node.pending_updates.items(), key=lambda item: int(item[0])):
            if not _single_lane(int(lane)):
                raise WorkTreeCheckpointError("pending update must target one concrete lane")
            _check_json_native(update.state)
            pending.append({
                "lane": int(lane),
                "state": update.state,
                "fingerprint": update.fingerprint,
                "sequence": update.sequence,
            })
        nodes.append({
            "parent": parent_index,
            "key": node.key,
            "kind": node.kind.value,
            "memoized_state": node.memoized_state,
            "memoized_fingerprint": node.memoized_fingerprint,
            "lanes": int(node.lanes),
            "child_lanes": int(node.child_lanes),
            "generation": node.generation,
            "pending_updates": pending,
        })
        index = len(nodes) - 1
        children = list(node.children())
        stack.extend((child, index) for child in reversed(children))

    payload = {"schema_version": SCHEMA_VERSION, "nodes": nodes}
    try:
        raw = json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise WorkTreeCheckpointError("WorkTree state is not safely JSON serializable") from exc
    return raw, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _single_lane(value: int) -> bool:
    known = int(Lane.SYNC | Lane.DRAFT | Lane.REACTIVE | Lane.BOUNDARY
                | Lane.TRANSITION | Lane.OFFLINE | Lane.IDLE)
    return value > 0 and (value & (value - 1)) == 0 and (value & ~known) == 0


def _decode_tree(raw: str, expected_fingerprint: str) -> StoryWorkRoot:
    try:
        payload = json.loads(raw)
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise WorkTreeCheckpointError("unsupported WorkTree checkpoint schema")
        records = payload["nodes"]
        if not isinstance(records, list) or not records:
            raise WorkTreeCheckpointError("empty WorkTree checkpoint")

        nodes: list[WorkNode] = []
        seen: set[str] = set()
        max_sequence = 0
        all_lanes = Lane.NONE
        for index, record in enumerate(records):
            key = record["key"]
            parent_index = record["parent"]
            if not isinstance(key, str) or not key or key in seen:
                raise WorkTreeCheckpointError("invalid or duplicate WorkTree node key")
            if index == 0 and parent_index is not None:
                raise WorkTreeCheckpointError("root node must have no parent")
            if index != 0 and (type(parent_index) is not int or not 0 <= parent_index < index):
                raise WorkTreeCheckpointError("invalid WorkTree parent index")
            seen.add(key)

            node = WorkNode(
                key=key,
                kind=WorkKind(record["kind"]),
                memoized_state=record["memoized_state"],
                memoized_fingerprint=record["memoized_fingerprint"],
                lanes=Lane(record["lanes"]),
                child_lanes=Lane(record["child_lanes"]),
                generation=record["generation"],
            )
            for pending in record["pending_updates"]:
                lane_int = pending["lane"]
                if type(lane_int) is not int or not _single_lane(lane_int):
                    raise WorkTreeCheckpointError("invalid checkpoint lane")
                lane = Lane(lane_int)
                if lane in node.pending_updates:
                    raise WorkTreeCheckpointError("duplicate pending update lane")
                update = PendingUpdate(
                    pending["state"], pending["fingerprint"], pending["sequence"]
                )
                node.pending_updates[lane] = update
                max_sequence = max(max_sequence, update.sequence)
            _sync_pending_view(node)
            all_lanes |= node.lanes
            nodes.append(node)
            if parent_index is not None:
                nodes[parent_index].append_child(node)

        for node in reversed(nodes):
            children_lanes = Lane.NONE
            for child in node.children():
                children_lanes |= child.lanes | child.child_lanes
            if node.child_lanes != children_lanes:
                raise WorkTreeCheckpointError("checkpoint child-lane aggregation mismatch")
            pending_lanes = Lane.NONE
            for lane in node.pending_updates:
                pending_lanes |= lane
            if node.lanes != pending_lanes:
                raise WorkTreeCheckpointError("checkpoint pending-lane aggregation mismatch")

        root = StoryWorkRoot(nodes[0])
        root._update_sequence = max_sequence
        if all_lanes != Lane.NONE:
            root.lane_state.mark_updated(all_lanes)
        root.finished_work = root.current
        actual_fingerprint = root.finished_fingerprint()
        root.finished_work = None
        if actual_fingerprint != expected_fingerprint:
            raise WorkTreeCheckpointError("WorkTree checkpoint fingerprint mismatch")
        return root
    except WorkTreeCheckpointError:
        raise
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        raise WorkTreeCheckpointError("malformed WorkTree checkpoint") from exc


def restore_work_root(db: WriterForgeDB, project_id: str) -> StoryWorkRoot:
    """Rehydrate the latest accepted WorkTree, never a stale or torn checkpoint."""
    row = db.conn.execute(
        """SELECT commit_id,bundle_hash,tree_hash,tree_json,work_fingerprint
           FROM story_work_checkpoints WHERE project_id=?""",
        (project_id,),
    ).fetchone()
    if row is None:
        raise WorkTreeCheckpointError(
            "no WorkTree checkpoint for project; older commits and rootless "
            "commits cannot be rehydrated automatically"
        )
    head = db.conn.execute(
        """SELECT commit_id,bundle_hash FROM story_commit_receipts
           WHERE project_id=? ORDER BY rowid DESC LIMIT 1""",
        (project_id,),
    ).fetchone()
    if head is None or (row["commit_id"], row["bundle_hash"]) != (
        head["commit_id"], head["bundle_hash"]
    ):
        raise WorkTreeCheckpointError("checkpoint is behind the durable story head")
    actual_hash = hashlib.sha256(row["tree_json"].encode("utf-8")).hexdigest()
    if actual_hash != row["tree_hash"]:
        raise WorkTreeCheckpointError("WorkTree checkpoint checksum mismatch")
    root = _decode_tree(row["tree_json"], row["work_fingerprint"])
    root.durable_commit_id = row["commit_id"]
    return root
