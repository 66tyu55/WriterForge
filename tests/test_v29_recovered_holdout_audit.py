"""Synthetic-only mixed original-success and numeric-length-recovered R2 audit."""
import json,unittest
from hashlib import sha256
from writerforge.r2_storage import _canonical
from test_v29_holdout_r2_audit import FakeR2
from scripts.run_v29_old_new_holdout import root_for_slot as prior_root
from scripts.run_v29_old_new_length_recovery import (
    root_for_slot as recovery_root,TRIAL as recovery_trial)
from scripts.audit_v29_recovered_holdout import audit

class RecoveryAuditTests(unittest.TestCase):
    def create(self):
        store=FakeR2()
        for slot in (1,2):
            old=prior_root(slot)
            pointer=json.loads(store.data.pop(old+"/completed.json"))
            data=json.loads(store.data.pop(old+"/snapshots/"+pointer["sha256"]+".json"))
            data["recovery_context"]={
                "original_v29_slot_failed_unscorable":True,
                "original_v29_score":None,
                "only_own_length_guidance_changed_in_symmetric_revision":True,
                "old_score_kept_only_if_same_new_trial_both_scored":True,
                "never_reuses_or_overwrites_old_round":True,
            }
            blob=_canonical(data)
            h=sha256(blob).hexdigest()
            root=recovery_root(slot)
            store.data[root+"/completed.json"]=_canonical({
                "sha256":h,"source_sha256":data["source_sha256"],
                "trial":recovery_trial,
                "task_sha256":data["writing_task_sha256"]})
            store.data[root+"/snapshots/"+h+".json"]=blob
        return store
    def test_mixed_recovery_never_pretends_identical_protocol(self):
        store=self.create()
        doc=audit(store,persist=True)
        self.assertEqual(doc["valid_graded_scenarios"],3)
        self.assertTrue(doc["mixed_length_protocol_between_slot0_and_recovery_slots"])
        self.assertTrue(doc["fair_same_protocol_within_each_old_vs_new_pair"])
        self.assertFalse(doc["causal_improvement_proven"])
        self.assertEqual(doc["second_window"],"LOCKED")
        self.assertEqual(store.saved,1)
    def test_missing_recovery_remains_unscored(self):
        store=self.create()
        store.data.pop(recovery_root(2)+"/completed.json")
        doc=audit(store,persist=True)
        self.assertEqual(doc["valid_graded_scenarios"],2)
        self.assertEqual(doc["results"][2]["status"],"NO_GENUINE_SCORABLE_REPORT")
        self.assertEqual(store.saved,0)
if __name__=="__main__":
    unittest.main()
