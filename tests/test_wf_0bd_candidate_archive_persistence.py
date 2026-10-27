"""0.BD: resume ungraded cognitive SHADOW after original host is gone.

This suite uses ONLY source-controlled immutable root and saved candidate.
No original 0.AY artifact, provider model, novel data, keys, R2 or Canon.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import unittest

from writerforge.evolution import PortableHabitCandidatePool

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / ".agents/skills/observe-before-next-choice/capsule.json"
SOURCE_SHA = "42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d"
CANDIDATE_SHA = "0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10"
MANIFEST_SHA = "6bb2c9507edbe8be95e79bb098dca210f87da085e04c7bb2a2650a683b01956f"
DIRECTORY = ROOT / "experiments" / "wf_0bd_portable_habit_snapshots" / CANDIDATE_SHA
VERIFIER_KEY = b"wf0bd-synthetic-local-only-reviewer-verifier"
NO_REAL_HELDOUT_PIN = sha256(
    b"0bd-NO-INDEPENDENT-HELDOUT-OR-LITERARY-EVALUATION").hexdigest()


def sha(b):
    return sha256(b).hexdigest()


class WF0BDPersistentCandidateAfterHostExit(unittest.TestCase):
    def test_historical_root_and_chatgpt_candidate_are_distinct_and_sha_exact(self):
        root=ORIGINAL.read_bytes()
        body=(DIRECTORY/"capsule.json").read_bytes()
        self.assertEqual(sha(root),SOURCE_SHA)
        self.assertEqual(sha(body),CANDIDATE_SHA)
        before=json.loads(root)
        after=json.loads(body)
        self.assertEqual(before["lifecycle"],after["lifecycle"])
        self.assertEqual(after["lifecycle"],"SHADOW")
        self.assertEqual(after["revision"],before["revision"]+1)
        self.assertEqual(after["authority"],before["authority"])
        self.assertEqual(after["transfer"],before["transfer"])
        self.assertEqual(after["provenance"],before["provenance"])
        self.assertEqual(after["stopping"],before["stopping"])
        self.assertFalse(after["authority"]["auto_skill_promotion"])
        self.assertFalse(after["authority"]["auto_canon_writes"])

    def test_manifest_can_rehydrate_without_first_host_model_or_old_artifacts(self):
        raw=(DIRECTORY/"portable_manifest.json").read_bytes()
        self.assertEqual(sha(raw),MANIFEST_SHA)
        manifest=json.loads(raw)
        pool=PortableHabitCandidatePool.from_manifest(
            manifest,pinned_roots={SOURCE_SHA:ORIGINAL.read_bytes()},
            reviewer_verifier_key=VERIFIER_KEY,
            frozen_heldout_sha256=NO_REAL_HELDOUT_PIN,
            expected_manifest_sha256=MANIFEST_SHA)
        self.assertEqual(pool.status(CANDIDATE_SHA),"SHADOW")
        restored=pool.export_candidate(CANDIDATE_SHA)
        self.assertEqual(restored["capsule_utf8"].encode("utf8"),
                         (DIRECTORY/"capsule.json").read_bytes())
        self.assertEqual(restored["proposer_skill"],"chatgpt-interactive")
        self.assertEqual(restored["parent_sha256"],SOURCE_SHA)
        self.assertFalse(restored["auto_execute"])
        self.assertFalse(restored["auto_promote"])
        self.assertFalse(restored["cross_host_quality_proven"])
        self.assertEqual(manifest["competition_evidence"],[])
        self.assertEqual(manifest["quarantine_attestations"],[])
        self.assertFalse(manifest["auto_execution_or_promotion"])

    def test_old_root_is_not_promoted_by_existence_of_new_candidate(self):
        original=json.loads(ORIGINAL.read_bytes())
        new=json.loads((DIRECTORY/"capsule.json").read_bytes())
        self.assertEqual(original["revision"],1)
        self.assertEqual(original["lifecycle"],"SHADOW")
        self.assertEqual(new["revision"],2)
        self.assertEqual(new["lifecycle"],"SHADOW")
        self.assertFalse(new["transfer"]["cross_host_quality_proven"])
        self.assertEqual(new["transfer"]["tested_host_count"],0)
        self.assertFalse(new["provenance"]["independently_graded"])

    def test_tampered_manifest_or_missing_external_pin_cannot_reload(self):
        manifest=json.loads((DIRECTORY/"portable_manifest.json").read_bytes())
        params=dict(pinned_roots={SOURCE_SHA:ORIGINAL.read_bytes()},
                    reviewer_verifier_key=VERIFIER_KEY,
                    frozen_heldout_sha256=NO_REAL_HELDOUT_PIN)
        with self.assertRaises(ValueError):
            PortableHabitCandidatePool.from_manifest(manifest,**params)
        manifest["candidates"][0]["capsule_utf8"] += " "
        with self.assertRaises(ValueError):
            PortableHabitCandidatePool.from_manifest(
                manifest,expected_manifest_sha256=MANIFEST_SHA,**params)


if __name__ == "__main__":
    unittest.main()
