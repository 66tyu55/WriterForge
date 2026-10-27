"""WF 0.BH source-first test of six actual local 3B model outputs.

No model loading or network. Test data points to immutable local GGUF
generation #40499625320; cannot upgrade Skill from unreviewed evidence.
"""
from __future__ import annotations

from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from experiments.wf_0bh_verify_stronger_local_origins import (
    verify_stronger_local_originals, save_verified_observation, SOURCE,
)


class WF0BHActualSourceAudit(unittest.TestCase):
    def test_original_six_completion_bytes_and_usage_are_verified(self):
        r=verify_stronger_local_originals()
        self.assertEqual(r["status"],"REAL_3B_LOCAL_OUTPUTS_VERIFIED_UNGRADED")
        self.assertEqual(r["source_actions_run_id"],40499625320)
        self.assertEqual(r["completed_pairs"],3)
        self.assertEqual(r["actual_local_model_calls"],6)
        self.assertEqual(r["v1_actual_prompt_tokens"],1100)
        self.assertEqual(r["v2_actual_prompt_tokens"],1247)
        self.assertEqual(r["v1_actual_completion_tokens"],212)
        self.assertEqual(r["v2_actual_completion_tokens"],182)
        self.assertEqual(r["v1_actual_total_tokens"],1312)
        self.assertEqual(r["v2_actual_total_tokens"],1429)
        self.assertEqual(r["v2_extra_total_tokens"],117)
        self.assertEqual(r["new_paid_provider_calls"],0)
        self.assertEqual(r["independent_reader_votes"],0)
        self.assertFalse(r["literary_gain_proven"])
        self.assertFalse(r["auto_activate_candidate"])
        self.assertEqual(r["candidate_stage"],"SHADOW")
        self.assertFalse(r["safe_to_conclude_global_v2_falsification"])
        self.assertEqual(len(r["case_pairs"]),3)

    def test_swapped_or_tampered_model_result_fails_sha_before_analysis(self):
        with TemporaryDirectory() as d:
            src=Path(d)/"copied"
            copytree(SOURCE,src)
            victim=src/"output_05_custody-without-fulfillment_v2.json"
            victim.write_bytes(victim.read_bytes()+b"corrupt")
            with self.assertRaisesRegex(ValueError,"ORIGINAL_MODEL_OUTPUT_SHA_MISMATCH"):
                verify_stronger_local_originals(archive=src)

    def test_forged_model_identity_and_literary_gain_flags_rejected(self):
        with TemporaryDirectory() as d:
            src=Path(d)/"copied"
            copytree(SOURCE,src)
            p=src/"SOURCE_MANIFEST.json"
            x=json.loads(p.read_text("utf8"))
            x["model_weights_sha256"]="0"*64
            p.write_text(json.dumps(x,ensure_ascii=False),encoding="utf8")
            with self.assertRaisesRegex(ValueError,"MANIFEST_SOURCE_INVALID"):
                verify_stronger_local_originals(archive=src)
            x=json.loads((SOURCE/"SOURCE_MANIFEST.json").read_text("utf8"))
            x["independently_proven_literary_gain"]=True
            p.write_text(json.dumps(x,ensure_ascii=False),encoding="utf8")
            with self.assertRaisesRegex(ValueError,"MANIFEST_SOURCE_INVALID"):
                verify_stronger_local_originals(archive=src)

    def test_transplanted_usage_cannot_change_source_metadata(self):
        with TemporaryDirectory() as d:
            src=Path(d)/"copied"
            copytree(SOURCE,src)
            p=src/"SOURCE_MANIFEST.json"
            x=json.loads(p.read_text("utf8"))
            x["outputs"][0]["total_tokens"]=999999
            p.write_text(json.dumps(x,ensure_ascii=False),encoding="utf8")
            with self.assertRaisesRegex(ValueError,"ORIGINAL_LOCAL_USAGE_MISMATCH"):
                verify_stronger_local_originals(archive=src)

    def test_unread_model_no_fake_grade_and_summary_is_single_write(self):
        with TemporaryDirectory() as d:
            target=Path(d)/"summary"
            with patch("urllib.request.urlopen",side_effect=AssertionError("NO HTTP")):
                out=save_verified_observation(output=target)
            self.assertEqual(out["actual_local_model_calls"],6)
            self.assertFalse(out["literary_gain_proven"])
            self.assertFalse(out["human_independent_blindness_proven"])
            self.assertEqual(out["new_model_calls_in_this_audit"],0)
            self.assertTrue((target/"STATUS.json").is_file())
            with self.assertRaises(FileExistsError):
                save_verified_observation(output=target)


if __name__=="__main__":
    unittest.main()
