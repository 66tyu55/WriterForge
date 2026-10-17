"""Fake, no-network private R2 aggregator tests for 3 original fiction prompts."""
import json,unittest
from hashlib import sha256
from types import SimpleNamespace
from test_v28_reverse_ab_candidates import synthetic_receipt
from writerforge.r2_storage import _canonical
from writerforge.reverse_score_scale import baseline_30_display
from writerforge.random_original_openings import (
    selected_ids,sample_manifest,sample_sha256,task_for_slot,
)
from scripts.audit_wf_three_random_openings_v10 import (
    _root,collect,effective_task,
)
from scripts.run_wf_three_random_openings_v10 import (
    SOURCE_SHA,SOURCE_CHAPTER,SOURCE_FIRST_SHA,SOURCE_NEXT_SHA,BUDGET_PROFILE,COMMON_AB_CHARS,
)

class FakeR2:
    config=SimpleNamespace(bucket="writerforge-private-library")
    def __init__(self,slots=(0,1,2),change_source=False):
        self.store={}
        self.writes=0
        for slot in slots:
            story_id=selected_ids()[slot]
            rec=synthetic_receipt()
            rec["edition_sha256"]=SOURCE_SHA
            rec["source_unit_sha256"]=("9"*64 if change_source else SOURCE_FIRST_SHA)
            rec["next_unit_sha256"]=SOURCE_NEXT_SHA
            rec["critic_prompt_original_source_prose"]=False
            rec["writing_task_sha256"]=sha256(effective_task(slot).encode()).hexdigest()
            rec["new_original_task_sha256"]=sha256(task_for_slot(slot).encode()).hexdigest()
            rec["random_original_story_sample"]=sample_manifest()
            rec["scenario_id"]=story_id
            rec["story_scenario"]={
                "random_original_scenarios_sha256":sample_sha256(),
                "same_reference_window_for_all_slots":True,
            }
            rec["source_cursor_diagnostic"]={
                "chapter":SOURCE_CHAPTER,"source_window_sha256":SOURCE_FIRST_SHA,
                "next_contiguous_sha256":SOURCE_NEXT_SHA,
                "second_curriculum_window":"LOCKED",
            }
            rec["role_output_token_profile"]=list(BUDGET_PROFILE)
            rec["neutral_common_target_chars"]=COMMON_AB_CHARS
            rec["symmetric_length_revision_opt_in"]=True
            rec["symmetric_revision_calls"]=2 if slot==2 else 0
            rec["manuscripts_cropped_or_padded"]=False
            rec["baseline_30_display"]=baseline_30_display(rec["comparisons"])
            rec["usage"]={"api_calls":6 if slot==2 else 4,
                "requested_output_tokens_reserved":42500,
                "prompt_tokens_reported":2200,"completion_tokens_reported":9000}
            data=_canonical(rec)
            receipt_sha=sha256(data).hexdigest()
            root=_root(slot)
            self.store[root+"/completed.json"]=_canonical(
                {"sha256":receipt_sha,"source_sha256":SOURCE_SHA})
            self.store[root+f"/snapshots/{receipt_sha}.json"]=data
    def _head(self,key):
        return {"exists":True} if key in self.store else None
    def _get_small(self,key,cap):
        value=self.store[key]
        assert len(value)<=cap
        return value
    def _put_small_immutable(self,key,data,digest):
        assert sha256(data).hexdigest()==digest
        if key in self.store:assert self.store[key]==data
        else:self.store[key]=data;self.writes+=1

class ThreeRandomOriginalAuditTests(unittest.TestCase):
    def test_full_results_save_one_idempotent_hash_only_report(self):
        store=FakeR2()
        report=collect(store,persist=True)
        self.assertTrue(report["all_three_scored"])
        self.assertEqual(report["count_scored"],3)
        self.assertFalse(report["all_three_negative"])
        self.assertFalse(report["core_promoted"])
        self.assertEqual(report["second_window"],"LOCKED")
        self.assertEqual(report["results"][2]["symmetric_revision_calls"],2)
        self.assertEqual(store.writes,1)
        self.assertEqual(collect(store,persist=True),report)
        self.assertEqual(store.writes,1)
    def test_one_missing_result_does_not_invent_a_rating(self):
        store=FakeR2(slots=(0,2))
        report=collect(store,persist=True)
        self.assertEqual(report["count_scored"],2)
        self.assertFalse(report["all_three_scored"])
        self.assertFalse(report["all_three_negative"])
        self.assertIsNone(report["results"][1]["model_rating"])
        self.assertEqual(store.writes,0)
    def test_source_swap_is_rejected(self):
        store=FakeR2(change_source=True)
        with self.assertRaisesRegex(ValueError,"TASK_SOURCE_OR_LOCK"):
            collect(store,persist=False)

if __name__=="__main__":
    unittest.main()
