"""WF 0.BG permanent source byte audit of ACTUAL 0.6B local inference.

No model inference, no provider secrets and no old 0.AY artifact needed.
All source texts are synthetic *new* public fixtures, not user R2 fiction.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copytree
from unittest.mock import patch
import json
import unittest

from experiments.wf_0bg_verify_real_local_value_observations import (
    review_observed_local_pairs, main, SOURCE,
)


class WF0BGPermanentLocalSourceEvidence(unittest.TestCase):
    def test_four_real_outputs_are_byte_locked_and_pair_effect_is_observed_not_graded(self):
        r=review_observed_local_pairs()
        self.assertEqual(r["status"],
                         "ACTUAL_LOCAL_MODEL_OUTPUTS_VERIFIED_QUALITY_UNGRADED")
        self.assertEqual(r["source_run_id"],40496101857)
        self.assertEqual(r["completed_pairs"],2)
        self.assertEqual(r["literal_identical_pairs"],1)
        self.assertEqual(r["v1_total_actual_tokens"],817)
        self.assertEqual(r["v2_total_actual_tokens"],912)
        self.assertEqual(r["actual_local_model_calls"],4)
        self.assertEqual(r["real_external_paid_provider_calls"],0)
        self.assertEqual(r["new_model_calls_in_this_review"],0)
        self.assertEqual(r["actual_independent_reader_votes"],0)
        self.assertFalse(r["literary_quality_proven"])
        self.assertFalse(r["candidate_auto_promoted"])
        self.assertEqual(r["candidate_status"],"SHADOW")
        by={row["case_id"]:row for row in r["pairs"]}
        self.assertTrue(by["asynchronous-tool-return"]["literal_generated_texts_equal"])
        self.assertFalse(by["quiet-household-pause"]["literal_generated_texts_equal"])
        self.assertEqual(
            by["asynchronous-tool-return"]["additional_v2_total_tokens"],49)
        self.assertEqual(by["quiet-household-pause"]["additional_v2_total_tokens"],46)
        self.assertEqual(
            by["asynchronous-tool-return"]["independent_literary_preference"],None)

    def test_tampered_original_local_output_is_rejected(self):
        with TemporaryDirectory() as folder:
            archive=Path(folder)/"fixture-copy"
            copytree(SOURCE,archive)
            outfile=archive/"output_03_asynchronous-tool-return_v2.json"
            outfile.write_bytes(outfile.read_bytes()+b"tampered")
            with self.assertRaisesRegex(ValueError,"OUTPUT_SHA_MISMATCH"):
                review_observed_local_pairs(archive=archive)

    def test_forged_success_and_candidate_activation_flags_fail_closed(self):
        with TemporaryDirectory() as folder:
            archive=Path(folder)/"fixture-copy"
            copytree(SOURCE,archive)
            manifest=archive/"SOURCE_MANIFEST.json"
            obj=json.loads(manifest.read_text("utf8"))
            obj["literary_gain_proven"]=True
            manifest.write_text(json.dumps(obj,ensure_ascii=False),encoding="utf8")
            with self.assertRaisesRegex(ValueError,"PROVENANCE_INVALID"):
                review_observed_local_pairs(archive=archive)

    def test_original_archived_model_sha_cannot_be_swapped(self):
        with TemporaryDirectory() as folder:
            archive=Path(folder)/"fixture-copy"
            copytree(SOURCE,archive)
            manifest=archive/"SOURCE_MANIFEST.json"
            obj=json.loads(manifest.read_text("utf8"))
            obj["model_weights_sha256"]="0"*64
            manifest.write_text(json.dumps(obj,ensure_ascii=False),encoding="utf8")
            with self.assertRaisesRegex(ValueError,"PROVENANCE_INVALID"):
                review_observed_local_pairs(archive=archive)

    def test_report_writes_only_source_checked_nonliterary_observations(self):
        with TemporaryDirectory() as folder:
            target=Path(folder)/"checked"
            with patch("urllib.request.urlopen",side_effect=AssertionError(
                    "zero provider traffic")):
                r=main(output=target)
            self.assertEqual(r["new_model_calls_in_this_review"],0)
            self.assertTrue((target/"STATUS.json").exists())
            summary=json.loads((target/"STATUS.json").read_bytes())
            self.assertEqual(summary["v1_total_actual_tokens"],817)
            self.assertEqual(summary["v2_total_actual_tokens"],912)
            self.assertFalse(summary["literary_quality_proven"])
            with self.assertRaises(FileExistsError):
                main(output=target)


if __name__=="__main__":
    unittest.main()
