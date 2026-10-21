"""Offline V106 pilot boundary checks: no live model or R2 calls.

Authenticates exact isolated WF production entry point and durable request
budget; not a literary score nor a simulated provider success.
"""
from __future__ import annotations
import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
from unittest.mock import patch

import wf_railway_v106_real_e_f_smoke_once as x
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import InvisibleWritingAssist
from writerforge.deepseek_flash_model import ROLES


class RealEFContractTest(unittest.TestCase):
    def test_single_provider_frozen_output_and_task_count(self):
        f=x.freeze()
        self.assertEqual(x.MAX_CALLS,9)
        self.assertEqual(x.MAX_OUTPUT,11600)
        self.assertEqual(x.MAX_TOTAL,150000)
        self.assertEqual(x.MODEL,"deepseek-flash")
        self.assertEqual(x.FROZEN_ORDER,
                         ("emotion_rolling","foresight_rolling"))
        self.assertEqual(f["max_actual_provider_calls"],9)
        self.assertEqual(f["max_reserved_completion_tokens"],11600)
        self.assertTrue(f["same_self_selected_two_event_outline"])
        self.assertTrue(f["no_retry_even_if_incomplete"])
        self.assertEqual(f["external_literary_judge_model_calls"],0)
        self.assertEqual(f["new_training_chapters"],0)
        self.assertEqual(f["source_outline_sha256"],
                         sha256(x.SCENE.encode("utf8")).hexdigest())
        self.assertIn("self_scene_writing",ROLES)
        self.assertNotIn("battery:tool",x.HORIZON_PINS)
        self.assertIn("目前未知",x.COMMON_HARD_FACTS)

    def test_model_selects_beats_and_arms_receive_only_common_world(self):
        first=x.make_outline_request()
        self.assertIn(x.SCENE,first)
        self.assertIn(x.COMMON_HARD_FACTS,first)
        self.assertIn("两个叙事事件",first)
        self.assertNotIn("上一组模型小说",first)
        self.assertNotIn("以自己的成绩判断",first)
        self.assertNotIn("用户私有R2",first)
        self.assertEqual(len(x.CHAPTER_GOAL)<451,True)
        self.assertEqual(len(x.SCENE+"\n"+x.COMMON_HARD_FACTS)>15,True)

    def test_neutral_snapshot_is_not_real_novel_or_accepted_skills(self):
        with TemporaryDirectory() as tmp:
            file=Path(tmp)/"v106.sqlite"
            sid=x.fake_but_published_snapshot(file)
            db=WriterForgeDB(file)
            rt=RuntimeEngine();rt.enter_write(sid)
            assist=InvisibleWritingAssist(
               db,rt,"v106-experiment-only","test-scene",
               x.CHAPTER_GOAL,model=x.MODEL,
               api_base="http://127.0.0.1:1234/v1",
               source_genre="科幻")
            packet=assist.flow.prepare(
                "test-scene.chapter-001",x.CHAPTER_GOAL,
                concerns=("scene","decision"),genre="科幻")
            self.assertIn("科幻",packet.prompt)
            self.assertNotIn("葛梨",packet.prompt)
            self.assertTrue(packet.evidence)
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM accepted_prose").fetchone()[0],0)
            db.close()

    def test_external_cloud_scoring_and_silent_repeats_absent(self):
        source=Path(x.__file__).read_text("utf8")
        ast.parse(source)
        self.assertEqual(source.count("wf_model.ask_json("),1)
        self.assertIn("WF106_EXAM_ALREADY_RESERVED_NO_DOUBLE_BILLING",source)
        self.assertIn("WF106_ORIGINAL_REQUEST_SLOT_REUSED_REFUSE_REBILL",source)
        self.assertIn("all_actual_model_call_receipts",source)
        self.assertIn('original_decoded_json',source)
        self.assertIn("AutonomousWriting(assist).run(",source)
        self.assertIn("forward_author_pinned_facts",source)
        self.assertIn("not_formal_blind_review",source)
        self.assertIn("fake_but_published_snapshot",source)
        self.assertNotIn("accept_draft(",source)
        self.assertNotIn("report_postwrite(",source)
        self.assertNotIn("retry=",source)
        self.assertNotIn("other_model= ",source)


if __name__=="__main__":
    unittest.main()
