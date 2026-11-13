"""Frozen two-arm original-grounded time parameter discovery experiment tests.

These tests prove leakage boundaries and reject missing evidence citations.
They NEVER count hypothetical extraction as successful literary learning.
"""
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"experiments"))
import wf_time_event_first_autonomous_once as trial

class AutonomousTimeDiscoveryTests(unittest.TestCase):
    def test_same_visible_observations_in_two_methods(self):
        d=trial.dataset()
        a=trial.user_prompt(d,"direct")
        b=trial.user_prompt(d,"event_first")
        content=trial.context(d)
        self.assertIn(content,a)
        self.assertIn(content,b)
        self.assertEqual(len(d["observations"]),11)
        self.assertNotEqual(a,b)

    def test_future_and_original_cannot_enter_model_prompt(self):
        d=trial.dataset()
        prompts=[trial.user_prompt(d,n) for n in trial.ARMS]
        for p in prompts:
            self.assertNotIn(d["experiment"]["source_future_sha256"],p)
            self.assertNotIn(d["scope"]["source_view_sha256"],p)
            self.assertNotIn("18-19",p)
            self.assertNotIn("《仙逆》",p)
            self.assertNotIn(d["experiment"]["rubric_sha256"],p)
        pre=trial.preflight()
        self.assertEqual(pre["planned_actual_model_calls"],2)
        self.assertFalse(pre["independent_human_review"])
        self.assertFalse(pre["model_weight_training"])

    def test_grounded_candidate_only_passes_syntax_not_truth(self):
        d=trial.dataset()
        p={k:"已知条件" for k in
           ("id","owner","trigger","variable","unit","update_rule",
            "epistemic","could_change","failure_if_missing")}
        p["evidence_ids"]=["O07","O08"]
        result,ids=trial.validate_candidate(
          {"questions":[],"parameters":[p],"abstentions":[]},d)
        self.assertEqual(result["status"],"STRUCTURAL_ONLY")
        self.assertEqual(len(ids),1)
        self.assertEqual(result["source_semantic_accuracy"],"UNASSESSED")

    def test_unseen_and_fake_observation_ids_not_accepted(self):
        d=trial.dataset()
        p={k:"未知" for k in
           ("id","owner","trigger","variable","unit","update_rule",
            "epistemic","could_change","failure_if_missing")}
        p["evidence_ids"]=["O99"]
        result,ids=trial.validate_candidate(
          {"questions":[],"parameters":[p],"abstentions":[]},d)
        self.assertEqual(ids,[])
        self.assertEqual(result["rejected_claims"][0]["reason"],
                         "SOURCE_ID_NOT_VISIBLE")

    def test_malformed_output_and_number_of_fields_never_auto_corrected(self):
        d=trial.dataset()
        a,b=trial.validate_candidate({"parameters":[]} ,d)
        self.assertEqual(a["status"],"MALFORMED_OR_INCOMPLETE")
        self.assertFalse(b)

    def test_no_hidden_novel_text_in_public_package(self):
        d=trial.dataset()
        self.assertTrue(d["scope"]["independent_human_gold"] is False)
        self.assertTrue(d["constraints"]["no_guaranteed_breakthrough"])
        self.assertTrue(d["constraints"]["unknown_absolute_calendar"])
        self.assertTrue(d["constraints"]["no_known_time_multiplier"])

if __name__=="__main__":unittest.main()
