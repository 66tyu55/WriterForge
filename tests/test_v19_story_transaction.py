import tempfile
import unittest

from writerforge import (
    WriterForgeDB, RuntimeEngine, Mode,
    Lane, WorkKind, WorkNode, StoryWorkRoot, StoryWorkLoop, find_node,
    EffectType, StoryEffect, StoryCommitPlan, StoryCommitCoordinator,
    StoryCommitError,
)


def build_work_root():
    book = WorkNode("book", WorkKind.BOOK, memoized_state={"v": 1})
    scene = book.append_child(WorkNode("scene-1", WorkKind.SCENE, memoized_state={"text": "old"}))
    root = StoryWorkRoot(book)
    root.schedule_update(scene, Lane.DRAFT, pending_state={"text": "new"})
    StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
    return root


def write_runtime():
    rt = RuntimeEngine()
    rt.enter_write(1)
    return rt


class V19StoryTransactionTests(unittest.TestCase):
    def test_effect_bundle_and_receipt_commit_atomically_then_adopt(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db = WriterForgeDB(f.name)
            root = build_work_root()
            plan = StoryCommitPlan(
                project_id="p1",
                commit_id="c1",
                work_fingerprint=root.finished_fingerprint(),
                effects=(
                    StoryEffect(EffectType.SET_CHARACTER, "hero", {"state": {"knowledge": ["secret"]}}),
                    StoryEffect(EffectType.SET_PROMISE, "p-1", {"payload": {"question": "who?"}, "status": "open"}),
                    StoryEffect(EffectType.SET_READER_STATE, "reader", {"state": {"suspects": ["hero"]}}),
                    StoryEffect(EffectType.ACCEPT_PROSE, "scene-1", {"body": "accepted text"}),
                ),
            )
            result = StoryCommitCoordinator(db, write_runtime()).commit(plan, work_root=root)
            self.assertTrue(result.committed)
            self.assertTrue(result.adopted_work_tree)
            self.assertEqual(find_node(root.current, "scene-1").memoized_state, {"text": "new"})
            self.assertEqual(db.conn.execute("SELECT COUNT(*) c FROM story_commit_receipts").fetchone()["c"], 1)
            self.assertEqual(db.conn.execute("SELECT COUNT(*) c FROM story_effect_journal").fetchone()["c"], 4)
            self.assertEqual(db.conn.execute("SELECT body FROM accepted_prose").fetchone()["body"], "accepted text")
            self.assertIsNotNone(db.conn.execute("SELECT 1 FROM character_state WHERE character_id='hero'").fetchone())
            self.assertIsNotNone(db.conn.execute("SELECT 1 FROM promises WHERE promise_id='p-1'").fetchone())
            db.close()

    def test_same_commit_same_bundle_is_durable_idempotent_replay(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db = WriterForgeDB(f.name)
            rt = write_runtime()
            plan = StoryCommitPlan(
                "p1", "same",
                (StoryEffect(EffectType.ACCEPT_PROSE, "scene-1", {"body": "x"}),),
            )
            c1 = StoryCommitCoordinator(db, rt)
            a = c1.commit(plan)
            b = StoryCommitCoordinator(db, rt).commit(plan)
            self.assertTrue(a.committed)
            self.assertFalse(b.committed)
            self.assertTrue(b.replayed)
            row = db.conn.execute("SELECT revision FROM accepted_prose WHERE project_id='p1' AND scope_id='scene-1'").fetchone()
            self.assertEqual(row["revision"], 1)
            self.assertEqual(db.conn.execute("SELECT COUNT(*) c FROM story_effect_journal").fetchone()["c"], 1)
            db.close()

    def test_same_commit_id_different_bundle_is_rejected(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db = WriterForgeDB(f.name)
            c = StoryCommitCoordinator(db, write_runtime())
            a = StoryCommitPlan("p1", "id", (StoryEffect(EffectType.ACCEPT_PROSE, "s", {"body": "a"}),))
            b = StoryCommitPlan("p1", "id", (StoryEffect(EffectType.ACCEPT_PROSE, "s", {"body": "b"}),))
            c.commit(a)
            with self.assertRaises(StoryCommitError):
                c.commit(b)
            self.assertEqual(db.conn.execute("SELECT body FROM accepted_prose").fetchone()["body"], "a")
            db.close()

    def test_mid_transaction_failure_rolls_back_every_effect_and_keeps_current_tree(self):
        class FailingCoordinator(StoryCommitCoordinator):
            def __init__(self, db, runtime):
                super().__init__(db, runtime)
                self.n = 0
            def _apply_effect(self, conn, project_id, effect):
                self.n += 1
                super()._apply_effect(conn, project_id, effect)
                if self.n == 1:
                    raise RuntimeError("boom")

        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db = WriterForgeDB(f.name)
            root = build_work_root()
            old_current = root.current
            plan = StoryCommitPlan(
                "p1", "rollback",
                (
                    StoryEffect(EffectType.SET_CHARACTER, "hero", {"state": {"x": 1}}),
                    StoryEffect(EffectType.ACCEPT_PROSE, "scene-1", {"body": "never"}),
                ),
                root.finished_fingerprint(),
            )
            with self.assertRaises(RuntimeError):
                FailingCoordinator(db, write_runtime()).commit(plan, work_root=root)

            self.assertIs(root.current, old_current)
            self.assertEqual(db.conn.execute("SELECT COUNT(*) c FROM character_state").fetchone()["c"], 0)
            self.assertEqual(db.conn.execute("SELECT COUNT(*) c FROM accepted_prose").fetchone()["c"], 0)
            self.assertEqual(db.conn.execute("SELECT COUNT(*) c FROM story_commit_receipts").fetchone()["c"], 0)
            self.assertIsNone(root.finished_work)
            # pending update survives for a retry
            self.assertTrue(find_node(root.current, "scene-1").lanes & Lane.DRAFT)
            db.close()

    def test_work_fingerprint_prevents_adopting_wrong_finished_tree(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db = WriterForgeDB(f.name)
            root = build_work_root()
            plan = StoryCommitPlan(
                "p1", "wrong-work",
                (StoryEffect(EffectType.ACCEPT_PROSE, "scene-1", {"body": "x"}),),
                "not-the-finished-tree",
            )
            with self.assertRaises(StoryCommitError):
                StoryCommitCoordinator(db, write_runtime()).commit(plan, work_root=root)
            self.assertEqual(db.conn.execute("SELECT COUNT(*) c FROM story_commit_receipts").fetchone()["c"], 0)
            db.close()

    def test_duplicate_effect_target_is_rejected_before_business_mutation(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db = WriterForgeDB(f.name)
            plan = StoryCommitPlan(
                "p1", "dup",
                (
                    StoryEffect(EffectType.SET_CHARACTER, "hero", {"state": {"x": 1}}),
                    StoryEffect(EffectType.SET_CHARACTER, "hero", {"state": {"x": 2}}),
                ),
            )
            with self.assertRaises(StoryCommitError):
                StoryCommitCoordinator(db, write_runtime()).commit(plan)
            self.assertEqual(db.conn.execute("SELECT COUNT(*) c FROM character_state").fetchone()["c"], 0)
            self.assertEqual(db.conn.execute("SELECT COUNT(*) c FROM story_commit_receipts").fetchone()["c"], 0)
            db.close()

    def test_immutable_canon_requires_patch_effect(self):
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            db = WriterForgeDB(f.name)
            rt = write_runtime()
            c = StoryCommitCoordinator(db, rt)
            c.commit(StoryCommitPlan(
                "p1", "canon-1",
                (StoryEffect(EffectType.UPSERT_CANON, "fact", {"statement": "A", "status": "immutable"}),),
            ))
            with self.assertRaises(Exception):
                c.commit(StoryCommitPlan(
                    "p1", "canon-2",
                    (StoryEffect(EffectType.UPSERT_CANON, "fact", {"statement": "B", "status": "immutable"}),),
                ))
            c.commit(StoryCommitPlan(
                "p1", "canon-3",
                (StoryEffect(EffectType.PATCH_CANON, "fact", {"statement": "B", "reason": "approved retcon"}),),
            ))
            self.assertEqual(db.conn.execute("SELECT statement FROM canon WHERE canon_id='fact'").fetchone()["statement"], "B")
            db.close()


if __name__ == "__main__":
    unittest.main()
