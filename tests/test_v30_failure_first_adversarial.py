"""Adversarial V30 failure-first tests, entirely synthetic report data.

Synthetic 85/92.8 etc are fixture values, NOT real receipts. A real workflow
will separately fresh-GET the actual immutable R2 SHA.
"""
import unittest
from hashlib import sha256
from test_v29_recovered_holdout_audit import RecoveryAuditTests
from scripts.audit_v29_recovered_holdout import audit
from writerforge.v29_semantic_regression_candidates import canonical
from writerforge.v30_failure_first import failure_first_review,FailureFirstError

class V30AdversarialFailureTests(unittest.TestCase):
    def known_fixture(self):
        r=audit(RecoveryAuditTests().create(),persist=False)
        records=r["results"]
        table=[
            ([7,7,8,8,9],85.0,92.8,
             ["GOAL_FILTERS_ATTENTION","COST_VISIBLE_IN_ACTION"],
             ["GOAL_FILTERS_ATTENTION","WITHHOLD_CAUSE_SHOW_CLUE"],1238,1318),
            ([-4,-8,-5,-4,-4],87.2,82.2,
             ["GOAL_FILTERS_ATTENTION","WITHHOLD_CAUSE_SHOW_CLUE"],
             ["GOAL_FILTERS_ATTENTION","COST_VISIBLE_IN_ACTION"],995,1134),
            ([4,8,6,7,6],82.8,89.0,
             ["GOAL_FILTERS_ATTENTION","WITHHOLD_CAUSE_SHOW_CLUE"],
             ["GOAL_FILTERS_ATTENTION","WITHHOLD_CAUSE_SHOW_CLUE"],1394,1401),
        ]
        names=("perception","causality","information","continuity","language")
        for x,(dims,old_score,new_score,old,new,oldlen,newlen) in zip(records,table):
            x["old_score"]=old_score
            x["new_score"]=new_score
            x["delta"]=round(new_score-old_score,1)
            x["per_dimension_new_minus_old"]=dict(zip(names,dims))
            x["mechanisms_old"]=old
            x["mechanisms_new"]=new
            x["mechanisms_same"]=set(old)==set(new)
            x["draft_chars_old"]=oldlen
            x["draft_chars_new"]=newlen
            x["all_five_negative"]=all(d<0 for d in dims)
        return r
    def check(self,report):
        return failure_first_review(report,receipt_sha256=sha256(canonical(report)).hexdigest())

    def test_positive_mean_does_not_cancel_a_real_five_dimension_decline(self):
        report=self.known_fixture()
        self.assertEqual(sum(r["delta"] for r in report["results"])/3,3)
        result=self.check(report)
        self.assertFalse(result["stable_literary_progress_proven"])
        self.assertFalse(result["literary_promotion_allowed"])
        self.assertEqual(result["validation_status"],
                         "MODEL_RATED_REGRESSION_PRESENT_NO_PROMOTION")
        self.assertEqual(result["critical_all_five_regressions"],1)
        self.assertEqual(result["number_of_negative_dimensions"],5)
        self.assertEqual(result["cases"][1]["negative_dimensions_do_not_cancel"],
                         {"perception":4,"causality":8,"information":5,
                          "continuity":4,"language":4})
        self.assertEqual(result["technique_changed_and_model_positive_cases"],1)
        self.assertEqual(result["technique_changed_and_model_negative_cases"],1)
        self.assertEqual(result["positive_cases_with_same_techniques_no_selector_credit"],1)
        self.assertEqual(result["cases"][2]["case_verdict"],
                         "POSITIVE_SCORE_SAME_OPERATIONS_NO_SELECTOR_CREDIT")
        self.assertTrue(result["critic_and_planner_same_flash_model_family"])
        self.assertEqual(result["cases_with_absolute_length_noncompliance"],2)
        self.assertEqual(result["first_window"],"NOT_PASSED")
        self.assertEqual(result["second_window"],"LOCKED")
        self.assertNotIn("mean_new_minus_old_scored_only",result)

    def test_tampered_digest_rejected_before_evaluation(self):
        report=self.known_fixture()
        with self.assertRaisesRegex(FailureFirstError,"UNTRUSTED"):
            failure_first_review(report,receipt_sha256="1"*64)

    def test_fake_mean_and_five_dimensions_mismatch_refused(self):
        report=self.known_fixture()
        report["results"][1]["delta"]=20
        with self.assertRaisesRegex(FailureFirstError,"UNTRUSTED"):
            self.check(report)

    def test_fake_same_mechanism_flag_refused_even_when_sha_matches(self):
        report=self.known_fixture()
        report["results"][2]["mechanisms_same"]=False
        with self.assertRaisesRegex(FailureFirstError,"FALSE_TECHNIQUE_CHANGE"):
            self.check(report)

    def test_symmetric_independent_length_rule_not_relaxed(self):
        report=self.known_fixture()
        report["results"][0]["draft_chars_new"]=4500
        with self.assertRaisesRegex(FailureFirstError,"MODEL_LENGTH_COMPARISON_NOT_FAIR"):
            self.check(report)

    def test_even_all_positive_cannot_be_auto_literary_promotion(self):
        report=self.known_fixture()
        record=report["results"][1]
        record["per_dimension_new_minus_old"]={k:3 for k in (
            "perception","causality","information","continuity","language")}
        record["delta"]=3.0
        record["new_score"]=90.2
        result=self.check(report)
        self.assertEqual(result["critical_all_five_regressions"],0)
        self.assertFalse(result["literary_promotion_allowed"])
        self.assertFalse(result["stable_literary_progress_proven"])
        self.assertEqual(result["validation_status"],
                         "NO_CONFIRMED_MODEL_RATED_NEGATIVE_CASE_BUT_STILL_UNVERIFIED")

if __name__=="__main__":
    unittest.main()
