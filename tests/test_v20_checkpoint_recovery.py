"""V20: crash-safe recovery and WorkTree commit-window regression tests."""
from pathlib import Path
import tempfile
import unittest

from writerforge import (
    WriterForgeDB, RuntimeEngine, Lane, WorkKind, WorkNode,
    StoryWorkRoot, StoryWorkLoop, find_node,
    EffectType, StoryEffect, StoryCommitPlan, StoryCommitCoordinator,
    StoryCommitError, PostCommitAdoptionError,
    WorkTreeCheckpointError, restore_work_root,
)


def runtime():
    instance = RuntimeEngine()
    instance.enter_write(1)
    return instance


def new_tree():
    book = WorkNode("book", WorkKind.BOOK, memoized_state={"title": "山河"})
    chapter_1 = book.append_child(WorkNode("chapter-1", WorkKind.CHAPTER, memoized_state={"no": 1}))
    chapter_2 = book.append_child(WorkNode("chapter-2", WorkKind.CHAPTER, memoized_state={"no": 2}))
    chapter_1.append_child(WorkNode("scene-1", WorkKind.SCENE, memoized_state={"body": "旧句"}))
    chapter_2.append_child(WorkNode("scene-2", WorkKind.SCENE, memoized_state={"body": "旧章"}))
    return StoryWorkRoot(book)


def plan_for(root, commit_id, text="文字"):
    return StoryCommitPlan(
        project_id="novel",
        commit_id=commit_id,
        work_fingerprint=root.finished_fingerprint(),
        effects=(StoryEffect(EffectType.ACCEPT_PROSE, "scene-1", {"body": text}),),
    )


def render_scene(root, scene, text, lane=Lane.DRAFT):
    node = find_node(root.current, scene)
    root.schedule_update(node, lane, pending_state={"body": text})
    StoryWorkLoop().render(root, render_lanes=lane)


