"""WF 0.BI RED: blind review packages from TEN genuine saved local outputs.

The test imports original first-host model traces and verifies their source
SHA before creating reviewer-facing artifacts. No model calls, no invented
reader opinions, no adjudicator AI and no private user novel or Canon.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copytree
import json
import unittest

from experiments.wf_0bi_genuine_blind_review_packet import (
    build_blind_packets, validate_packet_and_ballot,
    inspect_blind_review_sources, REVIEW_CHOICES,
    evaluate_signed_blind_ballots,
)


def sha(b: bytes) -> str:
    return sha256(b).hexdigest()


class WF0BIBlindRealModelEvidence(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.dest=Path(self.temp.name)/"packets"

    def tearDown(self):
        self.temp.cleanup()

    def generate(self):
        return build_blind_packets(output=self.dest)

    def test_five_genuine_pairs_preserve_real_byte_provenance(self):
        sources=inspect_blind_review_sources()
        self.assertEqual(len(sources),5)
        self.assertEqual(sum(1 for x in sources if x["host_group"]=="local_0bg"),2)
        self.assertEqual(sum(1 for x in sources if x["host_group"]=="local_0bh"),3)
        self.assertEqual(sum(len(x["outputs"]) for x in sources),10)
        self.assertEqual({x["case_id"] for x in sources},{
            "quiet-household-pause","asynchronous-tool-return",
            "purposeful-second-attempt","bounded-eyewitness",
            "custody-without-fulfillment",
        })
        self.assertTrue(all(
            x["outputs"]["v1"]["text_sha256"] and
            x["outputs"]["v2"]["text_sha256"] for x in sources))

    def test_two_distinct_review_packets_mask_actual_arm_and_cost(self):
        status=self.generate()
        self.assertEqual(status["status"],"BLIND_REVIEW_AWAITING_HUMAN_READERS")
        self.assertEqual(status["genuine_local_source_pairs"],5)
        self.assertEqual(status["reviewer_packets_created"],2)
        self.assertEqual(status["new_model_calls"],0)
        self.assertEqual(status["actual_independent_reader_votes"],0)
        self.assertFalse(status["literary_quality_proven"])
        self.assertFalse(status["auto_promote"])
        for label in ("reviewer_one","reviewer_two"):
            p=self.dest/label/"packet.json"
            html=self.dest/label/"REVIEW.html"
            self.assertTrue(p.is_file())
            self.assertTrue(html.is_file())
            packet=json.loads(p.read_text("utf8"))
            self.assertEqual(packet["format"],"wf.0bi.blinded-human-review-packet.v1")
            self.assertEqual(len(packet["items"]),5)
            self.assertEqual({item["host_group"] for item in packet["items"]},
                             {"local_0bg","local_0bh"})
            self.assertTrue(all(len(x["prior_prose"])==2 for x in packet["items"]))
            self.assertTrue(all(x["candidate_a"] and x["candidate_b"] for x in packet["items"]))
            html_text=html.read_text("utf8")
            self.assertIn("导出评阅结果",html_text)
            for restricted in ("v1_capsule_sha256","v2_capsule_sha256",
                               "Qwen2.5","Qwen3","original_local_completion_sha256",
                               "local_0bh_v2","source_model"):
                self.assertNotIn(restricted,p.read_text("utf8"))
                self.assertNotIn(restricted,html_text)
        secret=self.dest/"curator_ONLY"/"UNBLIND.json"
        self.assertTrue(secret.is_file())
        self.assertFalse((self.dest/"reviewer_one"/"UNBLIND.json").exists())
        self.assertFalse((self.dest/"reviewer_two"/"UNBLIND.json").exists())

    def test_second_human_gets_reversed_ab_order_for_each_case(self):
        self.generate()
        p=json.loads((self.dest/"reviewer_one"/"packet.json").read_text("utf8"))
        q=json.loads((self.dest/"reviewer_two"/"packet.json").read_text("utf8"))
        left={x["anonymous_case_id"]:x for x in p["items"]}
        right={x["anonymous_case_id"]:x for x in q["items"]}
        self.assertEqual(set(left),set(right))
        for cid,x in left.items():
            y=right[cid]
            self.assertEqual(x["candidate_a"],y["candidate_b"])
            self.assertEqual(x["candidate_b"],y["candidate_a"])
            self.assertEqual(x["prior_prose"],y["prior_prose"])
            self.assertEqual(x["task"],y["task"])
            self.assertNotEqual(x["candidate_a"],x["candidate_b"])

    def test_do_not_create_votes_or_score_on_export(self):
        status=self.generate()
        self.assertEqual(status["human_votes"],0)
        self.assertEqual(status["host_requests"],0)
        self.assertEqual(status["paid_provider_requests"],0)
        self.assertEqual(status["candidate_status"],"SHADOW")
        self.assertFalse(status["global_v2_falsification_proven"])
        self.assertFalse(status["production_recommendation"])
        self.assertEqual(status["no_auto_upgrade"],True)

    def test_json_bundle_and_html_have_no_local_model_secret_mapping(self):
        self.generate()
        for role in ("reviewer_one","reviewer_two"):
            packet=json.loads((self.dest/role/"packet.json").read_text("utf8"))
            self.assertNotIn("arm_map",packet)
            self.assertNotIn("secret",packet)
            self.assertNotIn("model_id",packet)
            self.assertNotIn("cost_tokens",packet)
            self.assertNotIn("actual_arm",packet)
            self.assertNotIn("source_file",packet)
            for item in packet["items"]:
                self.assertNotIn("v1",str(item))
                self.assertNotIn("v2",str(item))
                self.assertNotIn("prompt_tokens",str(item))
                self.assertNotIn("completion_tokens",str(item))

    def test_empty_or_partial_human_ballots_never_claim_judgment(self):
        self.generate()
        packet=json.loads((self.dest/"reviewer_one"/"packet.json").read_text("utf8"))
        missing={"format":"wf.0bi.human-ballot.v1",
                 "packet_id":packet["packet_id"],"reviewer_slot":"reviewer_one",
                 "votes":[]}
        with self.assertRaises(ValueError):
            validate_packet_and_ballot(packet,missing)
        unfinished={"format":"wf.0bi.human-ballot.v1",
                    "packet_id":packet["packet_id"],"reviewer_slot":"reviewer_one",
                    "votes":[{"anonymous_case_id":packet["items"][0]["anonymous_case_id"],
                              "choice":"A","reason":"A seems more coherent."}]}
        with self.assertRaises(ValueError):
            validate_packet_and_ballot(packet,unfinished)

    def test_reviewer_ballot_id_and_choice_must_match_original_blind_packet(self):
        self.generate()
        packet=json.loads((self.dest/"reviewer_one"/"packet.json").read_text("utf8"))
        choices=[{"anonymous_case_id":row["anonymous_case_id"],
                  "choice":"TIE","reason":""} for row in packet["items"]]
        ballot={"format":"wf.0bi.human-ballot.v1",
                "packet_id":packet["packet_id"],"reviewer_slot":"reviewer_one",
                "votes":choices}
        result=validate_packet_and_ballot(packet,ballot)
        self.assertEqual(result["valid_votes"],5)
        bad=dict(ballot,packet_id="wrong")
        with self.assertRaises(ValueError):
            validate_packet_and_ballot(packet,bad)
        forged=json.loads(json.dumps(ballot))
        forged["votes"][0]["choice"]="V2_WINS"
        with self.assertRaises(ValueError):
            validate_packet_and_ballot(packet,forged)

    def test_no_unindependent_unsigned_votes_could_mutate_production(self):
        self.generate()
        p=json.loads((self.dest/"reviewer_one"/"packet.json").read_text("utf8"))
        q=json.loads((self.dest/"reviewer_two"/"packet.json").read_text("utf8"))
        def all_ties(packet,role):
            return {"format":"wf.0bi.human-ballot.v1",
                    "packet_id":packet["packet_id"],
                    "reviewer_slot":role,
                    "votes":[{"anonymous_case_id":it["anonymous_case_id"],
                              "choice":"TIE","reason":""}
                             for it in packet["items"]]}
        result=evaluate_signed_blind_ballots(
            bundle_root=self.dest,
            ballots={"reviewer_one":all_ties(p,"reviewer_one"),
                     "reviewer_two":all_ties(q,"reviewer_two")},
            independently_trusted_reviewer_public_keys={})
        self.assertEqual(result["status"],"NOT_AUTHENTICATED_HUMAN_EVIDENCE")
        self.assertEqual(result["signed_reader_count"],0)
        self.assertFalse(result["literary_improvement_proven"])
        self.assertFalse(result["auto_promote"])
        self.assertFalse(result["global_v2_falsification_proven"])

    def test_nothing_overwritten_and_source_files_are_read_only(self):
        before=inspect_blind_review_sources()
        self.generate()
        with self.assertRaises(FileExistsError):
            self.generate()
        after=inspect_blind_review_sources()
        self.assertEqual(before,after)


if __name__=="__main__":
    unittest.main()
