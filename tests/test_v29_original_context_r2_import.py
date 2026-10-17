"""Zero-model true-schema R2 candidate import tests (synthetic receipts only)."""
from hashlib import sha256
from types import SimpleNamespace
import unittest,json
from writerforge.r2_storage import _canonical
from test_v28_three_random_openings_audit import FakeR2
from scripts.audit_wf_three_random_openings_v10 import collect
from scripts.import_v29_original_story_context_r2 import (
    import_candidates,AGGREGATE_SHA,PREFIX,
)
import scripts.import_v29_original_story_context_r2 as importer

class CandidateR2Test(unittest.TestCase):
    def prepare(self):
        store=FakeR2()
        report=collect(store,persist=False)
        raw=_canonical(report)
        h=sha256(raw).hexdigest()
        store.store[f"{PREFIX}/three-original-openings-audit/{h}.json"]=raw
        return store,h
    def test_private_immutable_candidates_no_critical_overwrites(self):
        store,h=self.prepare()
        with unittest.mock.patch.object(importer,"AGGREGATE_SHA",h):
            result=import_candidates(store)
            again=import_candidates(store)
        self.assertEqual(result,again)
        self.assertFalse(result["new_rules_promoted"])
        self.assertEqual(result["paid_model_calls"],0)
        self.assertEqual(result["second_window"],"LOCKED")
        path=f'{PREFIX}/unreviewed-story-context-candidates/{result["candidate_sha256"]}.json'
        payload=json.loads(store.store[path])
        self.assertFalse(payload["disable_global_mechanisms"])
        self.assertFalse(payload["automatic_skill_promotion"])
        self.assertEqual(len(payload["model_only_contextual_observations"]),3)
    def test_tampered_aggregate_refuses_candidate_write(self):
        store,h=self.prepare()
        original=f"{PREFIX}/three-original-openings-audit/{h}.json"
        store.store[original]+=b"corruption"
        with unittest.mock.patch.object(importer,"AGGREGATE_SHA",h):
            with self.assertRaisesRegex(ValueError,"SHA_MISMATCH"):
                import_candidates(store)

if __name__=="__main__":
    unittest.main()
