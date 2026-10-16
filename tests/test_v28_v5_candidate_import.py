"""Zero-network v5 private abstract evidence import regression."""
import unittest
from unittest.mock import patch
from hashlib import sha256
from types import SimpleNamespace
import scripts.import_v28_v5_transfer_candidates_r2 as importer
from writerforge.r2_storage import _canonical
from test_v28_reverse_ab_candidates import synthetic_receipt

class FakeStore:
    def __init__(self, raw):
        self.config=SimpleNamespace(bucket="writerforge-private-library")
        self.raw=raw
        self.store={}
    def _get_small(self,key,cap):
        data=self.raw if "/snapshots/" in key else self.store[key]
        assert len(data)<=cap
        return data
    def _put_small_immutable(self,key,payload,digest):
        assert sha256(payload).hexdigest()==digest
        if key in self.store:assert self.store[key]==payload
        else:self.store[key]=payload

class V5CandidateTest(unittest.TestCase):
    def test_immutable_v5_source_blind_import(self):
        data=synthetic_receipt()
        data["critic_prompt_original_source_prose"]=False
        raw=_canonical(data)
        fake=FakeStore(raw)
        with patch.object(importer,"RECEIPT_SHA",sha256(raw).hexdigest()),patch.object(importer,"SOURCE_SHA","a"*64):
            first=importer.import_prior_receipt(fake)
            second=importer.import_prior_receipt(fake)
        self.assertEqual(first,second)
        self.assertEqual(first["model_calls"],0)
        self.assertEqual(first["second_window"],"LOCKED")
        self.assertEqual(len(fake.store),1)
        self.assertNotIn(b"hypothetical",next(iter(fake.store.values())))
if __name__=="__main__":
    unittest.main()
