import unittest

from writerforge import (
    Lane, LaneRootState, DirtyDomain, EventEnvelope, EventBatcher,
    EventPriority, higher_event_priority, lower_event_priority,
    is_higher_event_priority, event_priority_to_lane, lanes_to_event_priority,
    priority_for_event,
)


class V16EventPriorityTests(unittest.TestCase):
    def test_event_priority_order_matches_urgency(self):
        self.assertEqual(
            higher_event_priority(EventPriority.DEFAULT, EventPriority.DISCRETE),
            EventPriority.DISCRETE,
        )
        self.assertEqual(
            lower_event_priority(EventPriority.CONTINUOUS, EventPriority.IDLE),
            EventPriority.IDLE,
        )
        self.assertTrue(
            is_higher_event_priority(EventPriority.CONTINUOUS, EventPriority.DEFAULT)
        )

    def test_event_priority_maps_to_source_lane(self):
        self.assertEqual(event_priority_to_lane(EventPriority.DISCRETE), Lane.SYNC)
        self.assertEqual(event_priority_to_lane(EventPriority.CONTINUOUS), Lane.DRAFT)
        self.assertEqual(event_priority_to_lane(EventPriority.DEFAULT), Lane.REACTIVE)
        self.assertEqual(event_priority_to_lane(EventPriority.IDLE), Lane.IDLE)

    def test_lanes_fold_back_to_four_event_priorities(self):
        self.assertEqual(lanes_to_event_priority(Lane.SYNC), EventPriority.DISCRETE)
        self.assertEqual(lanes_to_event_priority(Lane.DRAFT), EventPriority.CONTINUOUS)
        self.assertEqual(lanes_to_event_priority(Lane.BOUNDARY), EventPriority.DEFAULT)
        self.assertEqual(lanes_to_event_priority(Lane.TRANSITION), EventPriority.DEFAULT)
        self.assertEqual(lanes_to_event_priority(Lane.IDLE), EventPriority.IDLE)

    def test_default_event_classification_keeps_business_api_small(self):
        self.assertEqual(priority_for_event("user_edit"), EventPriority.DISCRETE)
        self.assertEqual(priority_for_event("sentence_accepted"), EventPriority.CONTINUOUS)
        self.assertEqual(priority_for_event("scene_boundary"), EventPriority.DEFAULT)
        self.assertEqual(priority_for_event("learn_offline"), EventPriority.IDLE)

    def test_batch_uses_highest_priority_event_for_same_scope(self):
        b = EventBatcher()
        b.push(EventEnvelope(
            "scene_boundary", "scene-1", DirtyDomain.READER,
            generation=1, priority=int(EventPriority.DEFAULT)
        ))
        b.push(EventEnvelope(
            "user_edit", "scene-1", DirtyDomain.CHARACTER,
            generation=2, priority=int(EventPriority.DISCRETE)
        ))
        out = b.flush()[0]
        self.assertEqual(out.priority, int(EventPriority.DISCRETE))
        self.assertEqual(out.generation, 2)
        self.assertTrue(out.dirty & DirtyDomain.READER)
        self.assertTrue(out.dirty & DirtyDomain.CHARACTER)

    def test_independent_scopes_flush_more_urgent_event_first(self):
        b = EventBatcher()
        b.push(EventEnvelope(
            "learn_offline", "book-bg", DirtyDomain.LEARN,
            priority=int(EventPriority.IDLE)
        ))
        b.push(EventEnvelope(
            "user_edit", "scene-now", DirtyDomain.CHARACTER,
            priority=int(EventPriority.DISCRETE)
        ))
        out = b.flush()
        self.assertEqual([x.scope for x in out], ["scene-now", "book-bg"])


