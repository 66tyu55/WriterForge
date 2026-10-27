"""WF 0.BJ fail-first: review one revealed a TRIAL DESIGN failure.

This is SOURCE ADEQUACY, not a literary scoring heuristic. It may pause
wasting a second human reader but cannot auto-judge v1/v2 or change Canon.
NO new author model calls, original texts or reader opinions fabricated.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import unittest

from experiments.wf_0bj_reader_trial_validity_gate import (
    assess_saved_trial_adequacy, assess_single_unsigned_review,
    UNFIT_REVIEW_STATUS
)
from experiments.wf_0bi_genuine_blind_review_packet import (
    inspect_blind_review_sources, build_blind_packets
)
from tempfile import TemporaryDirectory


class WF0BJHumanReviewValidity(unittest.TestCase):
    def test_source_locked_five_pairs_show_invalid_trial_design(self):
        result=assess_saved_trial_adequacy()
        self.assertEqual(result["status"],UNFIT_REVIEW_STATUS)
        self.assertEqual(result["real_model_output_pairs"],5)
        self.assertEqual(result["local_model_calls_replayed"],0)
        self.assertEqual(result["identical_completion_pairs"],[
            "asynchronous-tool-return"])
        self.assertEqual(result["both_arms_literal_source_echo_pairs"],[
            "asynchronous-tool-return"])
        self.assertEqual(result["three_b_declared_min_chars"],120)
        self.assertEqual(result["three_b_underlength_arms"],4)
        self.assertEqual(result["three_b_underlength_pairs"],2)
        self.assertTrue(result["high_overlap_0bg_quiet_pair"])
        self.assertGreater(result["quiet_pair_sequence_similarity"],0.85)
        self.assertLess(result["quiet_pair_sequence_similarity"],0.95)
        self.assertEqual(result["actual_core_wf_authoring_executions"],0)
        self.assertFalse(result["bare_model_baseline_was_collected"])
        self.assertFalse(result["can_claim_wf_vs_bare_model"])
        self.assertFalse(result["literary_quality_improved"])
        self.assertFalse(result["literary_quality_falsified"])
        self.assertFalse(result["candidate_auto_promoted"])
        self.assertEqual(result["candidate_stage"],"SHADOW")
        self.assertFalse(result["request_second_blind_reader"])

    def test_source_evidence_five_pairs_have_original_file_shas(self):
        source=inspect_blind_review_sources()
        report=assess_saved_trial_adequacy()
        self.assertEqual(set(report["source_case_ids"]),
                         {x["case_id"] for x in source})
        self.assertEqual(sum(report["real_output_counts_by_cohort"].values()),10)
        self.assertEqual(report["real_output_counts_by_cohort"]["local_0bg"],4)
        self.assertEqual(report["real_output_counts_by_cohort"]["local_0bh"],6)
        self.assertEqual(report["new_model_calls"],0)

    def test_single_unsigned_opinion_can_pause_not_award_a_winner(self):
        with TemporaryDirectory() as d:
            build_blind_packets(output=Path(d)/"bundle", random_seed=b"X"*32)
            packet=json.loads(
                (Path(d)/"bundle"/"reviewer_one"/"packet.json").read_text("utf8"))
            votes=[]
            for i,item in enumerate(packet["items"]):
                votes.append({
                    "anonymous_case_id":item["anonymous_case_id"],
                    "choice":["BOTH_BAD","TIE","A","A","A"][i],
                    "reason":"synthetic pilot feedback "+str(i),
                })
            ballot={
                "format":"wf.0bi.human-ballot.v1",
                "packet_id":packet["packet_id"],
                "reviewer_slot":"reviewer_one",
                "votes":votes
            }
            status=assess_single_unsigned_review(
                packet,ballot,evidence_label="SYNTHETIC_TEST_ONLY")
            self.assertEqual(status["status"],"SINGLE_UNSIGNED_REVIEW_DIAGNOSTIC")
            self.assertEqual(status["authenticated_independent_readers"],0)
            self.assertEqual(status["received_votes"],5)
            self.assertEqual(status["ballot_choices"]["A"],3)
            self.assertEqual(status["ballot_choices"]["TIE"],1)
            self.assertEqual(status["ballot_choices"]["BOTH_BAD"],1)
            self.assertFalse(status["win_rate_computable"])
            self.assertFalse(status["version_identity_in_ballot"])
            self.assertFalse(status["literary_benefit_proven"])
            self.assertFalse(status["auto_promote"])

    def test_wrong_packet_identity_invalid_and_no_half_results(self):
        with TemporaryDirectory() as d:
            build_blind_packets(output=Path(d)/"bundle",random_seed=b"Y"*32)
            packet=json.loads(
                (Path(d)/"bundle"/"reviewer_one"/"packet.json").read_text("utf8"))
            rows=[{"anonymous_case_id":x["anonymous_case_id"],
                   "choice":"TIE","reason":""}
                  for x in packet["items"]]
            wrong={"format":"wf.0bi.human-ballot.v1",
                   "packet_id":"forged-untrusted", "reviewer_slot":"reviewer_one",
                   "votes":rows}
            with self.assertRaises(ValueError):
                assess_single_unsigned_review(packet,wrong,
                                              evidence_label="SYNTHETIC_TEST_ONLY")
            wrong["packet_id"]=packet["packet_id"]
            wrong["votes"]=rows[:4]
            with self.assertRaises(ValueError):
                assess_single_unsigned_review(packet,wrong,
                                              evidence_label="SYNTHETIC_TEST_ONLY")

    def test_review_feedback_does_not_activate_a_shadow_capsule(self):
        out=assess_saved_trial_adequacy()
        self.assertEqual(out["original_v1_state"],"SHADOW")
        self.assertEqual(out["proposed_v2_state"],"SHADOW")
        self.assertEqual(out["new_paid_provider_calls"],0)
        self.assertEqual(out["new_cpu_model_calls"],0)
        self.assertEqual(out["production_candidate_activation"],False)


if __name__=="__main__":
    unittest.main()
