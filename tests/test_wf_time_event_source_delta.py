"""Time parameter revisions from sealed original-chapter deltas (no novel text)."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/
    ".agents/skills/xianxia-time-rule/scripts"))
import temporal_delta as t

def claim(ident,entity,key,value,seq,relation="UNKNOWN",epistemic="NARRATED",
          kind="PHYSICAL",elapsed=None):
    return {"id":ident,"entity":entity,"property":key,"value":value,
            "evidence_ids":[ident],"reveal_index":seq,
            "story_relation_to_prior":relation,"epistemic":epistemic,
            "event_type":kind,"elapsed_status":elapsed}

class DynamicTimeRuleEvidenceTests(unittest.TestCase):
    def test_later_decay_is_a_change_not_an_invented_numeric_decay_rate(self):
        out=t.propose_changes([
            claim("E01","X002","resource_potency","ACTIVE",1),
            claim("H13","X002","resource_potency","DEPLETED",2,"AFTER",
                  elapsed="about one month")])
        next_=out["candidates"][1]
        self.assertEqual(next_["classification"],"OBSERVED_STATE_CHANGE_CANDIDATE")
        self.assertEqual(next_["previous_claim_id"],"E01")
        self.assertIsNone(next_["inferred_physical_rate"])
        self.assertTrue(out["all_past_claims_preserved"])

    def test_social_promise_not_immutable_natural_law(self):
        out=t.propose_changes([
            claim("E01","P003","reward_status","OFFERED",1,kind="SOCIAL"),
            claim("H06","P003","reward_status","DELIVERED",2,
                  relation="AFTER",kind="SOCIAL")])
        self.assertEqual(out["candidates"][1]["classification"],
                         "SOCIAL_DECISION_CHANGE_CANDIDATE")
        self.assertFalse(out["world_rule_commit_approved"])

    def test_new_information_not_old_world_time_event(self):
        out=t.propose_changes([
            claim("E01","P001","cause_of_failed_training","UNKNOWN",1,
                  epistemic="UNKNOWN",kind="KNOWLEDGE"),
            claim("H11","P001","cause_of_failed_training","EXTERNAL_INHIBITOR",2,
                  relation="UNKNOWN",epistemic="REPORTED",kind="KNOWLEDGE")])
        self.assertEqual(out["candidates"][1]["classification"],
                         "NEW_INFORMATION_OR_CONTRADICTION_NOT_PROVEN_CHANGE")

    def test_new_lifetime_technique_quota_is_discovery_not_now_created(self):
        out=t.propose_changes([
            claim("H07","P003","lifetime_use_quota","THREE",2,
                  epistemic="REPORTED")])
        self.assertEqual(out["candidates"][0]["classification"],
                         "FIRST_REVEALED_EVIDENCE")

    def test_same_value_cannot_launder_another_cause(self):
        out=t.propose_changes([
            claim("E01","P001","progress","NONE",1),
            claim("H02","P001","progress","NONE",2,relation="AFTER")])
        self.assertEqual(out["candidates"][1]["classification"],
                         "ADDITIONAL_SOURCE_SUPPORT_NOT_NEW_RULE")

    def test_unverified_sources_and_story_order_are_rejected(self):
        x=claim("H01","X","a","b",1)
        x["evidence_ids"]=[]
        with self.assertRaisesRegex(t.TemporalDeltaError,"SOURCE_EVIDENCE_REQUIRED"):
            t.propose_changes([x])
        x=claim("H01","X","a","b",1)
        x["story_relation_to_prior"]="ALWAYS"
        with self.assertRaisesRegex(t.TemporalDeltaError,"STORY_TIME_RELATION_INVALID"):
            t.propose_changes([x])

if __name__=="__main__":
    unittest.main()
