"""No-network validate V29 candidate ledger refuses false promotion/deletion."""
import unittest
from hashlib import sha256
from test_v29_recovered_holdout_audit import RecoveryAuditTests
from scripts.audit_v29_recovered_holdout import audit
from writerforge.v29_semantic_regression_candidates import (
    candidate_from_audit,canonical,SemanticRegressionEvidenceError,
)

class V29SemanticAntiRegressionTests(unittest.TestCase):
    def report(self):
        store=RecoveryAuditTests().create()
        data=audit(store,persist=False)
        x=data["results"][1]
        x["per_dimension_new_minus_old"]={
            "perception":-4,"causality":-8,"information":-5,
            "continuity":-4,"language":-4}
        x["old_score"]=87.2
        x["new_score"]=82.2
        x["delta"]=-5.0
        return data
    def test_negative_context_persists_even_when_other_context_positive(self):
        report=self.report()
        blob=canonical(report)
        c=candidate_from_audit(report,report_sha256=sha256(blob).hexdigest())
        self.assertEqual(len(c["observations"]),3)
        self.assertTrue(c["any_five_dimension_regression"])
        self.assertFalse(c["stable_literary_improvement_proven"])
        self.assertFalse(c["allow_core_promotion"])
        self.assertFalse(c["allow_global_mechanism_deletion"])
        self.assertEqual(c["observations"][1]["candidate_status"],
                         "TASK_SCOPED_ALL_FIVE_REGRESSION_CANDIDATE")
        self.assertEqual(c["second_window"],"LOCKED")
    def test_forged_scores_and_mismatch_refused(self):
        report=self.report()
        with self.assertRaisesRegex(SemanticRegressionEvidenceError,"AUDIT_SHA"):
            candidate_from_audit(report,report_sha256="a"*64)
        report["results"][1]["delta"]=-3
        sha=sha256(canonical(report)).hexdigest()
        with self.assertRaisesRegex(SemanticRegressionEvidenceError,"FALSE_A_B_DELTA"):
            candidate_from_audit(report,report_sha256=sha)
if __name__=="__main__":
    unittest.main()
