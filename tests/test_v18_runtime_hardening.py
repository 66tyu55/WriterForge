import threading
import unittest

from writerforge import ReactiveSkillRuntime
from writerforge.lane_scheduler import Lane, LaneRootState, DirtyDomain, EventEnvelope, EventBatcher, LaneTask, LaneTaskQueue
from writerforge.story_work_tree import WorkKind, WorkNode, StoryWorkRoot, StoryWorkLoop, find_node


def build_tree():
    book = WorkNode("book", WorkKind.BOOK, memoized_state={"v": 1})
    ch1 = book.append_child(WorkNode("ch1", WorkKind.CHAPTER, memoized_state={"v": 1}))
    ch2 = book.append_child(WorkNode("ch2", WorkKind.CHAPTER, memoized_state={"v": 1}))
    ch1.append_child(WorkNode("s1", WorkKind.SCENE, memoized_state={"text": "A"}))
    s2 = ch2.append_child(WorkNode("s2", WorkKind.SCENE, memoized_state={"text": "B"}))
    return book, s2


class V18WorkTreeHardeningTests(unittest.TestCase):
    def test_lane_specific_updates_do_not_cross_contaminate(self):
        current, leaf = build_tree()
        root = StoryWorkRoot(current)
        root.schedule_update(leaf, Lane.DRAFT, pending_state={"text": "draft"})
        root.schedule_update(leaf, Lane.REACTIVE, pending_state={"text": "reactive"})
        StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
        root.adopt_after_commit()
        leaf = find_node(root.current, "s2")
        self.assertEqual(leaf.memoized_state, {"text": "draft"})
        self.assertTrue(leaf.lanes & Lane.REACTIVE)
        StoryWorkLoop().render(root, render_lanes=Lane.REACTIVE)
        root.adopt_after_commit()
        self.assertEqual(find_node(root.current, "s2").memoized_state, {"text": "reactive"})

    def test_none_is_a_real_pending_state_not_no_update(self):
        current, leaf = build_tree()
        root = StoryWorkRoot(current)
        root.schedule_update(leaf, Lane.DRAFT, pending_state=None)
        StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
        root.adopt_after_commit()
        self.assertIsNone(find_node(root.current, "s2").memoized_state)

    def test_reject_drops_pending_lane_and_speculative_buffer(self):
        current, leaf = build_tree()
        root = StoryWorkRoot(current)
        root.schedule_update(leaf, Lane.DRAFT, pending_state={"text": "reject"})
        StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
        root.discard_finished()
        leaf = find_node(root.current, "s2")
        self.assertEqual(leaf.memoized_state, {"text": "B"})
        self.assertFalse(leaf.lanes & Lane.DRAFT)
        self.assertEqual(leaf.pending_updates, {})
        self.assertIsNone(root.current.alternate)
        self.assertEqual(root.lane_state.pending & Lane.DRAFT, Lane.NONE)

    def test_two_buffer_graph_stays_bounded_across_many_commits(self):
        current, _ = build_tree()
        root = StoryWorkRoot(current)
        loop = StoryWorkLoop()
        for i in range(100):
            leaf = find_node(root.current, "s2")
            root.schedule_update(leaf, Lane.DRAFT, pending_state={"text": str(i)})
            loop.render(root, render_lanes=Lane.DRAFT)
            root.adopt_after_commit()
        seen = set()
        stack = [root.current]
        while stack:
            node = stack.pop()
            if id(node) in seen: continue
            seen.add(id(node))
            if node.child is not None: stack.append(node.child)
            if node.sibling is not None: stack.append(node.sibling)
            if node.alternate is not None: stack.append(node.alternate)
        self.assertLessEqual(len(seen), 10)


class V18CacheHardeningTests(unittest.TestCase):
    def test_scope_versions_are_bounded_without_manual_invalidation(self):
        rt = ReactiveSkillRuntime(max_cache_entries=50, max_versions_per_scope=2)
        for i in range(100):
            rt.compute(skill_name="craft", scope="scene-1", dependencies={"state": i}, fn=lambda i=i: i)
        self.assertLessEqual(rt.cache_size(), 2)
        self.assertLessEqual(rt.dependency_index_size(), 2)

    def test_global_cache_is_bounded(self):
        rt = ReactiveSkillRuntime(max_cache_entries=10, max_versions_per_scope=2)
        for i in range(100):
            rt.compute(skill_name="craft", scope=f"scene-{i}", dependencies={"state": i}, fn=lambda i=i: i)
        self.assertEqual(rt.cache_size(), 10)

    def test_invalidation_during_compute_marks_result_stale_and_does_not_cache(self):
        rt = ReactiveSkillRuntime()
        started, release = threading.Event(), threading.Event()
        holder = {}
        def fn():
            started.set()
            release.wait(timeout=2)
            return "old"
        def worker():
            holder["result"] = rt.compute(skill_name="reader", scope="chapter-1", dependencies={"character": "v1"}, fn=fn)
        t = threading.Thread(target=worker)
        t.start()
        self.assertTrue(started.wait(timeout=2))
        rt.invalidate({"character"})
        release.set()
        t.join(timeout=2)
        self.assertTrue(holder["result"].stale_after_compute)
        self.assertEqual(rt.cache_size(), 0)


class V18QueueAndLaneTests(unittest.TestCase):
    def test_task_queue_releases_generation_scope_when_last_task_finishes(self):
        q = LaneTaskQueue()
        q.enqueue(LaneTask("reader", Lane.TRANSITION, 1, "chapter-1", generation=1))
        q.advance_generation("chapter-1", 2)
        self.assertEqual(q.tracked_scope_count(), 1)
        q.flush(budget=5)
        self.assertEqual(q.pending_count(), 0)
        self.assertEqual(q.tracked_scope_count(), 0)

    def test_event_batcher_memory_scales_by_scope_not_event_count(self):
        b = EventBatcher()
        for i in range(10000):
            b.push(EventEnvelope("state_changed", "scene-1", DirtyDomain.CHARACTER, generation=i, transition_id=f"t{i}"))
        self.assertEqual(b.pending_scope_count(), 1)
        out = b.flush()[0]
        self.assertEqual(out.names, ("state_changed",))
        self.assertEqual(out.generation, 9999)
        self.assertLessEqual(len(out.transition_ids), 16)

    def test_suspended_entangled_lane_blocks_the_group_until_pinged(self):
        root = LaneRootState()
        root.mark_updated(Lane.DRAFT | Lane.REACTIVE)
        root.mark_entangled(Lane.DRAFT | Lane.REACTIVE)
        root.mark_suspended(Lane.REACTIVE)
        self.assertEqual(root.get_next_lanes(), Lane.NONE)
        root.mark_pinged(Lane.REACTIVE)
        self.assertEqual(root.get_next_lanes(), Lane.DRAFT | Lane.REACTIVE)


if __name__ == "__main__":
    unittest.main()
