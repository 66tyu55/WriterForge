"""V114B fail-before-paying regression for exact official DeepSeek budget.

The original V114 one-shot is NOT replayed. This tests the specific failure
observed from the consumed experiment: FlashBudget has a STRICT 150000 value.
Every prompt/system role is checked for the required JSON dispatch string.
Zero HTTP, no secret access, no R2, zero original chapters moved.
"""
from __future__ import annotations
from hashlib import sha256
import unittest
from experiments import v114_real_wf_continuity_once as failed
from experiments import v114b_real_wf_continuity_once as fresh
from writerforge.deepseek_flash_model import FlashBudget,DeepSeekFlashError

class ExactFlashPreBudget(unittest.TestCase):
    def test_old_failed_precommit_kept_and_new_unique(self):
        self.assertNotEqual(failed.EXAM,fresh.EXAM)
        self.assertEqual(failed.MAX_TOTAL,135000)
        self.assertEqual(fresh.MAX_TOTAL,150000)
        self.assertEqual(fresh.MAX_CALLS,4)
        self.assertEqual(fresh.MAX_OUTPUT,5000)
        self.assertEqual(fresh.precommit()["max_conservative_budget"],150000)
        self.assertTrue(fresh.precommit()["V114B_is_new_precommit_not_replay"])
        self.assertTrue(fresh.precommit()[
            "previous_v114_precommit_consumed_but_no_provider_HTTP_response"])
        self.assertEqual(fresh.precommit()[
            "previous_v114_failure_manifest_cas_sha256"],
            "faa8f406a1960a34ef9d348d138456364e5fd56844526c899c5c8394e32f3941")
        self.assertNotEqual(sha256(fresh.packed(fresh.precommit())).hexdigest(),
                            sha256(failed.packed(failed.precommit())).hexdigest())
        self.assertEqual(fresh.TASK,"给我一个追逐打斗的玄幻1000字")
        self.assertEqual(fresh.MODEL,failed.MODEL)
        self.assertEqual(fresh.ROLE,failed.ROLE)
        self.assertTrue(fresh.precommit()["no_auto_retry_or_author_prose_rewrite"])

    def test_first_request_exact_prior_budget_error_reproduced_offline(self):
        old=FlashBudget(max_calls=4,max_reserved_output_tokens=5000,
                        max_total_tokens=135000)
        with self.assertRaisesRegex(DeepSeekFlashError,
                                    "WF_FLASH_TOTAL_BUDGET_CONFIGURATION_INVALID"):
            old.reserve("self_scene_writing",1450,1500)
        self.assertEqual(old.calls_reserved,0)
        self.assertEqual(old.tokens_reserved,0)

    def test_new_exact_budget_admits_entire_genuine_production_call_sequence(self):
        b=FlashBudget(max_calls=fresh.MAX_CALLS,
                      max_reserved_output_tokens=fresh.MAX_OUTPUT,
                      max_total_tokens=fresh.MAX_TOTAL)
        requested=[fresh.BEAT_TOKENS,fresh.PLAN_TOKENS,
                   fresh.TURN_TOKENS,fresh.TURN_TOKENS]
        self.assertEqual(requested,[1450,650,1450,1450])
        for quota in requested:
            b.reserve(fresh.ROLE,quota,2100)
        self.assertEqual(b.calls_reserved,4)
        self.assertEqual(b.tokens_reserved,5000)
        self.assertEqual(b.calls_with_uncertain_usage,4)
        with self.assertRaisesRegex(DeepSeekFlashError,
                                    "WF_FLASH_CALL_OR_TOKEN_BUDGET_EXCEEDED"):
            b.reserve(fresh.ROLE,650,2100)

    def test_preflight_all_api_system_instructions_include_JSON(self):
        for name in ("PLAN_SYSTEM","CHAPTER_SYSTEM","TURN_SYSTEM"):
            value=getattr(fresh,name)
            self.assertIsInstance(value,str)
            self.assertTrue("JSON" in value or "json" in value,name)
            self.assertGreaterEqual(len(value),10)
        self.assertIn("needs",fresh.CHAPTER_SYSTEM)
        self.assertIn("parent_effect_quote",fresh.TURN_SYSTEM)
        self.assertIn("novel-studio",fresh.precommit()["external_memory_core"])
        self.assertFalse(fresh.precommit()["no_external_rating_model"] is False)
        self.assertEqual(fresh.precommit()["acceptance_and_skill_graduation"],"LOCKED")

    def test_original_WF_path_without_external_critic_or_retry(self):
        import pathlib
        s=pathlib.Path(fresh.__file__).read_text("utf8")
        self.assertIn('draft_mode="continuity_guard"',s)
        self.assertIn('AutonomousWriting(helper).run(',s)
        self.assertIn("WF114_WIRE_CAS_BEFORE_DECODE",s)
        self.assertIn("WF114_DECODED_ORIGINAL_BEFORE_ANY_WF_GUARD",s)
        self.assertEqual(s.count("model.ask_json("),1)
        self.assertNotIn("accept_draft(",s)
        self.assertNotIn("autoretry=",s)

if __name__=="__main__":
    unittest.main()
