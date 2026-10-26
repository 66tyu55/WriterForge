"""0.AM no-paid preflight of REAL G one-shot, frozen writer source and budget.

Tests local source evidence without learning or R2, and guards against
turning provider/schema failures into a fabricated complete chapter.
"""
from __future__ import annotations
import inspect
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import InvisibleWritingAssist
from experiments import wf_0am_real_history_same_model_g_once_20261026 as trial
from test_wf_0ai_decision_effect_pending import HISTORY_REAL,HISTORY_REAL_SHA


class FrozenHistoryOneShotPreflight(unittest.TestCase):
    def test_exact_original_source_sha_and_no_repeat_0af_scenes(self):
        self.assertEqual(trial.h(HISTORY_REAL),HISTORY_REAL_SHA)
        self.assertEqual(trial.EXPECTED_SOURCE_SHA,HISTORY_REAL_SHA)
        self.assertEqual(trial.ORIGINAL_SOURCE_RUN,40201458798)
        self.assertEqual(trial.ORIGINAL_RECOVERY_RUN,40202483990)
        self.assertIn("明日卯时",HISTORY_REAL)
        self.assertEqual(len(trial.GOALS),1)
        self.assertEqual(trial.MAX_MODEL_CALLS,12)
        self.assertEqual(trial.MAX_COMPLETION_RESERVATION,26000)
        self.assertTrue(trial.OUTPUT.name.startswith("wf_0am_"))

    def test_ephemeral_writer_owned_evidence_not_book_training(self):
        with TemporaryDirectory() as folder:
            db=WriterForgeDB(Path(folder)/"source.db")
            try:
                snapshot=trial.local_source_only_snapshot(db,HISTORY_REAL)
                rt=RuntimeEngine()
                rt.enter_write(snapshot)
                writer=InvisibleWritingAssist(
                    db,rt,trial.PROJECT,trial.SCENE,
                    "继续真实既有原作家的历史传令片段",
                    model="deepseek-flash",api_base="https://api.deepseek.com/v1",
                    source_genre="古代白话")
                packet=writer.flow.prepare(
                    trial.SCENE,trial.GOALS[0],
                    concerns=("scene","decision"),genre="古代白话")
                self.assertEqual(packet.snapshot_id,snapshot)
                self.assertEqual(len(packet.evidence),1)
                self.assertIn(HISTORY_REAL[:45],packet.prompt)
                works=db.conn.execute(
                    "SELECT work_id,source_sha256 FROM studied_works").fetchall()
                self.assertEqual(len(works),1)
                self.assertEqual(works[0]["source_sha256"],HISTORY_REAL_SHA)
                self.assertIsNone(db.conn.execute(
                    "SELECT 1 FROM accepted_prose").fetchone())
            finally:
                db.close()

    def test_full_real_G_with_one_model_and_no_silent_retries(self):
        program=inspect.getsource(trial.main)
        caller=inspect.getsource(trial.OneRealAuthor)
        self.assertIn('source_file.read_text("utf8")',inspect.getsource(
            trial.verify_old_real_source))
        self.assertIn("verify_old_real_source()",program)
        self.assertLess(program.index("verify_old_real_source()"),
                        program.index("writer=OneRealAuthor(secret)"))
        self.assertIn('draft_mode="continuity_guard"',program)
        self.assertIn('self_edit_timing="ai_decides"',program)
        self.assertIn("resume_story_checkpoint=root",program)
        self.assertIn("external_temporal_step(old",program)
        self.assertIn("new_graph(project_id=PROJECT",program)
        self.assertIn("read_core_from_resume",program)
        self.assertIn('if status["status"]!=',program)
        self.assertIn("original_wire_saved_before_parsing",caller)
        self.assertIn("on_response_wire=self.preserve_before_parse",caller)
        self.assertIn("WF0AM_NO_WIRE_OVERWRITE_OR_RETRY",caller)
        self.assertNotIn("time.sleep",caller+program)
        self.assertNotIn("retry(",caller.lower()+program.lower())
        self.assertIn("canon_writes",program)
        self.assertIn("R2_writes",program)


if __name__=="__main__":
    unittest.main()
