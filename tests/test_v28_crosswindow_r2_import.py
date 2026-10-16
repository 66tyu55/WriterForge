"""No-network immutable R2 cross-chapter report regression."""
import unittest
from unittest.mock import patch
from hashlib import sha256
from types import SimpleNamespace
from writerforge.r2_storage import _canonical
from test_v28_cross_window_review import fake_pair,h
import scripts.import_v28_chapter2_regression_evidence_r2 as reader

class FakeR2:
    def __init__(self,a,b,sha5,sha6):
        self.config=SimpleNamespace(bucket="writerforge-private-library")
        self.data={
            f'{reader.trial_root(reader.V5_TRIAL,"opening-chapter-1-contiguous-window-1")}/snapshots/{sha5}.json':_canonical(a),
            f'{reader.trial_root(reader.V6_TRIAL,"chapter-2-contiguous-window-1-diagnostic-only")}/snapshots/{sha6}.json':_canonical(b),
            f'{reader.trial_root(reader.V6_TRIAL,"chapter-2-contiguous-window-1-diagnostic-only")}/completed.json':_canonical({"sha256":sha6,"source_sha256":"a"*64}),
        }
        self.additions=0
    def _get_small(self,key,cap):
        data=self.data[key]
        assert len(data)<=cap
        return data
    def _put_small_immutable(self,key,payload,digest):
        assert sha256(payload).hexdigest()==digest
        if key in self.data:assert self.data[key]==payload
        else:self.data[key]=payload;self.additions+=1

class TestCrossImport(unittest.TestCase):
    def test_two_known_receipts_no_model_calls_idempotent(self):
        a,b=fake_pair(v6_skill=61)
        source_hash=sha256(reader.TRANSFER_TASK.encode("utf-8")).hexdigest()
        a["writing_task_sha256"]=b["writing_task_sha256"]=source_hash
        with patch.object(reader,"SOURCE_SHA","a"*64),patch.object(reader,"V5_SHA",h(a)):
            store=FakeR2(a,b,h(a),h(b))
            result=reader.audit_and_store(store)
            second=reader.audit_and_store(store)
        self.assertEqual(result,second)
        self.assertEqual(store.additions,1)
        self.assertEqual(result["model_calls"],0)
        self.assertTrue(result["sharp_drop_threshold_observed"])
        self.assertFalse(result["core_promoted"])
        self.assertEqual(result["second_window"],"LOCKED")
        saved=[v for k,v in store.data.items() if "/cross-window-candidates/" in k]
        self.assertEqual(len(saved),1)
        self.assertNotIn(b"fiction",saved[0])

if __name__=="__main__":
    unittest.main()
