"""Genuine V42 zero-model regression. Source is original, not prewritten exam answers."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge.native_experience_engine import (
    discover_experience, NativeExperienceVault, NativeExperienceError,
    make_world, causal_plan, write_native, run_experiment, _sha, TECHNIQUE,
)

SOURCE = (Path(__file__).resolve().parents[1] /
          "exams/wf_v40_reader_ch07/reader_packet.txt")


class V42NativeReaderToWriter(unittest.TestCase):
    def test_actual_original_source_is_ingested_without_host_explanation(self):
        text = SOURCE.read_text(encoding="utf-8")
        experience = discover_experience(text)
        self.assertIsNotNone(experience)
        self.assertEqual(experience.source_sha256, _sha(text))
        self.assertEqual(experience.mechanism, TECHNIQUE)
        self.assertEqual(text[experience.cause_offset:experience.cause_offset + 2], "因為")
        self.assertEqual(text[experience.consequence_offset:
                              experience.consequence_offset + 2], "所以")
        self.assertEqual(experience.status, "LEXICAL_HYPOTHESIS_UNREVIEWED")
        self.assertGreater(experience.consequence_offset, experience.cause_offset)

    def test_no_source_evidence_refuses_to_learn(self):
        self.assertIsNone(discover_experience("他缓缓走过河道，站住。"*30))
        self.assertIsNone(discover_experience("他因為忙碌。" * 24 + "所以去见人。"))
        with self.assertRaisesRegex(NativeExperienceError, "SOURCE_OUTSIDE_BOUNDS"):
            discover_experience("a")

    def test_durable_memory_survives_process_style_reopen_and_rejects_tamper(self):
        experience = discover_experience(SOURCE.read_text(encoding="utf-8"))
        with TemporaryDirectory() as td:
            p = Path(td) / "wf.sqlite3"
            db = NativeExperienceVault(p)
            receipt = db.store(experience)
            self.assertEqual(receipt, db.store(experience))
            db.close()
            db2 = NativeExperienceVault(p)
            self.assertEqual(db2.load(experience.source_sha256), experience)
            db2.close()
            with sqlite3.connect(p) as raw:
                raw.execute("UPDATE native_experience SET record_json='{}'")
            db3 = NativeExperienceVault(p)
            with self.assertRaisesRegex(NativeExperienceError, "READBACK_SHA_CHANGED"):
                db3.load(experience.source_sha256)
            db3.close()

    def test_only_persisted_candidate_changes_actual_writing(self):
        source = SOURCE.read_text(encoding="utf-8")
        with TemporaryDirectory() as td:
            r = run_experiment(source, Path(td) / "native.sqlite3",
                               ("unseen-plan-1", "unseen-plan-2", "unseen-plan-3"))
        self.assertEqual(r["status"], "NATIVE_RESTRICTED_TRANSFER_ABLATION_COMPLETED")
        self.assertEqual(r["model_calls"], 0)
        self.assertEqual(len(r["outcomes"]), 3)
        self.assertFalse(r["skill_promoted"])
        self.assertFalse(r["source_literary_role_independently_verified"])
        for case in r["outcomes"]:
            self.assertNotEqual(case["baseline_draft_sha256"],
                                case["learned_draft_sha256"])
            self.assertEqual(case["learned_cause_action_reveal_order"],
                ["observation", "cause_hypothesis", "action", "cost", "reveal"])
            body = case["actual_generated_prose"]
            self.assertGreater(len(body), 140)
            self.assertFalse(any(source[i:i + 24] in body for i in
                                 range(0, max(0, len(source) - 23), 24)))
            self.assertFalse(case["literary_quality_improvement_proven"])

    def test_blank_memory_cannot_claim_experience_transfer(self):
        trial = write_native("unseen-plan-99", None)
        self.assertEqual(trial["plan"]["learning_mode"], "ABLATION_NO_EXPERIENCE")
        self.assertEqual(trial["external_model_calls"], 0)
        self.assertIsNone(trial["plan"]["source_experience_sha256"])
        self.assertFalse(trial["literary_quality_proven"])
        self.assertTrue(trial["is_constrained_template_prose"])

    def test_no_invented_semantics_or_source_text_in_world(self):
        world = make_world("another-unseen-challenge")
        src = SOURCE.read_text(encoding="utf-8")
        self.assertTrue(all(len(x) <= 32 for x in world.values()))
        self.assertNotIn(src[250:350], "".join(world.values()))
        self.assertFalse(causal_plan("another-unseen-challenge", None)
                         ["literary_semantics_approved"])


if __name__ == "__main__":
    unittest.main()
