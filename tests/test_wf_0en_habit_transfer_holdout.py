"""Offline source-lock, independent holdout and paid-cost gates for 0.EN."""
from __future__ import annotations
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from experiments import wf_0en_habit_transfer_holdout as en
from writerforge.reverse_discovery_models import (
    DiscoveryCallBudget,DiscoveryError
)

class WF0ENHoldout(unittest.TestCase):
    def get_prior(self):
        source=os.getenv("WF0EN_SOURCE_DIR")
        if not source:
            self.skipTest("real GitHub Actions source-artifact path not supplied")
        return Path(source)

    def test_prior_genuine_paid_coach_is_reusable_at_zero_teacher_cost(self):
        plan=en.preflight(self.get_prior())
        self.assertEqual(plan["source_run_id"] if "source_run_id" in plan
                         else plan["old_run"],42007328800)
        self.assertEqual(plan["old_coach_sha256"],en.PRIOR_COACH_SHA)
        self.assertEqual(plan["teacher_calls"],0)
        self.assertFalse(plan["author_accepted"])
        self.assertEqual(len(plan["scenes"]),2)

    def test_original_prose_and_coach_tampering_fail_closed(self):
        prior=self.get_prior()
        with TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ("validated-prior-coach.json","replay-manifest.json",
                         "ford-tax-A.md","ford-tax-B.md"):
                (root/name).write_bytes((prior/name).read_bytes())
            self.assertEqual(en.verify_old_coach(root)["use"],"USE")
            (root/"validated-prior-coach.json").write_text("{}","utf8")
            with self.assertRaisesRegex(en.HoldoutError,
                                        "PAID_COACH_OR_MANIFEST"):
                en.verify_old_coach(root)

    def test_prompts_same_content_except_optional_habits(self):
        self.assertEqual(len({x["id"] for x in en.SCENES}),2)
        for scene in en.SCENES:
            sa,a=en.scene_prompt(scene,"A")
            sb,b=en.scene_prompt(scene,"B")
            self.assertEqual(sa,sb)
            self.assertTrue(b.startswith(a))
            self.assertNotIn("暂定习惯",a)
            self.assertIn("仅在合适时可采用",b)
            self.assertNotIn("谢凝",b)
            self.assertNotIn("船工阿福",b)
            self.assertNotIn("谁先承担后果？",a)
            self.assertLessEqual(len(b),2800)

    def test_writer_budget_cap_no_uncontrolled_retries(self):
        budget=DiscoveryCallBudget(max_calls=en.MAX_CALLS,
              max_reserved_output_tokens=en.MAX_RESERVED)
        for _ in range(en.MAX_CALLS):
            budget.reserve(1200,en.WRITER_TOKENS,role="writer")
        self.assertEqual(budget.calls,6)
        with self.assertRaisesRegex(DiscoveryError,
                                   "MODEL_CALL_OR_TOKEN_BUDGET_EXHAUSTED"):
            budget.reserve(1200,en.WRITER_TOKENS,role="writer")
        self.assertEqual(budget.calls,6)

    def test_no_network_without_explicit_approval(self):
        with patch.dict(os.environ,{"DISCOVERY_API_KEY":"synthetic-test-key",
                                   "WF0EN_PAID_APPROVAL":""}):
            with self.assertRaisesRegex(en.HoldoutError,
                                        "EXPLICIT_PAID_GATE_CLOSED"):
                en.live(Path("/no-prior"),Path("/must-not-create"))
        with patch.dict(os.environ,{"DISCOVERY_API_KEY":"",
                                   "WF0EN_PAID_APPROVAL":en.APPROVAL}):
            with self.assertRaisesRegex(en.HoldoutError,
                                        "DISCOVERY_KEY_MISSING"):
                en.live(Path("/no-prior"),Path("/must-not-create"))

    def test_han_count_not_punctuation_and_length_comparison(self):
        self.assertEqual(en.han_count("三人决定，不等。"),6)
        self.assertEqual(en.relative_difference(1000,1200),.1667)
        self.assertGreater(en.relative_difference(1000,1800),en.MAX_RATIO)
        self.assertEqual(en.relative_difference(0,0),1.0)
        self.assertEqual(en.MAX_RATIO,.20)
        self.assertEqual((en.MIN_LENGTH,en.MAX_LENGTH),(900,1400))

    def test_offline_plan_contains_no_promoted_rules(self):
        plan=en.preflight(self.get_prior())
        self.assertEqual(plan["phase"],"OFFLINE_VALIDATED_ONLY")
        self.assertEqual(plan["canon_writes"],0)
        self.assertEqual(plan["r2_writes"],0)
        self.assertFalse(plan["quality_improvement_proven"])
        self.assertFalse(plan["base_weights_modified"])
        self.assertEqual(plan["writer_model"],"deepseek-v4-pro-0813")
        self.assertEqual(plan["max_wire_calls_including_retry"],6)
        self.assertEqual(plan["max_reserved_output_tokens_not_usage"],15600)
        self.assertEqual(len(plan["original_model_questions"]),2)
        self.assertEqual(len(plan["explicit_human_transfer_questions"]),2)

if __name__=="__main__":
    unittest.main()
