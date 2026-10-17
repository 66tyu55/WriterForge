"""Three-chapter R2 aggregation tests using synthetic scores and no models."""
import json, unittest
from hashlib import sha256
from types import SimpleNamespace

from test_v28_reverse_ab_candidates import synthetic_receipt
from writerforge.reverse_random_chapters import chosen_chapters,selection_hash,SOURCE_SHA
from writerforge.reverse_score_scale import baseline_30_display
from writerforge.r2_storage import _canonical
from scripts.audit_wudong_random3_v7_r2 import collect,_root,PINS,TRANSFER_TASK

class FakePrivateR2:
    def __init__(self,score_overrides=None):
        self.config=SimpleNamespace(bucket="writerforge-private-library")
        self.store={}
        self.writes=0
        for slot,chapter in enumerate(chosen_chapters()):
            doc=synthetic_receipt()
            doc["edition_sha256"]=SOURCE_SHA
            doc["source_unit_sha256"]=PINS[chapter][1]
            doc["next_unit_sha256"]=PINS[chapter][2]
            doc["critic_prompt_original_source_prose"]=False
            doc["writing_task_sha256"]=sha256(TRANSFER_TASK.encode()).hexdigest()
            doc["random_chapter_sample"]={
                "protocol":"V28_RANDOM3_BEFORE_SCORE",
                "selection_sha256":selection_hash(),"slot":slot,"chapter":chapter,
                "selected_chapters":list(chosen_chapters()),
                "randomness_pinned_before_scoring":True,
            }
            doc["source_cursor_diagnostic"]={
                "chapter":chapter,"source_window_sha256":PINS[chapter][1],
                "next_contiguous_sha256":PINS[chapter][2],
                "chapter_body_sha256":PINS[chapter][0],
                "semantic_boundary_verified":False,
                "diagnostic_only_no_promotion":True,
                "second_curriculum_window":"LOCKED",
            }
            score=score_overrides[slot] if score_overrides else 70
            for dim in ("perception","causality","information","continuity","language"):
                doc["comparisons"]["skill"]["dimension_review"][dim]["score"]=score
            doc["comparisons"]["skill"]["model_critic_score_unverified"]=score
            doc["baseline_30_display"]=baseline_30_display(doc["comparisons"])
            doc["usage"]={"api_calls":4,"requested_output_tokens_reserved":36500,
                          "prompt_tokens_reported":2500,"completion_tokens_reported":3000}
            payload=_canonical(doc)
            digest=sha256(payload).hexdigest()
            root=_root(slot,chapter)
            self.store[root+"/completed.json"]=_canonical(
                {"sha256":digest,"source_sha256":SOURCE_SHA})
            self.store[root+f"/snapshots/{digest}.json"]=payload
    def _get_small(self,key,cap):
        value=self.store[key]
        assert len(value)<=cap
        return value
    def _put_small_immutable(self,key,data,digest):
        assert sha256(data).hexdigest()==digest
        if key not in self.store:self.store[key]=data;self.writes+=1
        else:assert self.store[key]==data

class AggregationTests(unittest.TestCase):
    def test_all_three_are_negative_and_immutable(self):
        store=FakePrivateR2([70,71,72])
        a=collect(store,persist=True)
        b=collect(store,persist=True)
        self.assertEqual(a,b)
        self.assertTrue(a["all_three_negative_relative_to_baseline"])
        self.assertTrue(a["all_three_five_dimensions_negative"])
        self.assertEqual(a["chapters"],[3,15,17])
        self.assertEqual(store.writes,1)
        self.assertFalse(a["core_promoted"])
        self.assertEqual(a["second_window"],"LOCKED")
    def test_one_positive_prevents_fabricated_universal_decline(self):
        store=FakePrivateR2([70,95,72])
        report=collect(store,persist=False)
        self.assertFalse(report["all_three_negative_relative_to_baseline"])
        self.assertFalse(report["all_three_five_dimensions_negative"])
        self.assertEqual(report["count"],3)
    def test_broken_hash_or_source_anchor_is_rejected(self):
        store=FakePrivateR2([70,71,72])
        key=next(k for k in store.store if "/snapshots/" in k)
        store.store[key]+=b"corrupt"
        with self.assertRaises(ValueError):
            collect(store,persist=False)

if __name__=="__main__":
    unittest.main()
