"""Adversarial checks: source-matched fiction hypotheses never self-certify."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest
from hashlib import sha256

ROOT = (Path(__file__).resolve().parents[1] /
        ".agents/skills/reversible-world-causality/scripts")
sys.path.insert(0, str(ROOT))
import codec
import semantic_gate
from test_wf_reversible_world_chronology import scenario

# A fixture-only key. Never use this for private novels or any real review.
SYNTHETIC_FIXTURE_KEY = b"synthetic-unit-test-not-for-any-real-world!"


def receipt(obs, claim_id, *, decision="SUPPORTED",
            role="human_editor", independent=True):
    info = semantic_gate.claims(obs)[claim_id]
    data = {
        "claim_id": claim_id,
        "claim_sha256": info["digest"],
        "decision": decision,
        "evidence_ids": info["evidence_ids"],
        "reviewer_id": "fixture-independent-human",
        "reviewer_role": role,
        "independent": independent,
        "reason": "Synthetic fixture was checked against each named source span.",
        "source_sha256": obs["source_sha256"],
    }
    data["signature"] = semantic_gate.sign_review(
        data, trusted_key=SYNTHETIC_FIXTURE_KEY)
    return data


def checked(raw, obs, reviews=(), cutoff=None, key=SYNTHETIC_FIXTURE_KEY):
    return semantic_gate.audit_and_model_prefix(
        obs, raw, "utf-8", reviews=reviews,
        trusted_key=key, cutoff_byte=cutoff)


class SemanticGateTests(unittest.TestCase):
    def test_old_schema_proves_anchors_not_truth(self):
        raw, obs = scenario()
        self.assertTrue(codec.validate_observations(obs, raw, "utf-8"))
        bad = deepcopy(obs)
        bad["links"][0]["source"], bad["links"][0]["target"] = (
            bad["links"][0]["target"], bad["links"][0]["source"])
        self.assertTrue(codec.validate_observations(bad, raw, "utf-8"))
        # New gate doesn't silently approve even the original real-looking graph.
        out = checked(raw, bad)
        self.assertEqual(out["model_prefix"]["facts"], [])
        self.assertEqual(out["model_prefix"]["links"], [])
        self.assertEqual(out["private_audit"]["quarantined_claims"],4)

    def test_no_review_never_passes_to_author(self):
        raw, obs = scenario()
        out = checked(raw, obs)
        self.assertEqual(out["private_audit"]["candidate_facts"],3)
        self.assertEqual(out["private_audit"]["candidate_links"],1)
        self.assertEqual(out["private_audit"]["quarantined_claims"],4)
        self.assertEqual(out["model_prefix"]["facts"],[])
        self.assertEqual(out["model_prefix"]["anchors"],[])
        self.assertEqual(out["model_prefix"]["links"],[])

    def test_independent_attested_facts_and_direction_can_flow(self):
        raw, obs = scenario()
        notes=[receipt(obs, "F001"), receipt(obs,"F002"), receipt(obs,"L000")]
        out = checked(raw, obs, notes)
        self.assertEqual(out["private_audit"]["supported_by_independent_human_receipt"],3)
        self.assertEqual([f["id"] for f in out["model_prefix"]["facts"]],
                         ["F001","F002"])
        self.assertEqual(len(out["model_prefix"]["links"]),1)
        self.assertFalse(out["private_audit"]["semantic_truth_machine_proven"])

    def test_reversing_signed_causal_link_does_not_pass(self):
        raw, obs = scenario()
        signed = [receipt(obs,"F001"),receipt(obs,"F002"),receipt(obs,"L000")]
        flipped = deepcopy(obs)
        flipped["links"][0]["source"],flipped["links"][0]["target"] = (
            flipped["links"][0]["target"],flipped["links"][0]["source"])
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "REVIEW_DOES_NOT_BIND_EXACT_CLAIM"):
            checked(raw,flipped,signed)

    def test_renaming_claim_to_invented_fact_invalidates_receipt(self):
        raw, obs = scenario()
        signed = [receipt(obs,"F001")]
        forged = deepcopy(obs)
        forged["facts"][0]["kind"] = "world.fantasy_kingdom_created"
        self.assertTrue(codec.validate_observations(forged,raw,"utf-8"))
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "REVIEW_DOES_NOT_BIND_EXACT_CLAIM"):
            checked(raw,forged,signed)

    def test_signed_model_opinion_or_partial_review_stays_quarantined(self):
        raw,obs=scenario()
        notes=[receipt(obs,"F001",role="independent_model"),
               receipt(obs,"F002",decision="PARTIAL"),
               receipt(obs,"F003",independent=False)]
        out=checked(raw,obs,notes)
        self.assertEqual(out["private_audit"]["reviewed_claims"],3)
        self.assertEqual(out["model_prefix"]["facts"],[])
        self.assertEqual(out["private_audit"]["quarantined_claims"],4)

    def test_wrong_key_and_tampered_receipt_rejected(self):
        raw,obs=scenario()
        one=[receipt(obs,"F001")]
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "REVIEW_SIGNATURE_MISMATCH"):
            checked(raw,obs,one,key=b"another-wrong-key-1234567890987654321")
        one[0]["reason"] = "Totally different review conclusion, changed after signing."
        with self.assertRaisesRegex(codec.ReversibleError,
                                    "REVIEW_SIGNATURE_MISMATCH"):
            checked(raw,obs,one)

    def test_sealed_prefix_does_not_disclose_later_approved_reviews(self):
        raw,obs=scenario()
        cutoff=raw.index("第二章".encode("utf-8"))
        signed=[receipt(obs,f["id"]) for f in obs["facts"]]
        signed.append(receipt(obs,"L000"))
        out=checked(raw,obs,signed,cutoff=cutoff)
        self.assertEqual([f["id"] for f in out["model_prefix"]["facts"]],["F001"])
        self.assertEqual(out["model_prefix"]["links"],[])
        self.assertNotIn("hidden_fact_count",out["model_prefix"])
        self.assertNotIn(obs["source_sha256"],str(out["model_prefix"]))

    def test_no_original_prose_in_forwarded_model_prefix(self):
        raw,obs=scenario()
        out=checked(raw,obs,[receipt(obs,"F001")])
        out_str=str(out["model_prefix"])
        for a in obs["anchors"]:
            if len(a["surface"])>1:
                self.assertNotIn(a["surface"],out_str)


if __name__=="__main__":
    unittest.main()
