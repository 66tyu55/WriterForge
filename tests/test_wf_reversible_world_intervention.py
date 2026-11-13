"""Counterfactuals cannot replay sealed source facts or invent certainty."""
from pathlib import Path
import sys
import unittest

ROOT = (Path(__file__).resolve().parents[1] /
        ".agents/skills/reversible-world-causality/scripts")
sys.path.insert(0, str(ROOT))
import codec
import intervention
from test_wf_reversible_world_chronology import scenario


def frozen():
    raw, obs = scenario()
    cutoff = raw.index("第二章".encode())
    change = {"id":"I001", "mode":"modify",
              "target_fact_id":"F001", "kind":"actor.choice",
              "cause_tag":"irrational_choice"}
    branch = intervention.prepare_branch(
        obs, raw, "utf-8", cutoff_byte=cutoff, change=change)
    return raw, obs, branch


def proposed(branch, candidates):
    return {"contract_sha256":branch["contract_sha256"],
            "candidate_futures":candidates}


class CounterfactualTests(unittest.TestCase):
    def test_existing_future_is_not_replayed(self):
        raw, obs, branch = frozen()
        self.assertEqual(branch["source_visible_fact_ids"],["F001"])
        self.assertEqual(branch["prior_original_future_facts_in_branch"],[])
        self.assertEqual(branch["prior_original_future_links_in_branch"],[])
        self.assertNotIn("withheld_original_fact_count", branch)
        self.assertFalse(branch["original_future_knowledge_disclosed"])
        self.assertFalse(branch["replay_original_future_after_change"])

    def test_modified_fact_must_be_visible(self):
        raw, obs, branch = frozen()
        change = {"id":"I002","mode":"modify",
                  "target_fact_id":"F002","kind":"actor.choice",
                  "cause_tag":"observed_constraint"}
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "INTERVENTION_TARGET_NOT_IN_SEEN_SOURCE"):
            intervention.prepare_branch(
                obs, raw, "utf-8",
                cutoff_byte=branch["cutoff_byte"],change=change)

    def test_inserted_accident_can_be_unexplained(self):
        raw, obs, branch = frozen()
        change = {"id":"I002","mode":"insert",
                  "target_fact_id":None,"kind":"chance.interruption",
                  "cause_tag":"unknown_origin"}
        b = intervention.prepare_branch(
            obs,raw,"utf-8",cutoff_byte=branch["cutoff_byte"],change=change)
        candidate = {"id":"H001","kind":"unexpected.consequence",
                     "basis_fact_ids":[],"status":"UNEXPLAINED",
                     "cause_tag":"unknown_origin"}
        self.assertTrue(intervention.validate_proposal(
            b,proposed(b,[candidate]))["structurally_accepted"])

    def test_hidden_fact_and_certain_future_are_rejected(self):
        _,_,branch=frozen()
        bad = {"id":"H001","kind":"possible.change",
               "basis_fact_ids":["F002"],"status":"POSSIBLE",
               "cause_tag":"observed_constraint"}
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "PREDICTION_USED_UNSEEN_ORIGINAL_FACT"):
            intervention.validate_proposal(branch,proposed(branch,[bad]))
        bad["basis_fact_ids"]=["F001"]
        bad["status"]="CERTAIN"
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "PROPOSED_FUTURE_CANNOT_BE_CERTAIN"):
            intervention.validate_proposal(branch,proposed(branch,[bad]))

    def test_relabeling_original_future_as_hypothesis_requires_visible_basis(self):
        _,_,branch=frozen()
        bad = {"id":"F002","kind":"future.result",
               "basis_fact_ids":["F001"],"status":"POSSIBLE",
               "cause_tag":"observed_constraint"}
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "FUTURE_ID_MUST_BE_FRESH_HYPOTHESIS"):
            intervention.validate_proposal(branch,proposed(branch,[bad]))

    def test_unfounded_cause_disallowed_but_unknown_permitted(self):
        _,_,branch=frozen()
        bare = {"id":"H007","kind":"world.perturbation",
                "basis_fact_ids":[],"status":"POSSIBLE",
                "cause_tag":"observed_constraint"}
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "UNSUPPORTED_CAUSAL_EXPLANATION"):
            intervention.validate_proposal(branch,proposed(branch,[bare]))
        bare["status"]="UNKNOWN"
        self.assertTrue(intervention.validate_proposal(
            branch, proposed(branch,[bare]))["structurally_accepted"])

    def test_contract_tampering_does_not_promote_candidate(self):
        _,_,branch=frozen()
        branch["original_future_knowledge_disclosed"]=True
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "BRANCH_CONTRACT_TAMPERED"):
            intervention.validate_proposal(branch,proposed(branch,[]))


if __name__=="__main__":
    unittest.main()
