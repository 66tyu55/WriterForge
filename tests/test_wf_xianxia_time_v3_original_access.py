"""A source-specific time access quota cannot silently produce age or training."""
from __future__ import annotations
from pathlib import Path
import sys,unittest
S=Path(__file__).resolve().parents[1]/".agents/skills/xianxia-time-rule/scripts"
sys.path.insert(0,str(S))
import time_parameters_v3 as t

def source_rule():
    return {"frame_id":"private_dream_space",
            "max_visits_per_world_day":3,
            "reported_entry_duration":{
              "quantity":"20","unit":"shichen","qualifier":"MORE_THAN"},
            "source_claim_status":"narrated","universal_rule":False}

class FullOriginalTimeTrainingCaseTests(unittest.TestCase):
    def test_visits_per_day_are_separate_from_flow_multiplier(self):
        d=source_rule();state={"day_id":None,"visits_used":0}
        for n in (1,2,3):
            record=t.admit_frame_visit(d,state,world_day_id=100)
            self.assertEqual(record["next_state"]["visits_used"],n)
            self.assertIsNone(record["subjective_elapsed_from_visit"])
            self.assertIsNone(record["cultivation_credit_from_visit"])
            self.assertIsNone(record["biological_aging_from_visit"])
            self.assertFalse(record["source_reported_duration_exact"])
            state=record["next_state"]
        with self.assertRaisesRegex(ValueError,"FRAME_DAILY_ENTRY_QUOTA_EXHAUSTED"):
            t.admit_frame_visit(d,state,world_day_id=100)
        next_day=t.admit_frame_visit(d,state,world_day_id=101)
        self.assertEqual(next_day["next_state"]["visits_used"],1)

    def test_time_quota_must_be_scoped_not_universal_law(self):
        d=source_rule();d["universal_rule"]=True
        with self.assertRaisesRegex(ValueError,"FRAME_QUOTA_NOT_SOURCE_BOUNDED"):
            t.admit_frame_visit(d,{"day_id":None,"visits_used":0},
                                world_day_id=100)

    def test_subjective_training_does_not_prove_bodily_aging(self):
        result=t.do_not_infer_aging_from_cultivation("1 calendar_year")
        self.assertIsNone(result["biological_age_increment"])
        self.assertTrue(result["may_not_set_to_cultivation_credit"])
        direct=t.do_not_infer_aging_from_cultivation(
           "1 calendar_year",direct_age_evidence={
               "duration":"2","unit":"calendar_month","epistemic":"reported"})
        self.assertEqual(direct["biological_age_increment"],"2")

    def test_no_unverifiable_visits_in_past_and_no_cliff_jumps(self):
        d=source_rule()
        with self.assertRaisesRegex(ValueError,"FRAME_QUOTA_STATE_INVALID"):
            t.admit_frame_visit(d,{"day_id":101,"visits_used":2},world_day_id=100)
        with self.assertRaisesRegex(ValueError,"FRAME_QUOTA_STATE_INVALID"):
            t.admit_frame_visit(d,{"day_id":101,"visits_used":False},world_day_id=101)

    def test_quota_cannot_turn_approximate_upper_bound_into_exact(self):
        d=source_rule()
        d["reported_entry_duration"]["qualifier"]="MORE_THAN"
        out=t.admit_frame_visit(d,{"day_id":None,"visits_used":0},world_day_id=1)
        self.assertFalse(out["source_reported_duration_exact"])
        self.assertTrue(out["rate_and_quota_separately_required"])

if __name__=="__main__":unittest.main()
