"""V21: writer-companion growth must be passive, durable and evidence-aware."""
import json
from pathlib import Path
import tempfile
import unittest

from writerforge import (
    WriterForgeDB, RuntimeEngine, WritingCompanion, CompanionEvidenceError,
    WritingFlow, AuthorCorrection,
    EffectType, StoryEffect, StoryCommitPlan, StoryCommitCoordinator,
    WorkNode, WorkKind, StoryWorkRoot, StoryWorkLoop, Lane, find_node,
)


def runtime():
    rt = RuntimeEngine()
    rt.enter_write(1)
    return rt


def prose(target, text, origin=None):
    payload = {"body": text}
    if origin is not None:
        payload["origin"] = origin
    return StoryEffect(EffectType.ACCEPT_PROSE, target, payload)


def rule(key, guidance="", *, direction="prefer", category="general", action="set"):
    payload = {"action": action}
    if action == "set":
        payload.update(guidance=guidance, direction=direction, category=category)
    return StoryEffect(EffectType.SET_AUTHOR_PREFERENCE, key, payload)


class GrowingCompanionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "novel.sqlite3"
        self.db = WriterForgeDB(self.path)
        self.coordinator = StoryCommitCoordinator(self.db, runtime())

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def commit(self, commit_id, *effects, project="novel", work_root=None):
        plan = StoryCommitPlan(
            project, commit_id, tuple(effects),
            work_root.finished_fingerprint() if work_root is not None else None,
        )
        return self.coordinator.commit(plan, work_root=work_root)

    def row(self, project="novel"):
        return self.db.conn.execute(
            "SELECT * FROM writer_companion_profiles WHERE project_id=?", (project,),
        ).fetchone()

    def test_passive_growth_only_after_accepted_text(self):
        companion = WritingCompanion(self.db, "novel")
        cold = companion.before_draft("s1")
        self.assertEqual(cold.voice_origin, "insufficient")
        self.assertEqual(cold.accepted_revisions, 0)
        self.commit("a1", prose("s1", "那扇门静静立着。"))
        observed = companion.before_draft("s2")
        self.assertEqual(observed.accepted_revisions, 1)
        self.assertEqual(observed.authored_revisions, 0)
        self.assertEqual(observed.voice_origin, "insufficient")
        self.assertNotEqual(observed.fingerprint, cold.fingerprint)

    def test_assistant_generated_text_does_not_create_author_voice(self):
        for i in range(5):
            self.commit(f"a{i}", prose(f"s{i}", f"我写了一段生成文本{i}。", "assistant_generated"))
        context = WritingCompanion(self.db, "novel").before_draft("next")
        self.assertEqual(context.accepted_revisions, 5)
        self.assertEqual(context.authored_revisions, 0)
        self.assertEqual(context.voice_origin, "accepted")
        self.assertIn("弱观察", context.compact_context())
        self.assertNotIn("已验证作者", context.compact_context())

    def test_author_edited_text_has_stronger_evidence_after_multiple_edits(self):
        self.commit("a1", prose("s1", "雨沿着屋檐滑下来。他没有说话。", "author_edited"))
        self.commit("a2", prose("s2", "她抬头。屋里的人都在等这个答案。", "author_written"))
        context = WritingCompanion(self.db, "novel").before_draft("s3")
        self.assertEqual(context.voice_origin, "author")
        self.assertEqual(context.authored_revisions, 2)
        self.assertGreater(context.voice_metrics["avg_sentence_chars"], 0)
        self.assertIn("已验证作者写作节奏", context.compact_context())

    def test_same_body_new_receipt_is_not_new_growth_evidence(self):
        self.commit("a1", prose("s1", "门关了。", "author_written"))
        self.commit("a2", prose("s1", "门关了。", "author_written"))
        self.assertEqual(self.row()["accepted_revisions"], 1)
        self.assertEqual(self.row()["authored_revisions"], 1)
        # Existing accepted-prose business revision semantics remain unchanged.
        row = self.db.conn.execute(
            "SELECT revision FROM accepted_prose WHERE project_id='novel'"
        ).fetchone()
        self.assertEqual(row["revision"], 2)

    def test_receipt_replay_never_double_trains(self):
        effect = prose("s1", "微风吹过空街。", "author_edited")
        self.commit("same", effect)
        duplicate = self.commit("same", effect)
        self.assertTrue(duplicate.replayed)
        self.assertEqual(self.row()["accepted_revisions"], 1)
        self.assertEqual(self.row()["authored_revisions"], 1)

    def test_author_feedback_changes_next_scene_without_copied_prose(self):
        companion = WritingCompanion(self.db, "novel")
        self.commit(
            "feedback",
            rule("avoid_explaining", "不在对白后重复解释人物情绪",
                 direction="avoid", category="dialogue"),
            rule("natural_environment", "环境反应随着人物行动自然发生",
                 category="description"),
        )
        dialogue = companion.before_draft("scene-2", concerns=("dialogue",))
        self.assertEqual(len(dialogue.guidance), 1)
        self.assertIn("避免：", dialogue.guidance[0])
        self.assertNotIn("环境反应", dialogue.compact_context())
        description = companion.before_draft("scene-3", concerns=("description",))
        self.assertEqual(len(description.guidance), 1)
        self.assertIn("环境反应", description.compact_context())
        self.assertEqual(description.authored_revisions, 0)
        self.assertLessEqual(len(description.compact_context()), 768)

    def test_feedback_can_be_updated_and_forgotten_without_unbounded_history(self):
        self.commit("r1", rule("pace", "短句优先", category="pacing"))
        self.commit("r2", rule("pace", "句式随叙事功能变化", category="pacing"))
        companion = WritingCompanion(self.db, "novel")
        self.assertIn("句式随", companion.before_draft("s2", concerns=("pacing",)).compact_context())
        self.assertNotIn("短句优先", companion.before_draft("s2", concerns=("pacing",)).compact_context())
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM writer_companion_preferences"
        ).fetchone()["n"], 1)
        self.commit("r3", rule("pace", action="remove"))
        context = companion.before_draft("s2", concerns=("pacing",))
        self.assertEqual(context.guidance, ())
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM writer_companion_preferences"
        ).fetchone()["n"], 0)

    def test_version_probe_and_bounded_context_cache(self):
        companion = WritingCompanion(self.db, "novel", max_cached_contexts=3)
        first = companion.before_draft("s1")
        second = companion.before_draft("s1")
        self.assertIs(first, second)
        self.assertEqual(companion.profile_loads, 1)
        self.assertEqual(companion.cache_hits, 1)
        for n in range(20):
            companion.before_draft(f"scene-{n}")
        self.assertEqual(companion.profile_loads, 1)
        self.assertLessEqual(companion.cached_context_count, 3)
        self.commit("a1", prose("scene-new", "他推开窗。"))
        updated = companion.before_draft("s1")
        self.assertEqual(companion.profile_loads, 2)
        self.assertNotEqual(updated.fingerprint, first.fingerprint)
        self.assertLessEqual(companion.cached_context_count, 3)

    def test_project_isolation_and_restart(self):
        self.commit("a1", prose("s1", "他缓缓举起灯笼。", "author_edited"))
        self.commit("r1", rule("dialogue", "对白不做说明书", category="dialogue"))
        self.commit("b1", prose("s1", "B书的句子。", "author_written"), project="another")
        self.db.close()
        self.db = WriterForgeDB(self.path)
        self.coordinator = StoryCommitCoordinator(self.db, runtime())
        a = WritingCompanion(self.db, "novel").before_draft("next", concerns=("dialogue",))
        b = WritingCompanion(self.db, "another").before_draft("next", concerns=("dialogue",))
        self.assertEqual(a.accepted_revisions, 1)
        self.assertEqual(b.accepted_revisions, 1)
        self.assertEqual(a.authored_revisions, 1)
        self.assertEqual(b.authored_revisions, 1)
        self.assertEqual(len(a.guidance), 1)
        self.assertEqual(len(b.guidance), 0)

    def test_failed_transaction_cannot_leak_growth(self):
        class FailAfterFirst(StoryCommitCoordinator):
            def _apply_effect(self, conn, project_id, effect):
                super()._apply_effect(conn, project_id, effect)
                raise RuntimeError("crash before sqlite commit")

        plan = StoryCommitPlan(
            "novel", "will-fail",
            (prose("s1", "落笔成章。", "author_edited"),),
        )
        with self.assertRaisesRegex(RuntimeError, "crash"):
            FailAfterFirst(self.db, runtime()).commit(plan)
        self.assertIsNone(self.row())
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM story_commit_receipts"
        ).fetchone()["n"], 0)

    def test_rejected_work_tree_does_not_grow_companion(self):
        book = WorkNode("book", WorkKind.BOOK, memoized_state={"x": 1})
        scene = book.append_child(WorkNode("s1", WorkKind.SCENE, memoized_state={"body": "x"}))
        root = StoryWorkRoot(book)
        root.schedule_update(scene, Lane.DRAFT, pending_state={"body": "unaccepted"})
        StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
        root.discard_finished()
        self.assertIsNone(self.row())

    def test_invalid_feedback_rolls_back_staged_prose_as_one_bundle(self):
        plan = StoryCommitPlan("novel", "invalid", (
            prose("s1", "句子。"),
            rule("vague", "", category="voice"),
        ))
        with self.assertRaises(CompanionEvidenceError):
            self.coordinator.commit(plan)
        self.assertEqual(
            self.db.conn.execute("SELECT COUNT(*) AS n FROM accepted_prose").fetchone()["n"], 0
        )
        self.assertIsNone(self.row())

    def test_cap_enforced_no_silent_eviction(self):
        for n in range(64):
            self.commit(f"rule-{n}", rule(f"key-{n}", f"Guidance {n}"))
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM writer_companion_preferences"
        ).fetchone()["n"], 64)
        with self.assertRaisesRegex(CompanionEvidenceError, "capacity"):
            self.commit("overflow", rule("extra", "No overwrite"))
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM story_commit_receipts"
        ).fetchone()["n"], 64)
        self.commit("replace", rule("key-0", "Replacement"))
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM writer_companion_preferences"
        ).fetchone()["n"], 64)

    def test_long_text_is_sampled_not_stored_again(self):
        big_text = "他沿长街而行。" * 5000
        self.commit("large", prose("scene", big_text, "author_written"))
        row = self.row()
        self.assertLessEqual(row["sampled_chars"], 8192)
        self.assertEqual(row["accepted_revisions"], 1)
        self.assertNotIn("他沿长街", json.dumps(dict(row)))
        context = WritingCompanion(self.db, "novel").before_draft("next")
        self.assertLessEqual(len(context.compact_context()), 768)

    def test_feedback_only_commit_can_create_companion_profile(self):
        self.commit("rule", rule("avoid_adverbs", "少用套话", category="voice"))
        self.assertEqual(self.row()["accepted_revisions"], 0)
        self.assertEqual(self.row()["version"], 1)

    def test_mode_guard_prevents_learn_mutating_companion(self):
        rt = RuntimeEngine()
        rt.enter_learn()
        with self.assertRaises(Exception):
            StoryCommitCoordinator(self.db, rt).commit(
                StoryCommitPlan("novel", "invalid-mode", (rule("x", "xxx"),))
            )
        self.assertIsNone(self.row())


if __name__ == "__main__":
    unittest.main()
