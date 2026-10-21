"""V114 real GitHub smoke preflight, zero paid model and zero R2 calls."""
import unittest
from pathlib import Path
from writerforge import WriterForgeDB,RuntimeEngine
from writerforge.writing_assist import InvisibleWritingAssist
from writerforge.v96_causal_turns import parse_turn_outline
from experiments.v111_peer.neutral_bridge import fresh_neutral_published_snapshot
from experiments import v114_real_wf_continuity_once as x

class V114LivePreflight(unittest.TestCase):
    def test_one_shot_r2_and_two_turn_budget(self):
        a=x.precommit()
        self.assertEqual(a["exam"],"WF-V114-REAL-CONTINUITY-AND-NOVEL-STUDIO-20261021")
        self.assertEqual(a["user_exact_task"],"给我一个追逐打斗的玄幻1000字")
        self.assertEqual(a["model"],"deepseek-flash")
        self.assertEqual(a["max_model_requests"],4)
        self.assertEqual(a["max_reserved_model_output"],5000)
        self.assertTrue(a["no_auto_retry_or_author_prose_rewrite"])
        self.assertTrue(a["original_wire_R2_before_JSON_parse"])
        self.assertTrue(a["original_decoded_R2_before_WF_validation"])
        self.assertFalse(a["no_external_rating_model_calls"]
                         if "no_external_rating_model_calls" in a else False)
        self.assertEqual(a["acceptance_and_skill_graduation"],"LOCKED")
        self.assertEqual(a["external_memory_pinned_upstream_commit"],
                         "b585a9ca4ce474fe2471bf3bb7f8c284c6e4104a")
        self.assertTrue(a["old_V113_original_951_char_body_never_sent_to_model"])
        self.assertTrue(a["synthetic_neutral_snapshot_used"])

    def test_own_beat_instruction_does_not_supply_a_plot_answer(self):
        self.assertIn("两个事件",x.PLAN_SYSTEM)
        self.assertIn("kind=action或decision",x.PLAN_PROMPT)
        self.assertIn("causal_parent=null",x.PLAN_PROMPT)
        self.assertNotIn("沈渡",x.PLAN_PROMPT+x.TURN_SYSTEM)
        self.assertNotIn("旧剑穗",x.PLAN_PROMPT+x.TURN_SYSTEM)
        self.assertIn("parent_effect_quote必须为JSON null",x.TURN_SYSTEM)
        self.assertIn("450-550",x.TURN_SYSTEM)
        self.assertEqual(x.MAX_CALLS,4)

    def test_new_WF_continuity_not_fake_external_skill_judge(self):
        src=Path(x.__file__).read_text("utf8")
        self.assertIn('AutonomousWriting(helper).run(',src)
        self.assertIn('draft_mode="continuity_guard"',src)
        self.assertIn('on_response_wire=wire',src)
        self.assertIn('WF114_REQUEST_INTENT_R2_LOCKED',src)
        self.assertIn('WF114_WIRE_CAS_BEFORE_DECODE',src)
        self.assertIn('WF114_DECODED_ORIGINAL_BEFORE_ANY_WF_GUARD',src)
        self.assertEqual(src.count("model.ask_json("),1)
        self.assertNotIn("accept_draft(",src)
        self.assertNotIn("autoretry=",src)
        self.assertIn('"model_judge_calls":0',src)

if __name__=="__main__":
    unittest.main()
