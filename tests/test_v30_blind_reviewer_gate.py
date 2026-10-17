"""Synthetic-only double-blind critique attacks; never model/live calls."""
import unittest
from copy import deepcopy
from writerforge.v30_blind_reviewer_gate import (
    verify_double_blind_model_reviews,BlindReviewerGateError,DIMS,
)

def review(model,rev=False,better=True):
    old={d:80 for d in DIMS}
    new={d:(88 if better else 72) for d in DIMS}
    return {
        "reviewer_model":model,
        "host_label_mapping":({"A":"semantic","B":"legacy"} if rev else
                              {"A":"legacy","B":"semantic"}),
        "anonymous_task_only":True,
        "source_prose_exposed":False,
        "ratings":({"A":new,"B":old} if rev else {"A":old,"B":new}),
    }
def call(rows):
    return verify_double_blind_model_reviews(
        planner_model="deepseek-v4-flash-0731",
        writer_model="glm-5.3",critiques=rows)

class V30BlindMultiModelGateTests(unittest.TestCase):
    def test_two_distinct_models_swapped_but_never_skill_pass(self):
        result=call([review("intern-s2"),review("minimax-m3",rev=True)])
        self.assertTrue(result["unanimous_all_dimensions_model_preference"])
        self.assertEqual(result["reviewer_count"],2)
        self.assertFalse(result["literary_skill_advanced"])
        self.assertFalse(result["human_review_performed"])
    def test_second_reviewer_negative_cannot_be_average_cancelled(self):
        result=call([review("intern-s2"),review("minimax-m3",rev=True,better=False)])
        self.assertFalse(result["unanimous_all_dimensions_model_preference"])
        self.assertTrue(result["any_model_disagrees_or_sees_regression"])
        self.assertEqual(len(result["reviewers"][1]["negative_dimensions"]),5)
        self.assertEqual(result["status"],"MODEL_DISAGREEMENT_OR_REGRESSION_NOT_PASSED")
    def test_planner_as_critic_refused(self):
        with self.assertRaisesRegex(BlindReviewerGateError,"SELF_OR_DUPLICATE"):
            call([review("deepseek-v4-flash-0731"),review("minimax-m3",rev=True)])
    def test_same_critic_twice_refused(self):
        with self.assertRaisesRegex(BlindReviewerGateError,"SELF_OR_DUPLICATE"):
            call([review("minimax-m3"),review("minimax-m3",rev=True)])
    def test_not_reversed_arms_or_source_exposure_refused(self):
        rows=[review("intern-s2"),review("minimax-m3",rev=False)]
        with self.assertRaisesRegex(BlindReviewerGateError,"BLIND_LABEL_SWAP"):
            call(rows)
        rows[1]["host_label_mapping"]={"A":"semantic","B":"legacy"}
        rows[1]["source_prose_exposed"]=True
        with self.assertRaisesRegex(BlindReviewerGateError,"BLIND_LABEL_SWAP"):
            call(rows)
    def test_missing_dimension_and_boolean_rating_fail(self):
        rows=[review("intern-s2"),review("minimax-m3",rev=True)]
        rows[1]["ratings"]["A"].pop("information")
        with self.assertRaisesRegex(BlindReviewerGateError,"DIMENSIONS_INCOMPLETE"):
            call(rows)
        rows=[review("intern-s2"),review("minimax-m3",rev=True)]
        rows[1]["ratings"]["A"]["language"]=True
        with self.assertRaisesRegex(BlindReviewerGateError,"DIMENSIONS_INCOMPLETE"):
            call(rows)

if __name__=="__main__":
    unittest.main()
