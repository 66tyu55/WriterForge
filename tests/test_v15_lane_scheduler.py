import unittest

from writerforge.lane_scheduler import (
    Lane, DirtyDomain, EventEnvelope, EventBatcher,
    LaneTask, LaneTaskQueue, highest_priority_lane,
)


class V15LaneSchedulerTests(unittest.TestCase):
    def test_highest_priority_lane_is_lowest_set_bit(self):
        lanes = Lane.TRANSITION | Lane.REACTIVE | Lane.OFFLINE
        self.assertEqual(highest_priority_lane(lanes), Lane.REACTIVE)

    def test_event_batching_merges_dirty_domains_without_repeating_names(self):
        b = EventBatcher()
        b.push(EventEnvelope("state_changed", "scene-1", DirtyDomain.CHARACTER, generation=2))
        b.push(EventEnvelope("state_changed", "scene-1", DirtyDomain.CAUSALITY, generation=2))
        b.push(EventEnvelope("promise_changed", "scene-1", DirtyDomain.PROMISE, generation=3))
        out = b.flush()[0]
        self.assertEqual(out.names, ("state_changed", "promise_changed"))
        self.assertTrue(out.dirty & DirtyDomain.CHARACTER)
        self.assertTrue(out.dirty & DirtyDomain.CAUSALITY)
        self.assertTrue(out.dirty & DirtyDomain.PROMISE)
        self.assertEqual(out.generation, 3)

    def test_urgent_work_preempts_transition_work(self):
        q = LaneTaskQueue()
        q.enqueue(LaneTask("taste", Lane.TRANSITION, 4, "s", generation=1), now_tick=0)
        q.enqueue(LaneTask("quick_continuity", Lane.DRAFT, 2, "s", generation=1), now_tick=0)
        out = q.flush(budget=2, now_tick=0)
        self.assertEqual([x.name for x in out.selected], ["quick_continuity"])
        self.assertIn("taste", out.deferred)

    def test_same_request_is_enqueued_once(self):
        q = LaneTaskQueue()
        task = LaneTask("memory_recall", Lane.REACTIVE, 2, "s", generation=1, fingerprint="abc")
        self.assertTrue(q.enqueue(task))
        self.assertFalse(q.enqueue(task))
        self.assertEqual(q.pending_count(), 1)

    def test_stale_transition_is_discarded_after_new_generation(self):
        q = LaneTaskQueue()
        q.enqueue(LaneTask("reader_review", Lane.TRANSITION, 5, "chapter-7", generation=1), now_tick=0)
        q.advance_generation("chapter-7", 2)
        out = q.flush(budget=10, now_tick=1)
        self.assertEqual(out.selected, ())
        self.assertEqual(out.dropped_stale, ("reader_review",))

    def test_draft_work_is_not_silently_dropped_when_generation_advances(self):
        q = LaneTaskQueue()
        q.enqueue(LaneTask("commit_guard", Lane.DRAFT, 1, "s", generation=1), now_tick=0)
        q.advance_generation("s", 2)
        out = q.flush(budget=2, now_tick=1)
        self.assertEqual([x.name for x in out.selected], ["commit_guard"])

    def test_expired_low_priority_work_gets_starvation_protection(self):
        q = LaneTaskQueue()
        q.enqueue(LaneTask("offline_summary", Lane.OFFLINE, 5, "book", timeout_ticks=3), now_tick=0)
        # Expired work is allowed one over-budget dispatch rather than starving forever.
        out = q.flush(budget=2, now_tick=3)
        self.assertEqual([x.name for x in out.selected], ["offline_summary"])
        self.assertEqual(out.spent, 5)

    def test_allowed_lane_mask_behaves_like_route_chunk_filter(self):
        q = LaneTaskQueue()
        q.enqueue(LaneTask("draft", Lane.DRAFT, 1, "s"))
        q.enqueue(LaneTask("boundary", Lane.BOUNDARY, 1, "s"))
        q.enqueue(LaneTask("offline", Lane.OFFLINE, 1, "s"))
        out = q.flush(budget=5, allowed=Lane.SYNC | Lane.DRAFT | Lane.REACTIVE)
        self.assertEqual([x.name for x in out.selected], ["draft"])
        self.assertEqual(set(out.deferred), {"boundary", "offline"})


if __name__ == "__main__":
    unittest.main()

class V15SkillSchedulerRoutingTests(unittest.TestCase):
    def test_scene_boundary_loads_only_dirty_deep_domain_when_provided(self):
        from writerforge.scheduler import SkillScheduler
        s = SkillScheduler()
        d = s.boundary_decision(
            "scene_boundary", budget=12,
            dirty_domains=DirtyDomain.CHARACTER | DirtyDomain.MEMORY,
        )
        self.assertIn("character_audit", d.selected)
        self.assertIn("memory_recall", d.selected)
        self.assertNotIn("causality_audit", d.selected)
        self.assertNotIn("deep_continuity", d.selected)

    def test_chapter_reader_route_is_not_stolen_by_unrelated_structural_audits(self):
        from writerforge.scheduler import SkillScheduler
        s = SkillScheduler()
        d = s.boundary_decision(
            "chapter_boundary", budget=16,
            dirty_domains=DirtyDomain.READER | DirtyDomain.PROMISE,
        )
        self.assertIn("reader_experience_review", d.selected)
        self.assertNotIn("character_audit", d.selected)
        self.assertNotIn("causality_audit", d.selected)
        self.assertNotIn("deep_continuity", d.selected)

    def test_default_chapter_boundary_is_reader_oriented_not_full_deep_audit(self):
        from writerforge.scheduler import SkillScheduler
        d = SkillScheduler().boundary_decision("chapter_boundary", budget=24)
        self.assertIn("reader_experience_review", d.selected)
        self.assertNotIn("character_audit", d.selected)
        self.assertNotIn("causality_audit", d.selected)

    def test_pending_runtime_batches_same_turn_and_drops_stale_transition(self):
        from writerforge.scheduler import SkillScheduler, Priority
        s = SkillScheduler()
        s.enqueue_event(EventEnvelope(
            "chapter_boundary", "ch-9", DirtyDomain.READER, generation=1, transition_id="old"
        ))
        # New generation arrives before old transition work is consumed.
        s.enqueue_event(EventEnvelope(
            "chapter_boundary", "ch-9", DirtyDomain.READER, generation=2, transition_id="new"
        ))
        first = s.flush_pending(budget=8, now_tick=0, max_priority=Priority.P2)
        # Sync guards + reader boundary work consume the urgent slice; transition work can defer.
        self.assertIn("runtime_guard", first.selected)
        self.assertIn("snapshot_guard", first.selected)
        self.assertTrue(first.deferred)
