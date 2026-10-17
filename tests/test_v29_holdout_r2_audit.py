"""Synthetic-only test for real-shape R2 holdout result audit."""
import json,unittest
from types import SimpleNamespace
from hashlib import sha256
from writerforge.r2_storage import _canonical
from writerforge.v29_fresh_holdout import chosen_ids,task,manifest,manifest_sha
from writerforge.reverse_discovery_models import ROLE_MODELS
from scripts.run_v29_old_new_holdout import (
    SOURCE_SHA,SOURCE_UNIT_SHA,FOLLOWING_UNIT_SHA,root_for_slot)
from scripts.audit_v29_old_new_holdout import audit
from test_v29_old_new_holdout import SOURCE,Planner,Writer,Critic
from writerforge.v29_old_new_trial import compare_old_vs_semantic

class FakeR2:
    config=SimpleNamespace(bucket="writerforge-private-library")
    def __init__(self,slots=(0,1,2),score_tamper=False):
        self.data={};self.saved=0
        for slot in slots:
            p,w,c=Planner(),Writer(),Critic()
            doc=compare_old_vs_semantic(
                planner=p,writer=w,critic=c,first=SOURCE,
                second="合成来源的后续情节。"*50,source_sha=SOURCE_SHA,
                source_window_sha=sha256(SOURCE.encode()).hexdigest(),
                writing_task=task(slot))
            doc["source_unit_sha256"]=SOURCE_UNIT_SHA
            doc["following_unit_sha256"]=FOLLOWING_UNIT_SHA
            doc["heldout_manifest"]=manifest()
            doc["heldout_manifest_sha256"]=manifest_sha()
            doc["original_task_sha256"]=sha256(task(slot).encode()).hexdigest()
            doc["slot"]=slot;doc["scenario"]=chosen_ids()[slot]
            doc["model_roles"]=dict(ROLE_MODELS)
            doc["model_usage"]={
                "calls":5,"reserved_output_tokens":30000,
                "prompt_tokens_reported":2500,"completion_tokens_reported":4300}
            if score_tamper and slot==1:
                doc["semantic_minus_legacy_model_mean"]=99
            payload=_canonical(doc)
            digest=sha256(payload).hexdigest()
            root=root_for_slot(slot)
            self.data[root+"/completed.json"]=_canonical(
                {"sha256":digest,"source_sha256":SOURCE_SHA,
                 "task_sha256":sha256(task(slot).encode()).hexdigest(),
                 "trial":"v29-sourceblind-old-vs-semantic-two-arm"})
            self.data[root+"/snapshots/"+digest+".json"]=payload
    def _head(self,key):
        return {"ContentLength":len(self.data[key])} if key in self.data else None
    def _get_small(self,key,cap):
        value=self.data[key]
        if len(value)>cap:raise ValueError("over cap")
        return value
    def _put_small_immutable(self,key,blob,digest):
        if sha256(blob).hexdigest()!=digest:raise ValueError("bad hash")
        if key in self.data and self.data[key]!=blob:raise ValueError("collision")
        if key not in self.data:self.saved+=1
        self.data[key]=blob

class HoldoutAuditTests(unittest.TestCase):
    def test_three_valid_scored_trials_are_never_literary_certification(self):
        s=FakeR2()
        r=audit(s,persist=True)
        self.assertEqual(r["valid_graded_scenarios"],3)
        self.assertFalse(r["causal_improvement_proven"])
        self.assertEqual(r["second_window"],"LOCKED")
        self.assertEqual(s.saved,1)
        audit(s,persist=True)
        self.assertEqual(s.saved,1)
        self.assertEqual(len({r["scenario"] for r in r["results"]}),3)
    def test_missing_result_not_invented_and_no_full_aggregate_saved(self):
        s=FakeR2(slots=(0,2))
        r=audit(s,persist=True)
        self.assertEqual(r["valid_graded_scenarios"],2)
        self.assertEqual(r["results"][1]["status"],"NO_GENUINE_SCORABLE_REPORT")
        self.assertIsNone(r["results"][1]["delta"])
        self.assertEqual(s.saved,0)
    def test_forged_difference_rejected(self):
        s=FakeR2(score_tamper=True)
        with self.assertRaisesRegex(ValueError,"FALSE_MODEL_IMPROVEMENT_DELTA"):
            audit(s,persist=False)
if __name__=="__main__":
    unittest.main()
