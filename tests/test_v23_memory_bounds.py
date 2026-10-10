"""V23 bounded-resource regressions: no unbounded client queues or checkpoints.

These tests check explicit safety caps and correctness under over-budget
inputs. They are not proof that *all* Python/native allocations cannot leak.
"""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from writerforge import (
    WriterForgeDB, RuntimeEngine, Mode, XuehaiStore, EventBatcher,
    EventEnvelope, DirtyDomain, LaneTask, LaneTaskQueue, Lane,
    StoryWorkRoot, StoryWorkLoop, WorkNode, WorkKind, WorkTreeCheckpointError,
    ReaderLearningSession, ReaderReaction, FeedbackStore,
)
from writerforge.work_tree_checkpoint import encode_finished_tree


class MemoryBoundsTests(unittest.TestCase):
    def test_event_batch_scope_cap_preserves_previous_events_on_overflow(self):
        queue = EventBatcher(max_pending_scopes=2,max_event_names_per_scope=2)
        queue.push(EventEnvelope("a","first",DirtyDomain.CONTINUITY,1))
        queue.push(EventEnvelope("b","second",DirtyDomain.CONTINUITY,1))
        with self.assertRaisesRegex(OverflowError,"scope cap"):
            queue.push(EventEnvelope("c","third",DirtyDomain.CONTINUITY,1))
        self.assertEqual(queue.pending_scope_count(),2)
        flushed=queue.flush()
        self.assertEqual({x.scope for x in flushed},{"first","second"})
        self.assertEqual(queue.pending_scope_count(),0)

    def test_event_name_cap_prevents_growth_without_corrupting_batch(self):
        q=EventBatcher(max_pending_scopes=2,max_event_names_per_scope=2)
        for name in ("a","b"):
            q.push(EventEnvelope(name,"scope",DirtyDomain.CONTINUITY,1))
        with self.assertRaisesRegex(OverflowError,"name cap"):
            q.push(EventEnvelope("c","scope",DirtyDomain.CONTINUITY,1))
        out=q.flush()
        self.assertEqual(out[0].names,("a","b"))

    def test_lane_queue_rejects_excess_before_tracking_scope(self):
        q=LaneTaskQueue(max_pending_tasks=1)
        def task(name,scope):
            return LaneTask(
                name=name,lane=Lane.DRAFT,cost=1,
                scope=scope,generation=1,dirty=DirtyDomain.CONTINUITY,
                fingerprint=name,
            )
        self.assertTrue(q.enqueue(task("first","scene-1")))
        with self.assertRaisesRegex(OverflowError,"queue cap"):
            q.enqueue(task("second","scene-2"))
        self.assertEqual(q.pending_count(),1)
        self.assertEqual(q.tracked_scope_count(),1)
        drained=q.flush(budget=100)
        self.assertEqual([x.name for x in drained.selected],["first"])
        self.assertEqual(q.pending_count(),0)
        self.assertEqual(q.tracked_scope_count(),0)
        self.assertTrue(q.enqueue(task("third","scene-3")))

    @staticmethod
    def finished_root():
        book=WorkNode("book",WorkKind.BOOK,memoized_state={"chapters":2})
        scene=book.append_child(WorkNode("scene",WorkKind.SCENE,memoized_state={"body":"old"}))
        root=StoryWorkRoot(book)
        root.schedule_update(scene,Lane.DRAFT,pending_state={"body":"new"})
        StoryWorkLoop().render(root,render_lanes=Lane.DRAFT)
        return root

    def test_worktree_memory_budget_checks_before_commit(self):
        root=self.finished_root()
        with patch("writerforge.work_tree_checkpoint.MAX_CHECKPOINT_NODES",1):
            with self.assertRaisesRegex(WorkTreeCheckpointError,"node cap"):
                encode_finished_tree(root)
        with patch("writerforge.work_tree_checkpoint.MAX_CHECKPOINT_CHARS",200):
            with self.assertRaisesRegex(WorkTreeCheckpointError,"budget|size|large"):
                encode_finished_tree(root)
        raw,checksum=encode_finished_tree(root)
        self.assertTrue(raw)
        self.assertEqual(len(checksum),64)

    def test_speculative_render_cap_fails_clean_and_can_retry(self):
        root = self.finished_root()
        # Finished root from helper is intentional: first reject candidate,
        # then retry current pending work at the same scope.
        root.discard_finished(drop_rendered_updates=False)
        with patch("writerforge.story_work_tree.MAX_RENDER_UNITS",1):
            with self.assertRaisesRegex(RuntimeError,"render cap"):
                StoryWorkLoop().render(root,render_lanes=Lane.DRAFT)
        self.assertIsNone(root.finished_work)
        self.assertTrue(bool(root.current.child.lanes & Lane.DRAFT))
        # The pending work was not lost and can finish after relaxing budget.
        result=StoryWorkLoop().render(root,render_lanes=Lane.DRAFT)
        self.assertGreaterEqual(result.units,2)

    def test_checkpoint_rejects_excess_depth_and_long_string(self):
        from writerforge.work_tree_checkpoint import _check_json_native
        with self.assertRaisesRegex(WorkTreeCheckpointError,"nesting"):
            nested="end"
            for _ in range(90):
                nested=[nested]
            _check_json_native(nested)
        with self.assertRaisesRegex(WorkTreeCheckpointError,"too long"):
            _check_json_native("A" * 250001)

    def test_reader_trace_query_is_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            db=WriterForgeDB(Path(folder)/"evidence.db")
            rt=RuntimeEngine()
            rt.enter_learn()
            reader=ReaderLearningSession(db,rt,"session","work",1,12)
            reader.start()
            for i in range(12):
                reader.record_first_read(i,f"chapter-{i}",ReaderReaction(3,3,3))
            self.assertEqual(len(reader.trajectory(limit=5)),5)
            self.assertEqual(reader.trajectory(limit=5,offset=10)[0]["unit_index"],10)
            with self.assertRaises(Exception):
                reader.trajectory(limit=999999)
            db.close()

    def test_feedback_aggregate_is_unbounded_count_but_bounded_items(self):
        with tempfile.TemporaryDirectory() as folder:
            db=WriterForgeDB(Path(folder)/"feedback.db")
            feedback=FeedbackStore(db,"project")
            for i in range(31):
                feedback.add(reader_id=f"reader-{i%4}",chapter_ref=f"ch-{i}",
                             category="continuity",comment=f"issue {i}")
            out=feedback.triage(limit=5)
            self.assertEqual(out["counts"]["continuity"],31)
            self.assertEqual(len(out["items"]),5)
            self.assertTrue(out["items_truncated"])
            self.assertEqual(out["convergent_signals"],["continuity"])
            db.close()


if __name__=="__main__":
    unittest.main()
