import unittest

from writerforge.lane_scheduler import Lane
from writerforge.story_work_tree import (
    WorkKind, WorkNode, StoryWorkRoot, StoryWorkLoop,
    create_work_in_progress, find_node,
)


def build_tree():
    book = WorkNode("book", WorkKind.BOOK, memoized_state={"v": 1})
    ch1 = book.append_child(WorkNode("ch1", WorkKind.CHAPTER, memoized_state={"v": 1}))
    ch2 = book.append_child(WorkNode("ch2", WorkKind.CHAPTER, memoized_state={"v": 1}))
    ch1.append_child(WorkNode("s1", WorkKind.SCENE, memoized_state={"text": "A"}))
    s2 = ch2.append_child(WorkNode("s2", WorkKind.SCENE, memoized_state={"text": "B"}))
    return book, s2


class V17StoryWorkTreeTests(unittest.TestCase):
    def test_work_in_progress_uses_two_version_buffer(self):
        current, _ = build_tree()
        first = create_work_in_progress(current)
        self.assertIs(first.alternate, current)
        self.assertIs(current.alternate, first)
        second = create_work_in_progress(current)
        self.assertIs(first, second)

    def test_leaf_update_bubbles_child_lanes_only_through_ancestors(self):
        current, leaf = build_tree()
        root = StoryWorkRoot(current)
        root.schedule_update(leaf, Lane.DRAFT, pending_state={"text": "B2"})

        ch1 = find_node(current, "ch1")
        ch2 = find_node(current, "ch2")
        self.assertEqual(ch1.child_lanes, Lane.NONE)
        self.assertTrue(ch2.child_lanes & Lane.DRAFT)
        self.assertTrue(current.child_lanes & Lane.DRAFT)
        self.assertTrue(leaf.lanes & Lane.DRAFT)

    def test_unrelated_subtree_bails_out(self):
        current, leaf = build_tree()
        root = StoryWorkRoot(current)
        root.schedule_update(leaf, Lane.DRAFT, pending_state={"text": "B2"})

        result = StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
        self.assertIn("ch1", result.bailed_subtrees)
        self.assertNotIn("s1", result.visited)
        self.assertIn("s2", result.visited)

    def test_render_does_not_replace_current_until_outer_commit(self):
        current, leaf = build_tree()
        root = StoryWorkRoot(current)
        root.schedule_update(leaf, Lane.DRAFT, pending_state={"text": "B2"})
        StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)

        self.assertIs(root.current, current)
        self.assertEqual(find_node(root.current, "s2").memoized_state, {"text": "B"})

        adopted = root.adopt_after_commit()
        self.assertIs(root.current, adopted)
        self.assertEqual(find_node(root.current, "s2").memoized_state, {"text": "B2"})

    def test_rejected_candidate_can_discard_wip_without_side_effect(self):
        current, leaf = build_tree()
        root = StoryWorkRoot(current)
        root.schedule_update(leaf, Lane.DRAFT, pending_state={"text": "reject"})
        StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
        root.discard_finished()

        self.assertIs(root.current, current)
        self.assertEqual(find_node(current, "s2").memoized_state, {"text": "B"})

    def test_compute_is_called_only_for_dirty_node(self):
        current, leaf = build_tree()
        root = StoryWorkRoot(current)
        root.schedule_update(leaf, Lane.REACTIVE, pending_state={"text": "B3"})
        calls = []

        def compute(old, wip):
            calls.append(wip.key)
            return wip.pending_state

        StoryWorkLoop().render(root, render_lanes=Lane.REACTIVE, compute=compute)
        self.assertEqual(calls, ["s2"])

    def test_unfinished_other_lane_survives_completion(self):
        current, leaf = build_tree()
        root = StoryWorkRoot(current)
        root.schedule_update(leaf, Lane.DRAFT, pending_state={"text": "B2"})
        root.schedule_update(leaf, Lane.REACTIVE, pending_state={"text": "B3"})

        StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
        root.adopt_after_commit()
        new_leaf = find_node(root.current, "s2")
        self.assertTrue(new_leaf.lanes & Lane.REACTIVE)
        self.assertTrue(root.current.child_lanes & Lane.REACTIVE)
        self.assertTrue(root.lane_state.pending & Lane.REACTIVE)

    def test_alternate_becomes_reusable_after_commit(self):
        current, leaf = build_tree()
        root = StoryWorkRoot(current)
        root.schedule_update(leaf, Lane.DRAFT, pending_state={"text": "B2"})
        StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
        new_current = root.adopt_after_commit()

        old_current = new_current.alternate
        self.assertIsNotNone(old_current)
        next_wip = create_work_in_progress(new_current)
        self.assertIs(next_wip, old_current)


if __name__ == "__main__":
    unittest.main()
