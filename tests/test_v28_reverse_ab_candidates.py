"""Offline V28 quality-evidence regressions: synthetic metadata, ZERO model calls."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import copy
import unittest

from writerforge.reverse_ab_candidates import (
    OfflineCandidateLedger, CandidateEvidenceError, derive_unverified_candidates,
    _canonical,
)

DIMENSIONS = ("perception", "causality", "information", "continuity", "language")


def synthetic_receipt():
    # Metadata shape and numeric scores mirror the published v4 comparison,
    # but this fixture is NOT downloaded private R2 evidence.
    baseline = dict(zip(DIMENSIONS, (88, 82, 85, 90, 86)))
    enhanced = dict(zip(DIMENSIONS, (92, 89, 87, 91, 90)))

    def comparison(label, values, chars, digest):
        return {
            "source_prompt": label,
            "draft_sha256": digest,
            "draft_chars": chars,
            "anonymized_critic_label": "A" if label == "baseline" else "B",
            "model_critic_score_unverified": sum(values.values()) // 5,
            "dimension_review": {
                key: {"score": value, "reason": "A private hypothetical model reason, never persisted"}
                for key, value in values.items()
            },
        }
    return {
        "format": "writerforge.cloud-ab-v1",
        "source_work": "wudongqiankun",
        "edition_sha256": "a"*64,
        "source_unit_sha256": "b"*64,
        "next_unit_sha256": "c"*64,
        "roles": {
            "planner": {"model": "deepseek-v4-flash-0731", "provider": "discovery"},
            "writer": {"model": "glm-5.3", "provider": "discovery"},
            "critic": {"model": "deepseek-v4-flash-0731", "provider": "discovery"},
        },
        "planner_mechanisms_unreviewed": [
            {"technique_id": "COST_VISIBLE_IN_ACTION", "source_paragraphs": []},
            {"technique_id": "EMOTIONAL_TURN_WITH_EVIDENCE", "source_paragraphs": []},
        ],
        "writer_prompt_source_prose_or_plot": False,
        "length_gate": {
            "comparable": True,
            "max_relative_difference": 0.15,
            "baseline_chars": 1050,
            "skill_chars": 1183,
        },
        "comparisons": {
            "baseline": comparison("baseline", baseline, 1050, "d"*64),
            "skill": comparison("skill", enhanced, 1183, "e"*64),
        },
        "uncertainty": "A potentially private discussion of novel events",
        "learned_mechanism": "A model observation, never a new craft rule",
        "drafts_retained": False,
        "human_blind_review_performed": False,
        "literal_master_quality_90pct_verified": False,
        "second_unit_unlocked": False,
        "core_automatically_promoted": False,
    }


def digest(receipt):
    return sha256(_canonical(receipt)).hexdigest()


class CandidateTests(unittest.TestCase):
    def test_numeric_facts_and_no_prose_or_promotion(self):
        receipt = synthetic_receipt()
        result = derive_unverified_candidates(receipt, receipt_sha256=digest(receipt))
        self.assertEqual(result["model_deltas"]["causality"], 7)
        self.assertEqual(result["model_deltas"]["information"], 2)
        self.assertIn({"type": "BELOW_REFERENCE_CANDIDATE",
                       "dimension": "information", "gap": 3},
                      result["fault_candidates_unreviewed"])
        self.assertEqual(result["forgetting"], "NOT_TESTED")
        self.assertFalse(result["critic_source_blind"])  # historical v4
        self.assertFalse(result["promotable"])
        self.assertEqual(result["first_window"], "NOT_PASSED")
        self.assertEqual(result["second_window"], "LOCKED")
        self.assertNotIn("A private hypothetical", str(result))
        self.assertNotIn("novel events", str(result))
        self.assertEqual(len(result["mechanism_hypotheses_unreviewed"]), 2)

    def test_same_snapshot_is_idempotent_in_durable_ledger(self):
        receipt = synthetic_receipt()
        with TemporaryDirectory() as tmp:
            ledger = OfflineCandidateLedger(Path(tmp) / "candidate.sqlite3")
            try:
                self.assertTrue(ledger.add_receipt(receipt, receipt_sha256=digest(receipt)))
                self.assertFalse(ledger.add_receipt(receipt, receipt_sha256=digest(receipt)))
                self.assertEqual(ledger.count(), 1)
                rows = ledger.db.execute("SELECT status,data_json FROM unverified_ab_trials").fetchall()
                self.assertEqual(rows[0][0], "CANDIDATE_NOT_PROMOTED")
                self.assertNotIn("hypothetical", rows[0][1])
                self.assertNotIn("novel events", rows[0][1])
            finally:
                ledger.close()
            reopened = OfflineCandidateLedger(Path(tmp) / "candidate.sqlite3")
            try:
                self.assertEqual(reopened.count(), 1)
            finally:
                reopened.close()

    def test_forged_or_changed_receipt_is_rejected(self):
        receipt = synthetic_receipt()
        h = digest(receipt)
        receipt["comparisons"]["skill"]["dimension_review"]["information"]["score"] = 100
        with self.assertRaisesRegex(CandidateEvidenceError, "digest"):
            derive_unverified_candidates(receipt, receipt_sha256=h)

    def test_leaking_original_or_fake_length_gate_is_rejected(self):
        for mutate in [
            lambda r: r.update(writer_prompt_source_prose_or_plot=True),
            lambda r: r["length_gate"].update(comparable=False),
            lambda r: r["length_gate"].update(baseline_chars=400),
            lambda r: r["comparisons"]["skill"].update(draft_chars=1800),
            lambda r: r["planner_mechanisms_unreviewed"].append(
                {"technique_id": "INVENTED_FROM_SOURCE", "source_paragraphs": []}),
        ]:
            with self.subTest(mutate=mutate):
                receipt = synthetic_receipt()
                mutate(receipt)
                with self.assertRaises(CandidateEvidenceError):
                    derive_unverified_candidates(receipt, receipt_sha256=digest(receipt))

    def test_no_fabricated_independence_from_historical_receipt(self):
        receipt = synthetic_receipt()
        receipt["critic_prompt_original_source_prose"] = False
        result = derive_unverified_candidates(receipt, receipt_sha256=digest(receipt))
        self.assertTrue(result["critic_source_blind"])
        receipt["critic_prompt_original_source_prose"] = True
        with self.assertRaises(CandidateEvidenceError):
            derive_unverified_candidates(receipt, receipt_sha256=digest(receipt))


if __name__ == "__main__":
    unittest.main()
