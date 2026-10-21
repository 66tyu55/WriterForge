"""V108 preregistration and real WF route offline checks. No model/network."""
import unittest
from pathlib import Path
from unittest.mock import patch
from hashlib import sha256
from copy import deepcopy
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.v107_outline_observation import observe_shared_two_turns
from writerforge.deepseek_flash_model import ROLES
import wf_railway_v106_real_e_f_smoke_once as consumed
import wf_railway_v108_real_e_f_once as fresh

class V108ColdPreflight(unittest.TestCase):
    def test_new_unique_frozen_identity_and_same_common_world(self):
        self.assertNotEqual(consumed.EXAM,fresh.EXAM)
        self.assertEqual(consumed.SCENE,fresh.SCENE)
        self.assertEqual(consumed.COMMON_HARD_FACTS,fresh.COMMON_HARD_FACTS)
        self.assertEqual(consumed.HORIZON_PINS,fresh.HORIZON_PINS)
        self.assertNotEqual(consumed.make_outline_request(),
                            fresh.make_outline_request())
        self.assertEqual(fresh.FROZEN_ORDER,
                         ("emotion_rolling","foresight_rolling"))
        self.assertEqual(fresh.MODEL,"deepseek-flash")
        self.assertEqual(fresh.MAX_CALLS,9)
        self.assertEqual(fresh.MAX_OUTPUT,11600)
        self.assertTrue(fresh.freeze()["new_experiment_not_replay_of_v106"])
        self.assertTrue(fresh.freeze()["v106_failed_response_unmodified_and_unrecovered"])
        self.assertTrue(fresh.freeze()["not_formal_blind_review"])
        self.assertEqual(fresh.freeze()["new_training_chapters"],0)

    def test_formatted_outline_syntax_is_exact_v96_not_manual_story_answer(self):
        prompt=fresh.make_outline_request()
        self.assertIn("craft_focus必须是JSON数组",prompt)
        self.assertIn('"causal_parent":null',prompt)
        self.assertIn('"causal_parent":"t01"',prompt)
        self.assertIn('恰好两个事件对象',prompt)
        self.assertIn('请自行替换',prompt)
        self.assertNotIn("旧模型答复",prompt)
        good={"turns":[
            {"id":"t01","kind":"action","actor":"角色一",
             "goal":"实际到现场先查清气流与能源状态",
             "causal_parent":None,"craft_focus":["action"]},
            {"id":"t02","kind":"decision","actor":"角色二",
             "goal":"在已确认实际后果之后选择下一步路线",
             "causal_parent":"t01","craft_focus":["dialogue"]},
        ]}
        before=deepcopy(good)
        self.assertTrue(observe_shared_two_turns(good)["exact_v96_valid"])
        self.assertEqual(len(parse_turn_outline(
            __import__("json").dumps(good,ensure_ascii=False))),2)
        self.assertEqual(before,good)

    def test_raw_cas_announced_before_v96_parser_in_new_runner(self):
        text=Path(fresh.__file__).read_text("utf8")
        self.assertLess(text.index('"WF107_SINGLE_REQUEST_INTENT_R2_SEALED"'),
                        text.index("wf_model.ask_json("))
        self.assertLess(
            text.index('"WF107_RAW_MODEL_REPLY_R2_SEALED_BEFORE_VALIDATION"'),
            text.index("outline=parse_turn_outline("))
        self.assertIn('"WF107_STRICT_SHARED_OUTLINE_REJECTED_WITH_EVIDENCE"',text)
        self.assertIn("no_auto_retry",text)
        self.assertEqual(text.count("wf_model.ask_json("),1)
        self.assertNotIn("accept_draft(",text)
        self.assertNotIn("report_postwrite(",text)
        self.assertNotIn("retry_on_json",text)
        self.assertIn("AutonomousWriting(assist).run(",text)
        self.assertIn("fake_but_published_snapshot",text)
        self.assertIn("same_WF_two_turns_sha256",text)

    def test_preflight_fixture_no_real_learned_books_are_used(self):
        from tempfile import TemporaryDirectory
        from writerforge import WriterForgeDB,RuntimeEngine
        from writerforge.writing_assist import InvisibleWritingAssist
        with TemporaryDirectory() as d:
            name=Path(d)/"fake.db"
            snapshot=fresh.fake_but_published_snapshot(name)
            db=WriterForgeDB(name)
            rt=RuntimeEngine()
            rt.enter_write(snapshot)
            obj=InvisibleWritingAssist(
                db,rt,"v108-experiment-only","v108-dryrun",
                fresh.CHAPTER_GOAL,
                model=fresh.MODEL,api_base="http://127.0.0.1:1234/v1",
                source_genre="科幻")
            packet=obj.flow.prepare(
                "v108-dryrun.chapter-001",fresh.CHAPTER_GOAL,
                concerns=("scene","decision"),genre="科幻")
            self.assertIn("科幻",packet.prompt)
            self.assertEqual(len(packet.evidence)>0,True)
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM accepted_prose").fetchone()[0],0)
            db.close()

    def test_new_run_does_not_alias_original_cas_precommit(self):
        self.assertNotEqual(
            sha256(fresh.encode(fresh.freeze())).hexdigest(),
            sha256(consumed.encode(consumed.freeze())).hexdigest())
        self.assertIn("self_scene_writing",ROLES)


if __name__=="__main__":
    unittest.main()
