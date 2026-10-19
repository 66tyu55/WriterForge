"""V81 independent blind-case freeze and no-grading-by-model unit tests."""
from __future__ import annotations
from hashlib import sha256
import unittest
from writerforge.v81_frozen_blind_ablation import (
 CASES,frozen_sha,prompt_for_case,grade_case,decision_summary,
)

class BlindTransferTest(unittest.TestCase):
    def test_pre_registered_cases_are_outside_private_training(self):
        self.assertEqual(len(CASES),3)
        self.assertEqual([x["id"] for x in CASES],["A","B","C"])
        self.assertEqual(len({c["focus"] for c in CASES}),3)
        self.assertEqual(len(frozen_sha()),64)
    def test_identical_input_except_explicit_prior_strategy(self):
        case=CASES[0]
        a=prompt_for_case(case,experience_strategy=None)
        b=prompt_for_case(case,experience_strategy="观察人物知道的信息和环境变化")
        self.assertEqual(a[0],b[0])
        self.assertIn(case["scene"],a[1])
        self.assertIn(case["scene"],b[1])
        self.assertNotIn(case["focus"],a[1])
        self.assertNotIn("观察人物知道的信息",a[1])
        self.assertIn("观察人物知道的信息",b[1])
    def test_exact_quote_and_mechanism_without_ai_self_score(self):
        case=CASES[0]
        passed=grade_case(case,{
           "mechanism":case["focus"],"evidence":case["scene"][:12],
           "reader_question":"钟声从哪里来？",
           "uncertainty":"这不足以认定是谁敲钟",
        })
        self.assertEqual(passed["score"],3)
        self.assertFalse(passed["literary_quality_or_training_transfer_proven"])
        broken=grade_case(case,{
           "mechanism":case["focus"],"evidence":"这句话不存在在当前原文里",
           "reader_question":"能否继续观察？",
           "uncertainty":"无法判断",
        })
        self.assertFalse(broken["source_exact"])
        self.assertLess(broken["score"],3)
    def test_summary_does_not_claim_skill_promotion_even_if_all_right(self):
        data=[]
        for case in CASES:
            for arm in ("without_experience","with_experience"):
                out={"case_id":case["id"],"arm":arm,
                     "output_sha256":sha256((arm+case["id"]).encode()).hexdigest(),
                     "grade":{"score":3 if arm=="with_experience" else 2}}
                data.append(out)
        summary=decision_summary(data)
        self.assertEqual(summary["measured_ablation_delta"],3)
        self.assertEqual(summary["different_outputs_in_paired_cases"],3)
        self.assertFalse(summary["claims_literary_mastery"])
        self.assertFalse(summary["human_literary_judge_involved"])
if __name__=="__main__":
    unittest.main()
