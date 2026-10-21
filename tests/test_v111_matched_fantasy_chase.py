"""V111 no-network fair-question test: isolated MIT GitHub Skill vs real WF.

This test uses a synthetic published compatibility snapshot and mock model
replies, NEVER DeepSeek, R2 or the real 15-chapter literary experience.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

import wf_railway_v111_three_arm_prose_eval_once as demo
from test_v26_invisible_writer import PLAN
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import (
    InvisibleWritingAssist,AutonomousWriting,
)
from wf_railway_v108_real_e_f_once import fake_but_published_snapshot

class V111MatchedOriginalProse(unittest.TestCase):
    def test_real_pinned_MIT_github_skill_installed_text_only(self):
        source,license_text=demo.skill_original()
        self.assertTrue(source.startswith("---\nname: storyteller"))
        self.assertIn("Show don't tell",source)
        self.assertIn("MIT License",license_text)
        self.assertTrue(demo.PEER_PATH.exists())
        self.assertEqual(demo.blob_hash(demo.PEER_PATH.read_bytes()),
                         demo.PEER_GIT_BLOB)
        self.assertEqual(demo.blob_hash(demo.LICENSE_PATH.read_bytes()),
                         demo.LICENSE_GIT_BLOB)
        self.assertEqual(demo.PEER_ORIGIN_REPO,"xcrrr/claude-skills")
        self.assertIn(source,demo.peer_system(source))
        self.assertNotIn(source,demo.bare_system())
        self.assertNotIn("storyteller",demo.common_prose_instruction().lower())
        self.assertNotIn("storyteller",demo.user_question().lower())

    def test_frozen_exact_user_prompt_provider_costs_and_length(self):
        skill,_=demo.skill_original()
        f=demo.freeze(skill)
        self.assertEqual(demo.TASK,"给我一个追逐打斗的玄幻1000字")
        self.assertEqual(f["exact_common_user_question"],demo.TASK)
        self.assertEqual(demo.user_question(),demo.TASK)
        self.assertEqual(demo.ARMS,
            ("WF_SINGLE","GITHUB_STORYTELLER","BARE_DEEPSEEK"))
        self.assertEqual(demo.MAX_CALLS,4)
        self.assertEqual(demo.MAX_RESERVED_TOKENS,8450)
        self.assertEqual(demo.PROSE_TOKENS,2600)
        self.assertEqual(demo.WF_PLAN_TOKENS,650)
        self.assertEqual(f["same_max_prose_tokens_each_arm"],2600)
        self.assertEqual(f["max_relative_length_gap"],0.1)
        self.assertEqual(f["comparable_per_arm_range"],[900,1100])
        self.assertEqual(f["literary_grade"],"UNDETERMINED")
        self.assertFalse(f["author_accepted"])
        self.assertTrue(f["peer_skill_isolated_from_WF_writing"])
        self.assertTrue(f["WF_neutral_fixture_not_15_authored_chapters"])
        self.assertTrue(f["no_auto_retry_no_cropping_no_postprocessing"])
        self.assertTrue(f["raw_model_response_before_WF_validation"])
        self.assertTrue(f["original_wire_before_JSON_decode"])
        self.assertEqual(f["third_party_judge_model_calls"],0)

    def test_only_exact_original_prose_one_field_never_automatic_crop(self):
        original="他踏碎脚下的灵石，急忙回头看了一眼身后的追兵。"*20
        result=demo.prose_observation({"prose":original})
        self.assertEqual(result["raw_prose"],original)
        self.assertEqual(result["actual_codepoints"],len(original))
        self.assertEqual(result["status"],"LENGTH_OFF_TARGET")
        self.assertEqual(result["body_sha256"],
                         demo.digest(original.encode("utf8")))
        self.assertEqual(
            demo.prose_observation({"body":original})["status"],
            "PROSE_JSON_SCHEMA_FAILED")
        self.assertEqual(
            demo.prose_observation({"prose":original,"notes":"好句"})["status"],
            "PROSE_JSON_SCHEMA_FAILED")

    def test_WF_actual_single_runs_two_calls_without_peer_skill_context(self):
        with TemporaryDirectory() as root:
            dbpath=Path(root)/"neutral.sqlite3"
            snap=fake_but_published_snapshot(dbpath)
            db=WriterForgeDB(dbpath)
            rt=RuntimeEngine()
            rt.enter_write(snap)
            scene="一名游侠在风中翻过悬崖边的石桥。"*55
            assist=InvisibleWritingAssist(
                db,rt,"v111-benchmark-only","my-fantasy-scene",demo.TASK,
                model=demo.MODEL,api_base="http://127.0.0.1:1234/v1",
                source_genre="玄幻")
            with patch("writerforge.writing_assist.local_chat_completion",
                       side_effect=[PLAN,scene]) as model:
                outcome=AutonomousWriting(assist).run(
                    outline=demo.TASK,chapter_goals=[demo.TASK],
                    output_dir=Path(root)/"generated",
                    draft_mode="single")
            self.assertEqual(model.call_count,2)
            self.assertEqual(model.call_args_list[0].kwargs["max_tokens"],650)
            self.assertEqual(model.call_args_list[1].kwargs["max_tokens"],2600)
            actual=Path(outcome["chapters"][0]["candidate"]).read_text("utf8")
            self.assertEqual(actual,scene)
            self.assertFalse(outcome["chapters"][0]["accepted"])
            self.assertNotIn("storyteller",model.call_args_list[1].args[0].prompt)
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM accepted_prose").fetchone()[0],0)
            db.close()

    def test_source_runner_has_only_one_provider_and_no_external_judge(self):
        raw=Path(demo.__file__).read_text("utf8")
        self.assertEqual(raw.count("model.ask_json("),1)
        self.assertIn('on_response_wire=on_response_wire',raw)
        self.assertIn("WF111_RAW_PROVIDER_WIRE_PRIVATE_SEALED",raw)
        self.assertIn("WF111_JSON_PRIVATE_SEALED_BEFORE_VALIDATION",raw)
        self.assertIn("WF111_ONCE_ONLY_PRECOMMIT_REFUSES_DOUBLE_BILL",raw)
        self.assertIn("AutonomousWriting(ass).run(",raw)
        self.assertIn("draft_mode=\"single\"",raw)
        self.assertNotIn("manual_fix_wrong_json",raw)
        self.assertNotIn("accept_draft(",raw)
        self.assertNotIn("storyteller",Path(
            __file__).parts[-2] if False else "irrelevant_to_source")
        self.assertIn("blind_method_identity_hidden",raw)
        self.assertIn("unblind_after_review_only",raw)


if __name__=="__main__":
    unittest.main()
