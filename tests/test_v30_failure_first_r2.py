"""No-network test: R2 backfill must use real hash, not fabricated scores."""
from hashlib import sha256
from unittest.mock import patch
import unittest
from test_v29_recovered_holdout_audit import RecoveryAuditTests
from test_v30_failure_first_adversarial import V30AdversarialFailureTests
from writerforge.v29_semantic_regression_candidates import canonical
from scripts.audit_v30_failure_first_real_r2 import run,SOURCE_PREFIX,V30_PREFIX
import scripts.audit_v30_failure_first_real_r2 as importer

class V30RealR2ReadbackTests(unittest.TestCase):
    def make_fake(self):
        store=RecoveryAuditTests().create()
        report=V30AdversarialFailureTests().known_fixture()
        payload=canonical(report)
        digest=sha256(payload).hexdigest()
        key=f"{SOURCE_PREFIX}/three-slot-holdout-audit/{digest}.json"
        store.data[key]=payload
        return store,digest,key

    def test_immutable_failure_first_record_on_verified_real_shape(self):
        store,digest,_=self.make_fake()
        with patch.object(importer,"SOURCE_AGGREGATE_SHA",digest):
            summary=run(store)
            again=run(store)
        self.assertEqual(summary,again)
        self.assertEqual(summary["five_dimension_negative_cases"],1)
        self.assertFalse(summary["promotion_allowed"])
        self.assertEqual(summary["absolute_length_noncompliant_cases"],2)
        self.assertEqual(summary["same_mechanism_positive_excluded_from_selector_credit"],1)
        self.assertEqual(summary["model_calls"],0)
        key=f'{V30_PREFIX}/immutable-audits/{summary["new_immutable_sha256"]}.json'
        self.assertIn(key,store.data)
        self.assertEqual(sha256(store.data[key]).hexdigest(),summary["new_immutable_sha256"])

    def test_tamper_prevents_write(self):
        store,digest,key=self.make_fake()
        store.data[key]=store.data[key]+b"unexpected suffix"
        with patch.object(importer,"SOURCE_AGGREGATE_SHA",digest):
            with self.assertRaisesRegex(ValueError,"SCORE_AGGREGATE_TAMPERED"):
                run(store)
        self.assertFalse(any(k.startswith(V30_PREFIX) for k in store.data))

if __name__=="__main__":
    unittest.main()