class V20WorkTreeRecoveryTests(unittest.TestCase):
    def test_roundtrip_restart_recovers_tree_topology_and_pending_lane(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "book.sqlite3"
            db = WriterForgeDB(file)
            root = new_tree()
            root.schedule_update(find_node(root.current, "scene-1"), Lane.DRAFT, pending_state={"body": "新句"})
            root.schedule_update(find_node(root.current, "scene-2"), Lane.REACTIVE, pending_state={"body": "后续"})
            StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
            result = StoryCommitCoordinator(db, runtime()).commit(plan_for(root, "c1", "新句"), work_root=root)
            self.assertTrue(result.committed)
            self.assertTrue(result.adopted_work_tree)
            self.assertEqual(root.durable_commit_id, "c1")
            db.close()

            reopened = WriterForgeDB(file)
            restored = restore_work_root(reopened, "novel")
            self.assertEqual(restored.durable_commit_id, "c1")
            self.assertEqual(find_node(restored.current, "scene-1").memoized_state["body"], "新句")
            self.assertEqual(find_node(restored.current, "scene-2").memoized_state["body"], "旧章")
            self.assertEqual(find_node(restored.current, "scene-1").parent.key, "chapter-1")
            self.assertEqual(find_node(restored.current, "scene-2").parent.key, "chapter-2")
            self.assertIsNone(restored.current.alternate)
            self.assertIsNone(restored.finished_work)
            self.assertTrue(restored.lane_state.pending & Lane.REACTIVE)
            self.assertEqual(
                find_node(restored.current, "scene-2").pending_updates[Lane.REACTIVE].state,
                {"body": "后续"},
            )

            StoryWorkLoop().render(restored, render_lanes=Lane.REACTIVE)
            second = StoryCommitPlan(
                "novel", "c2",
                (StoryEffect(EffectType.ACCEPT_PROSE, "scene-2", {"body": "后续"}),),
                restored.finished_fingerprint(),
            )
            StoryCommitCoordinator(reopened, runtime()).commit(second, work_root=restored)
            self.assertEqual(restored.lane_state.pending, Lane.NONE)
            self.assertEqual(
                reopened.conn.execute(
                    "SELECT COUNT(*) c FROM story_work_checkpoints WHERE project_id='novel'"
                ).fetchone()["c"], 1,
            )
            reopened.close()
            check = WriterForgeDB(file)
            self.assertEqual(
                find_node(restore_work_root(check, "novel").current, "scene-2").memoized_state,
                {"body": "后续"},
            )
            check.close()

    def test_postcommit_adoption_failure_is_recoverable_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "book.sqlite3"
            db = WriterForgeDB(file)
            root = new_tree()
            render_scene(root, "scene-1", "已接受")
            plan = plan_for(root, "adoption-crash", "已接受")

            def fail_adoption():
                raise RuntimeError("simulated failure after SQLite COMMIT")

            root.adopt_after_commit = fail_adoption
            with self.assertRaises(PostCommitAdoptionError) as caught:
                StoryCommitCoordinator(db, runtime()).commit(plan, work_root=root)
            self.assertTrue(caught.exception.durable_committed)
            db.close()

            reopened = WriterForgeDB(file)
            recovered = restore_work_root(reopened, "novel")
            self.assertEqual(find_node(recovered.current, "scene-1").memoized_state, {"body": "已接受"})
            replay = StoryCommitCoordinator(reopened, runtime()).commit(plan)
            self.assertTrue(replay.replayed)
            self.assertFalse(replay.committed)
            self.assertEqual(
                reopened.conn.execute(
                    "SELECT revision FROM accepted_prose WHERE project_id='novel' AND scope_id='scene-1'"
                ).fetchone()["revision"], 1,
            )
            reopened.close()

    def test_failed_effect_transaction_keeps_previous_checkpoint(self):
        class RejectingCoordinator(StoryCommitCoordinator):
            def _apply_effect(self, conn, project_id, effect):
                super()._apply_effect(conn, project_id, effect)
                raise RuntimeError("mid-transaction error")

        with tempfile.TemporaryDirectory() as folder:
            db = WriterForgeDB(Path(folder) / "book.sqlite3")
            root = new_tree()
            render_scene(root, "scene-1", "A")
            StoryCommitCoordinator(db, runtime()).commit(plan_for(root, "c1", "A"), work_root=root)
            old = db.conn.execute(
                "SELECT tree_hash FROM story_work_checkpoints WHERE project_id='novel'"
            ).fetchone()["tree_hash"]
            render_scene(root, "scene-1", "B")
            with self.assertRaises(RuntimeError):
                RejectingCoordinator(db, runtime()).commit(plan_for(root, "c2", "B"), work_root=root)
            self.assertEqual(
                db.conn.execute("SELECT tree_hash FROM story_work_checkpoints").fetchone()["tree_hash"],
                old,
            )
            self.assertEqual(
                db.conn.execute("SELECT COUNT(*) c FROM story_commit_receipts").fetchone()["c"], 1,
            )
            self.assertEqual(find_node(restore_work_root(db, "novel").current, "scene-1").memoized_state,
                             {"body": "A"})
            db.close()

    def test_corrupt_snapshot_is_detected_not_silently_loaded(self):
        with tempfile.TemporaryDirectory() as folder:
            db = WriterForgeDB(Path(folder) / "book.sqlite3")
            root = new_tree()
            render_scene(root, "scene-1", "A")
            StoryCommitCoordinator(db, runtime()).commit(plan_for(root, "c1"), work_root=root)
            db.conn.execute(
                "UPDATE story_work_checkpoints SET tree_json='{}' WHERE project_id='novel'"
            )
            db.conn.commit()
            with self.assertRaisesRegex(WorkTreeCheckpointError, "checksum"):
                restore_work_root(db, "novel")
            db.close()

    def test_rootless_story_commit_invalidates_older_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            db = WriterForgeDB(Path(folder) / "book.sqlite3")
            root = new_tree()
            render_scene(root, "scene-1", "A")
            coordinator = StoryCommitCoordinator(db, runtime())
            coordinator.commit(plan_for(root, "c1"), work_root=root)
            coordinator.commit(StoryCommitPlan(
                "novel", "bare", (StoryEffect(EffectType.SET_CHARACTER, "hero", {"state": {"age": 20}}),)
            ))
            with self.assertRaisesRegex(WorkTreeCheckpointError, "no WorkTree checkpoint"):
                restore_work_root(db, "novel")
            db.close()

    def test_stale_restored_root_cannot_replace_newer_story(self):
        with tempfile.TemporaryDirectory() as folder:
            db = WriterForgeDB(Path(folder) / "book.sqlite3")
            root = new_tree()
            render_scene(root, "scene-1", "A")
            coordinator = StoryCommitCoordinator(db, runtime())
            coordinator.commit(plan_for(root, "c1"), work_root=root)
            recovered = restore_work_root(db, "novel")
            coordinator.commit(StoryCommitPlan(
                "novel", "c2", (StoryEffect(EffectType.SET_CHARACTER, "hero", {"state": {"age": 25}}),)
            ))
            render_scene(recovered, "scene-1", "B")
            with self.assertRaisesRegex(StoryCommitError, "stale WorkTree"):
                coordinator.commit(plan_for(recovered, "c3", "B"), work_root=recovered)
            self.assertEqual(
                db.conn.execute("SELECT COUNT(*) c FROM story_commit_receipts").fetchone()["c"], 2,
            )
            db.close()

    def test_non_head_replay_never_adopts_stale_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            db = WriterForgeDB(Path(folder) / "book.sqlite3")
            root = new_tree()
            render_scene(root, "scene-1", "A")
            p1 = plan_for(root, "c1", "A")
            coordinator = StoryCommitCoordinator(db, runtime())
            coordinator.commit(p1, work_root=root)
            coordinator.commit(StoryCommitPlan(
                "novel", "c2", (StoryEffect(EffectType.SET_CHARACTER, "hero", {"state": {"age": 25}}),)
            ))
            replay_candidate = new_tree()
            render_scene(replay_candidate, "scene-1", "A")
            with self.assertRaisesRegex(StoryCommitError, "non-head"):
                coordinator.commit(p1, work_root=replay_candidate)
            self.assertEqual(
                db.conn.execute("SELECT COUNT(*) c FROM story_commit_receipts").fetchone()["c"], 2,
            )
            db.close()

    def test_schedule_after_render_must_not_lose_new_update(self):
        root = new_tree()
        render_scene(root, "scene-1", "first")
        before = root.finished_fingerprint()
        with self.assertRaisesRegex(RuntimeError, "awaiting commit/reject"):
            root.schedule_update(
                find_node(root.current, "scene-1"), Lane.DRAFT,
                pending_state={"body": "second"},
            )
        self.assertEqual(root.finished_fingerprint(), before)
        root.discard_finished(drop_rendered_updates=False)
        render_scene(root, "scene-1", "second")
        self.assertNotEqual(root.finished_fingerprint(), before)

    def test_recovered_root_cannot_commit_to_another_project(self):
        with tempfile.TemporaryDirectory() as folder:
            db = WriterForgeDB(Path(folder) / "book.sqlite3")
            root = new_tree()
            render_scene(root, "scene-1", "A")
            coordinator = StoryCommitCoordinator(db, runtime())
            coordinator.commit(plan_for(root, "c1", "A"), work_root=root)
            restored = restore_work_root(db, "novel")
            render_scene(restored, "scene-1", "B")
            wrong = StoryCommitPlan(
                "another-novel", "c2",
                (StoryEffect(EffectType.ACCEPT_PROSE, "scene-1", {"body": "B"}),),
                restored.finished_fingerprint(),
            )
            with self.assertRaisesRegex(StoryCommitError, "different project"):
                coordinator.commit(wrong, work_root=restored)
            self.assertEqual(
                db.conn.execute(
                    "SELECT COUNT(*) c FROM story_commit_receipts WHERE project_id='another-novel'"
                ).fetchone()["c"], 0,
            )
            db.close()

    def test_foreign_node_schedule_does_not_mutate_other_tree(self):
        first = new_tree()
        second = new_tree()
        foreign_scene = find_node(second.current, "scene-1")
        with self.assertRaisesRegex(ValueError, "does not belong"):
            first.schedule_update(foreign_scene, Lane.DRAFT, pending_state={"body": "wrong"})
        self.assertEqual(foreign_scene.lanes, Lane.NONE)
        self.assertEqual(foreign_scene.pending_updates, {})
        self.assertEqual(second.current.child_lanes, Lane.NONE)
        self.assertEqual(first._update_sequence, 0)
        self.assertEqual(first.lane_state.pending, Lane.NONE)

    def test_render_exception_discards_wip_without_consuming_pending_update(self):
        root = new_tree()
        root.schedule_update(
            find_node(root.current, "scene-1"), Lane.DRAFT,
            pending_state={"body": "retry"},
        )

        def failing_compute(old, wip):
            raise RuntimeError("injected compute error")

        with self.assertRaisesRegex(RuntimeError, "compute error"):
            StoryWorkLoop().render(root, render_lanes=Lane.DRAFT, compute=failing_compute)
        self.assertIsNone(root.work_in_progress)
        self.assertIsNone(root.finished_work)
        self.assertIsNone(root.current.alternate)
        self.assertTrue(find_node(root.current, "scene-1").lanes & Lane.DRAFT)
        self.assertTrue(root.lane_state.pending & Lane.DRAFT)

        # A fresh render succeeds without rescheduling or leaking a stale alternate.
        StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
        root.adopt_after_commit()
        self.assertEqual(find_node(root.current, "scene-1").memoized_state,
                         {"body": "retry"})

    def test_non_json_state_fails_before_any_durable_write(self):
        with tempfile.TemporaryDirectory() as folder:
            db = WriterForgeDB(Path(folder) / "book.sqlite3")
            root = new_tree()
            render_scene(root, "scene-1", {"unserializable"})  # set is not JSON-native
            with self.assertRaises(WorkTreeCheckpointError):
                StoryCommitCoordinator(db, runtime()).commit(plan_for(root, "c1"), work_root=root)
            self.assertEqual(
                db.conn.execute("SELECT COUNT(*) c FROM story_commit_receipts").fetchone()["c"], 0,
            )
            db.close()


if __name__ == "__main__":
    unittest.main()
