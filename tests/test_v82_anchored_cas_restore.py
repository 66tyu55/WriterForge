"""V82 incremental Reader-only cold R2 checkpoint verification (fake CAS only).

Validates immutable V81 prefix and V82 chapter-range suffix without fetching
and paying or repeating V81's already-audited 121 older source events.
All newly added units are still independently checked against original text
by the real V82 examiner (separate module).
"""
from __future__ import annotations
from hashlib import sha256
import unittest

from writerforge.v79_provisional_r2_cas_journal import (
    WFProvisionalR2CASJournal,FORMAT,
)
from writerforge.r2_learn_journal import (
    WFLearnJournalError,canonical,
)
from test_v80_150k_batch import MemoryCAS

READER="synthetic-reader-only-secret-mock-v82"
SOURCE_KEY="a"*64
SOURCE_SHA="b"*64
ROOT="writerforge/v1/learn/v1/"+SOURCE_KEY+"/"+SOURCE_SHA+"/"


class TestAnchoredColdReader(unittest.TestCase):
    def setUp(self):
        self.storage={}
        self.reader=WFProvisionalR2CASJournal(
            endpoint="https://wf-r2-api.synthetic.workers.dev",
            reader_token=READER,read_only=True)
        self.reader.vault=MemoryCAS(self.storage)
        self.old_key=ROOT+"000010/seal.json"
        self.new_key=ROOT+"000011/first/000001.json"
        self.old_sha=sha256(b"old event").hexdigest()
        self.new_sha=sha256(b"new event").hexdigest()
        self.prev=self.commit({self.old_key:self.old_sha})
        self.cur=self.commit({
            self.old_key:self.old_sha,
            self.new_key:self.new_sha,
        })

    def commit(self,events):
        body={
            "format":FORMAT,
            "single_writer":True,
            "native_learn_route_deployed":False,
            "literary_mastery_verified":False,
            "storage_namespace":"indexes/v1/chunks",
            "event_addresses":events,
            "previous_checkpoint_sha256":None,
        }
        raw=canonical(body)
        digest=sha256(raw).hexdigest()
        from writerforge.r2_index_vault import chunk_key
        self.storage[chunk_key(digest)]=raw
        return digest

    def test_anchors_prior_prefix_and_marks_new_entries_unverified(self):
        result=self.reader.restore_anchored_suffix(
            final_checkpoint_sha=self.cur,
            independently_verified_prior_sha=self.prev,
            first_new_chapter=11,last_new_chapter=15)
        self.assertEqual(result["unchanged_prior_event_count"],1)
        self.assertEqual(result["new_event_count_requiring_independent_review"],1)
        self.assertTrue(result["all_prior_r2_event_pointers_unchanged"])
        self.assertFalse(result["all_intermediate_checkpoints_verified"])
        self.assertFalse(result["literary_quality_independently_verified"])
        self.assertTrue(self.reader.read_only)
        self.assertIsNone(self.reader.writer)

    def test_rewriting_prev_pointer_fails(self):
        modified=self.commit({
            self.old_key:"c"*64,
            self.new_key:self.new_sha,
        })
        with self.assertRaisesRegex(WFLearnJournalError,
                                    "PREVIOUS_TRAINING_WAS_REWRITTEN"):
            self.reader.restore_anchored_suffix(
                final_checkpoint_sha=modified,
                independently_verified_prior_sha=self.prev)

    def test_out_of_range_suffix_rejected(self):
        wrong=self.commit({
            self.old_key:self.old_sha,
            ROOT+"000016/seal.json":self.new_sha,
        })
        with self.assertRaisesRegex(WFLearnJournalError,
                                    "OUTSIDE_CHAPTER_RANGE"):
            self.reader.restore_anchored_suffix(
                final_checkpoint_sha=wrong,
                independently_verified_prior_sha=self.prev)

    def test_unsafe_writer_exam_rejected(self):
        self.reader.read_only=False
        with self.assertRaisesRegex(WFLearnJournalError,
                                    "REQUIRES_READER_ONLY"):
            self.reader.restore_anchored_suffix(
                final_checkpoint_sha=self.cur,
                independently_verified_prior_sha=self.prev)

if __name__=="__main__":
    unittest.main()