class V16LaneRootTests(unittest.TestCase):
    def test_suspended_lane_is_skipped_until_pinged(self):
        root = LaneRootState()
        root.mark_updated(Lane.REACTIVE, now_tick=0)
        root.mark_suspended(Lane.REACTIVE)
        self.assertEqual(root.get_next_lanes(), Lane.NONE)
        root.mark_pinged(Lane.REACTIVE)
        self.assertEqual(root.get_next_lanes(), Lane.REACTIVE)

    def test_lower_priority_update_does_not_interrupt_useful_wip(self):
        root = LaneRootState()
        root.mark_updated(Lane.REACTIVE | Lane.BOUNDARY, now_tick=0)
        self.assertEqual(
            root.get_next_lanes(wip_lanes=Lane.REACTIVE),
            Lane.REACTIVE,
        )

    def test_higher_priority_update_can_interrupt_wip(self):
        root = LaneRootState()
        root.mark_updated(Lane.SYNC | Lane.TRANSITION, now_tick=0)
        self.assertEqual(
            root.get_next_lanes(wip_lanes=Lane.TRANSITION),
            Lane.SYNC,
        )

    def test_entanglement_is_transitive(self):
        root = LaneRootState()
        root.mark_updated(Lane.DRAFT | Lane.REACTIVE | Lane.BOUNDARY)
        root.mark_entangled(Lane.DRAFT | Lane.REACTIVE)
        root.mark_entangled(Lane.REACTIVE | Lane.BOUNDARY)
        got = root.get_entangled_lanes(Lane.DRAFT)
        self.assertEqual(
            got & (Lane.DRAFT | Lane.REACTIVE | Lane.BOUNDARY),
            Lane.DRAFT | Lane.REACTIVE | Lane.BOUNDARY,
        )

    def test_expired_non_suspended_lane_gets_forced_forward(self):
        root = LaneRootState()
        root.mark_updated(Lane.TRANSITION, now_tick=0)
        self.assertEqual(root.expired, Lane.NONE)
        root.mark_starved_lanes_as_expired(now_tick=13)
        self.assertTrue(root.expired & Lane.TRANSITION)
        self.assertEqual(root.get_next_lanes(), Lane.TRANSITION)

    def test_idle_and_offline_do_not_get_lane_expiration_by_default(self):
        root = LaneRootState()
        root.mark_updated(Lane.OFFLINE | Lane.IDLE, now_tick=0)
        root.mark_starved_lanes_as_expired(now_tick=1000)
        self.assertEqual(root.expired & (Lane.OFFLINE | Lane.IDLE), Lane.NONE)

    def test_finished_lanes_clear_only_their_metadata(self):
        root = LaneRootState()
        root.mark_updated(Lane.DRAFT | Lane.TRANSITION, now_tick=0)
        root.mark_entangled(Lane.DRAFT | Lane.TRANSITION)
        root.mark_finished(finished=Lane.DRAFT, remaining=Lane.TRANSITION)
        self.assertEqual(root.pending, Lane.TRANSITION)
        self.assertFalse(root.expired & Lane.DRAFT)
        self.assertNotIn(Lane.DRAFT, root.entanglements)


class V16SchedulerIntegrationTests(unittest.TestCase):
    def test_scheduler_infers_priority_when_caller_does_not_supply_one(self):
        from writerforge.scheduler import SkillScheduler, Priority
        s = SkillScheduler()
        s.enqueue_event(EventEnvelope(
            "sentence_accepted", "scene-1", DirtyDomain.CONTINUITY, generation=1
        ))
        d = s.flush_pending(budget=8, now_tick=0, max_priority=Priority.P1)
        self.assertIn("runtime_guard", d.selected)
        self.assertIn("snapshot_guard", d.selected)

    def test_same_lane_tasks_use_source_event_priority_as_tiebreaker(self):
        from writerforge.lane_scheduler import LaneTask, LaneTaskQueue
        q = LaneTaskQueue()
        q.enqueue(LaneTask(
            "default_reactive", Lane.REACTIVE, 1, "a",
            source_priority=int(EventPriority.DEFAULT)
        ))
        q.enqueue(LaneTask(
            "continuous_reactive", Lane.REACTIVE, 1, "b",
            source_priority=int(EventPriority.CONTINUOUS)
        ))
        out = q.flush(budget=1)
        self.assertEqual(out.selected[0].name, "continuous_reactive")


if __name__ == "__main__":
    unittest.main()
