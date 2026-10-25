"""0.AH frozen first paid batch protocol, entirely offline and zero models."""
from __future__ import annotations
import unittest
from hashlib import sha256

from experiments import wf_0ah_first_three_real_microfiction_20261025 as trial
from experiments.wf_0ad_multigenre_real_paired_writing_20261025 import (
    GENRES as PRIOR_REAL_GENRES, judge_prompt, JUDGEMENTS,
)


class ThreeGenreOriginalMicrofictionProtocol(unittest.TestCase):
    def test_three_new_preregistered_different_literary_functions(self):
        scenes = trial.SCENES
        self.assertEqual(len(scenes), 3)
        self.assertEqual([s["id"] for s in scenes], [
            "wuxia_bridge", "xianxia_herb", "history_dispatch"])
        self.assertEqual(len({s["genre"] for s in scenes}), 3)
        self.assertEqual(len({s["role"] for s in scenes}), 3)
        self.assertFalse({s["id"] for s in scenes} &
                         {s["id"] for s in PRIOR_REAL_GENRES})
        for x in scenes:
            self.assertTrue(x["topic"] and x["literary_task"])
            self.assertGreaterEqual(len(x["topic"]), 60)

    def test_identical_model_and_output_ceiling_both_writer_arms(self):
        plan = trial.protocol_receipt()
        self.assertEqual(plan["author_max_tokens_each_arm"], 1700)
        self.assertTrue(plan["equal_completion_ceiling_both_author_arms"])
        self.assertTrue(plan["same_system_both_arms"])
        self.assertTrue(plan["same_literary_scene_prompt_both_arms"])
        self.assertTrue(plan["same_output_budget_does_not_equalize_prompt_length"])
        self.assertTrue(plan["WF_extra_trace_JSON_uses_some_of_same_budget"])
        self.assertLessEqual(
            len(trial.SCENES) *
            (2 * trial.AUTHOR_MAX_TOKENS + 2 * trial.JUDGE_MAX_TOKENS),
            trial.MAX_RESERVED_OUTPUT)
        self.assertEqual(trial.MAX_CALLS, 12)
        self.assertEqual(plan["R2_reads"], plan["R2_writes"])
        self.assertEqual(plan["canon_writes"], 0)
        self.assertFalse(plan["main_modified"])
        for item in trial.SCENES:
            shared = trial.scene_prompt(item)
            self.assertTrue(trial.author_prompt(item, "bare").startswith(shared))
            self.assertTrue(trial.author_prompt(item, "WF").startswith(shared))
            self.assertIn("WF", trial.author_prompt(item, "WF"))
            self.assertNotIn("WF现有来源核验契约",
                             trial.author_prompt(item, "bare"))

    def test_rating_swaps_orders_but_never_exposes_arm_to_rater(self):
        self.assertEqual(JUDGEMENTS,
                         (("裸模型", "WF辅助"), ("WF辅助", "裸模型")))
        sample = {
            "bare": {"prose": "甲文" * 100},
            "WF": {"prose": "乙文" * 100},
        }
        first = judge_prompt(trial.SCENES[0], sample, JUDGEMENTS[0])
        reversed_order = judge_prompt(trial.SCENES[0], sample, JUDGEMENTS[1])
        self.assertTrue(first.index("甲文" * 10) < first.index("乙文" * 10))
        self.assertTrue(reversed_order.index("乙文" * 10) <
                        reversed_order.index("甲文" * 10))
        self.assertIn("不得", trial.SCENES[0]["topic"])

    def test_length_count_and_no_false_proof(self):
        self.assertEqual(trial.hanzi_count("风，停了。"), 3)
        self.assertEqual(trial.hanzi_count("A 2026!"), 0)
        plan = trial.protocol_receipt()
        self.assertEqual(plan["allowed_hanzi_count"], [200, 350])
        self.assertTrue(plan["literary_score_does_not_decide_source_acceptance"])
        self.assertTrue(plan["original_0AD_0AE_authors_never_called"])
        self.assertTrue(plan["no_paid_retry"])
        self.assertTrue(plan["same_model_family_judge_not_independent_human"])


if __name__ == "__main__":
    unittest.main()
