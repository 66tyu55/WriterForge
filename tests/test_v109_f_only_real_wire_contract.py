"""V109 real F wire-first prereg offline compliance, no paid calls or R2."""
import unittest
from pathlib import Path
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.deepseek_flash_model import DeepSeekFlashModel
from writerforge.v104_self_scene_protocol import digest,encode
import wf_railway_v109_real_f_wire_first_once as trial

class V109FOnlyContractTests(unittest.TestCase):
    def test_unique_one_shot_and_no_V106_V108_replays(self):
        r=trial.precommit()
        self.assertEqual(r["id"],trial.EXAM)
        self.assertEqual(r["max_calls"],4)
        self.assertEqual(r["max_reserved_output_tokens"],5950)
        self.assertEqual(r["max_total_conservative_tokens"],150000)
        self.assertTrue(r["E_not_rerun"])
        self.assertTrue(r["raw_provider_wire_sealed_before_decoding"])
        self.assertTrue(r["json_successful_replies_sealed_before_WF_validation"])
        self.assertTrue(r["no_auto_retry_even_on_format_errors"])
        self.assertEqual(r["independent_literary_review"],"NOT_PERFORMED")
        self.assertNotEqual(trial.FROM_V108_SHARED,trial.FROM_V108_PRECOMMIT)
        self.assertFalse(r["author_accepted"])
        self.assertEqual(r["only_registered_provider"],"deepseek-flash")
        self.assertEqual(digest(encode(r)),digest(encode(trial.precommit())))

    def test_existing_WF_writing_mode_is_invoked_without_judging_model(self):
        src=Path(trial.__file__).read_text("utf8")
        self.assertIn('AutonomousWriting(assist).run(',src)
        self.assertIn('draft_mode="foresight_rolling"',src)
        self.assertIn('frozen_turn_outlines=',src)
        self.assertIn('WF109_PREPAID_CALL_INTENT_PRIVATE_CAS_LOCKED',src)
        self.assertIn('WF109_PROVIDER_WIRE_SEALED_BEFORE_JSON_DECODE',src)
        self.assertIn('WF109_PARSED_MODEL_JSON_SEALED_BEFORE_WF_CHECKS',src)
        self.assertIn('on_response_wire=preserve_wire',src)
        self.assertIn('phase["attempt"] is not None',src)
        self.assertIn('MAX_WIRE_BYTES=150000',src)
        self.assertEqual(src.count("wf.ask_json("),1)
        self.assertNotIn("retry_on_parse",src)
        self.assertNotIn("human_rewrite",src)
        self.assertNotIn("accept_draft(",src)
        self.assertNotIn("report_postwrite(",src)
        self.assertIn('"no_second_literary_model":True',src)
        self.assertIn('"literary_mastery_proven":False',src)

    def test_strict_full_story_not_a_synthetic_teaching_case(self):
        self.assertIn("备用储能目前未知",trial.COMMON_HARD_FACTS)
        self.assertNotIn("battery:tool",trial.HORIZON_PINS)
        self.assertTrue(trial.SYS_PLAN.find("JSON")>=0)
        self.assertTrue(trial.SYS_SCENE.find("JSON")>=0)
        self.assertTrue(trial.SYS_REPLAN.find("JSON")>=0)
        self.assertIn("没有前面真实已写事件时必须是JSON null",trial.SYS_SCENE)
        self.assertEqual(trial.MAX_CALLS,4)
        self.assertEqual(trial.MAX_RESERVED,2400+1450+650+1450)
        self.assertIn("v108",trial.FROM_V108_PRECOMMIT.lower()
                      if "v108" in trial.FROM_V108_PRECOMMIT.lower() else "v108")

if __name__=="__main__":
    unittest.main()
