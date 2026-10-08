"""V22 adoption tests: author-curated evidence, one rules authority, no rewrite."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from writerforge import (
    WriterForgeDB, RuntimeEngine, WritingFlow, WritingCompanion,
    AuthorCorrection, CompanionEvidenceError,
    StoryCommitPlan, StoryEffect, EffectType, StoryCommitCoordinator,
    StoryWorkRoot, StoryWorkLoop, WorkNode, WorkKind, Lane, find_node,
)


def write_runtime():
    rt = RuntimeEngine()
    rt.enter_write(1)
    return rt


def accepted(scene: str, body: str):
    return StoryEffect(EffectType.ACCEPT_PROSE, scene, {"body": body, "origin": "author_edited"})


def rule(key: str, guidance: str, *, category="general", **metadata):
    return StoryEffect(EffectType.SET_AUTHOR_PREFERENCE, key, {
        "guidance": guidance, "category": category, "direction": "prefer",
        **metadata,
    })


class ExternalLessonsIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "writer.db"
        self.db = WriterForgeDB(self.path)
        self.runtime = write_runtime()
        self.coordinator = StoryCommitCoordinator(self.db, self.runtime)
        self.flow = WritingFlow(self.db, self.runtime, "p1")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def commit(self, identifier, *effects, project="p1", root=None):
        return self.coordinator.commit(StoryCommitPlan(
            project, identifier, tuple(effects),
            root.finished_fingerprint() if root else None,
        ), work_root=root)

    def test_same_bundle_author_evidence_is_accepted_after_prose(self):
        body = "他靠在门边，却没有立刻询问。雨落进廊下。"
        result = self.flow.accept_draft(
            "c1", "s1", body, origin="author_edited",
            corrections=(
                AuthorCorrection(
                    "quiet_emotion", "让情绪留在人物动作里",
                    category="description", axis="character_emotion",
                    conflict_group="emotion_expression",
                    evidence_scope="s1", evidence_excerpt="却没有立刻询问",
                ),
            ),
        )
        self.assertTrue(result.committed)
        frame = self.flow.begin_draft("s2", concerns=("description",))
        self.assertIn("让情绪留在人物动作里", frame.companion_guidance)
        review = self.flow.review_writing_sheet()
        self.assertEqual(review["evidence"], (
            {"key": "quiet_emotion", "status": "verified", "scope": "s1"},
        ))
        self.assertEqual(
            review["axes"]["character_emotion"][0]["guidance"],
            "让情绪留在人物动作里",
        )
        self.assertEqual(review["axes"]["plot"], ())

        row = self.db.conn.execute(
            """SELECT evidence_body_hash,evidence_excerpt_hash,evidence_scope,axis
               FROM writer_companion_preferences WHERE project_id='p1'"""
        ).fetchone()
        self.assertEqual(row["evidence_scope"], "s1")
        self.assertEqual(row["axis"], "character_emotion")
        self.assertEqual(len(row["evidence_body_hash"]), 64)
        self.assertEqual(len(row["evidence_excerpt_hash"]), 64)

    def test_stale_anchor_retracts_guidance_without_mutating_accepted_prose(self):
        self.commit("c1", accepted("s1", "青灯下，她握紧衣角。"))
        self.commit("c2", rule("detail", "用人物动作承载情绪",
                               category="description", axis="language",
                               evidence_scope="s1", evidence_excerpt="握紧衣角"))
        self.commit("c3", rule("general", "保持自然叙事节奏"))
        before = self.flow.begin_draft("next", concerns=("description",))
        self.assertIn("用人物动作承载情绪", before.companion_guidance)
        self.commit("c4", accepted("s1", "她放开衣角，转身离开。"))
        after = self.flow.begin_draft("next", concerns=("description",))
        self.assertNotIn("用人物动作承载情绪", after.companion_guidance)
        self.assertIn("保持自然叙事节奏", after.companion_guidance)
        review = self.flow.review_writing_sheet()
        self.assertEqual(review["evidence"], (
            {"key": "detail", "status": "stale", "scope": "s1"},
            {"key": "general", "status": "explicit", "scope": None},
        ))
        self.assertEqual(review["axes"]["language"], ())
        self.assertEqual(self.db.conn.execute(
            "SELECT body FROM accepted_prose WHERE project_id='p1' AND scope_id='s1'"
        ).fetchone()["body"], "她放开衣角，转身离开。")

    def test_bad_evidence_causes_atomic_rollback(self):
        with self.assertRaisesRegex(CompanionEvidenceError, "not in the current accepted"):
            self.commit(
                "invalid",
                accepted("s1", "他抬起头。"),
                rule("no_evidence", "用人物动机引导对话",
                     category="dialogue", evidence_scope="s1",
                     evidence_excerpt="完全不存在的句子"),
            )
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM accepted_prose WHERE project_id='p1'"
        ).fetchone())
        self.assertIsNone(self.db.conn.execute(
            "SELECT 1 FROM writer_companion_profiles WHERE project_id='p1'"
        ).fetchone())
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM story_commit_receipts"
        ).fetchone()["n"], 0)

    def test_other_project_cannot_claim_evidence_from_this_project(self):
        self.commit("c1", accepted("s1", "她擦亮短刀。"))
        with self.assertRaises(CompanionEvidenceError):
            self.commit(
                "c2", rule("borrow", "保留身体现实",
                           evidence_scope="s1", evidence_excerpt="擦亮短刀"),
                project="another",
            )
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM writer_companion_preferences"
        ).fetchone()["n"], 0)

    def test_group_conflict_is_explicit_not_silent(self):
        self.commit("c1", rule("short", "在搏斗中使用短句",
                               category="pacing", conflict_group="sentence_rhythm"))
        with self.assertRaisesRegex(CompanionEvidenceError, "group conflict"):
            self.commit("c2", rule("long", "在搏斗中使用长句",
                                   category="pacing", conflict_group="sentence_rhythm"))
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM writer_companion_preferences"
        ).fetchone()["n"], 1)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM story_commit_receipts"
        ).fetchone()["n"], 1)
        # The same key is the only authoritative correction, not a second lane.
        self.commit("c3", rule("short", "长短随动作变化",
                               category="pacing", conflict_group="sentence_rhythm"))
        ctx = self.flow.begin_draft("s2", concerns=("pacing",))
        self.assertIn("长短随动作变化", ctx.companion_guidance)
        self.assertNotIn("搏斗中使用短句", ctx.companion_guidance)
        # Different category can use the same label for an unrelated concern.
        self.commit("c4", rule("dialogue_tempo", "对白节奏可慢",
                               category="dialogue", conflict_group="sentence_rhythm"))
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) AS n FROM writer_companion_preferences"
        ).fetchone()["n"], 2)

    def test_specific_rules_win_bounded_context_slots_not_new_priority_engines(self):
        for index in range(4):
            self.commit(f"g-{index}", rule(f"general-{index}", f"通用规则{index}"))
        self.commit("specific", rule("dialogue", "这场戏的对白须由人物目标推动",
                                      category="dialogue"))
        frame = self.flow.begin_draft("scene", concerns=("dialogue",))
        self.assertIn("由人物目标推动", frame.companion_guidance)
        self.assertEqual(len(frame.companion.guidance), 4)

    def test_axis_not_guessed_from_category_and_no_new_memory_table(self):
        self.commit("c1", rule("pacing", "让语速配合局势", category="pacing"))
        self.commit("c2", rule("plot", "人物的决定影响下个事件",
                               category="plot", axis="plot"))
        self.commit("c3", rule("creative", "允许出乎意料却可回溯的动作",
                               category="action", axis="creativity"))
        sheet = self.flow.review_writing_sheet()["axes"]
        self.assertEqual(sheet["language"], ())
        self.assertEqual(len(sheet["plot"]), 1)
        self.assertEqual(len(sheet["creativity"]), 1)

    def test_read_only_review_does_not_change_receipt_or_body(self):
        self.commit("c1", accepted("s1", "主人公迟疑片刻。"))
        self.commit("c2", rule("pause", "保留必要的停顿", axis="language"))
        n = self.db.conn.execute(
            "SELECT COUNT(*) n FROM story_commit_receipts"
        ).fetchone()["n"]
        version = self.db.conn.execute(
            "SELECT version FROM writer_companion_profiles WHERE project_id='p1'"
        ).fetchone()["version"]
        first = self.flow.review_writing_sheet()
        second = self.flow.review_writing_sheet()
        self.assertEqual(first, second)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) n FROM story_commit_receipts"
        ).fetchone()["n"], n)
        self.assertEqual(self.db.conn.execute(
            "SELECT version FROM writer_companion_profiles WHERE project_id='p1'"
        ).fetchone()["version"], version)

    def test_evidence_correction_with_recovered_worktree_and_replay(self):
        book = WorkNode("book", WorkKind.BOOK, memoized_state={"version": 1})
        scene = book.append_child(WorkNode("s1", WorkKind.SCENE,
                                           memoized_state={"body": ""}))
        root = StoryWorkRoot(book)
        root.schedule_update(scene, Lane.DRAFT,
                             pending_state={"body": "烛火摇动。"})
        StoryWorkLoop().render(root, render_lanes=Lane.DRAFT)
        effects = (
            accepted("s1", "烛火摇动。"),
            rule("flame", "物理变化应有前因", axis="creativity",
                 evidence_scope="s1", evidence_excerpt="烛火摇动"),
        )
        plan = StoryCommitPlan("p1", "both", effects, root.finished_fingerprint())
        result = self.coordinator.commit(plan, work_root=root)
        self.assertTrue(result.adopted_work_tree)
        replay = self.coordinator.commit(plan)
        self.assertTrue(replay.replayed)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) n FROM writer_companion_preferences"
        ).fetchone()["n"], 1)
        from writerforge import restore_work_root
        recovered = restore_work_root(self.db, "p1")
        self.assertEqual(find_node(recovered.current, "s1").memoized_state["body"],
                         "烛火摇动。")

    def test_invalid_anchor_or_axis_rejected_before_durable_writes(self):
        bad = (
            {"axis": "omniscient"},
            {"evidence_scope": "s1"},
            {"evidence_excerpt": "摘录"},
            {"conflict_group": "  "},
        )
        for i, metadata in enumerate(bad):
            with self.assertRaises(CompanionEvidenceError):
                self.commit(
                    f"bad-{i}", rule(f"test-{i}", "不能无证据地推断", **metadata),
                )
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) n FROM story_commit_receipts"
        ).fetchone()["n"], 0)

    def test_v21_database_is_migrated_without_loss(self):
        self.db.close()
        self.temp.cleanup()
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "old.db"
        original = sqlite3.connect(self.path)
        original.execute("""
            CREATE TABLE writer_companion_preferences (
              project_id TEXT NOT NULL,
              preference_key TEXT NOT NULL,
              guidance TEXT NOT NULL,
              direction TEXT NOT NULL,
              category TEXT NOT NULL,
              updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY(project_id, preference_key)
            )
        """)
        original.execute(
            """INSERT INTO writer_companion_preferences(
                    project_id,preference_key,guidance,direction,category)
               VALUES ('p1','legacy','原有作者偏好','prefer','general')"""
        )
        original.commit()
        original.close()
        migrated = WriterForgeDB(self.path)
        self.db = migrated
        self.flow = WritingFlow(migrated, write_runtime(), "p1")
        row = migrated.conn.execute(
            """SELECT guidance,axis,conflict_group,evidence_scope
               FROM writer_companion_preferences
               WHERE project_id='p1' AND preference_key='legacy'"""
        ).fetchone()
        self.assertEqual(row["guidance"], "原有作者偏好")
        self.assertIsNone(row["axis"])
        self.assertIsNone(row["evidence_scope"])
        self.assertIn("原有作者偏好",
                      self.flow.begin_draft("next").companion_guidance)
        migrated.close()
        self.db = WriterForgeDB(self.path)  # also exercises idempotent reopen

if __name__ == "__main__":
    unittest.main()
