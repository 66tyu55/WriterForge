"""Fail-closed admission test for one ranked modern novel (metadata only)."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/"catalog"/"modern"/"fanrenxiuxian.json"

class ModernWorkAdmissionTest(unittest.TestCase):
    def test_fanren_quality_does_not_imply_archived_or_trained(self):
        work=json.loads(FILE.read_text(encoding="utf-8"))
        self.assertEqual(work["work_id"],"fanrenxiuxian")
        self.assertEqual(work["status"],"quality_admitted_source_pending")
        self.assertEqual(work["ranking"]["category"],"海外传播榜")
        self.assertFalse(work["source"]["source_verified"])
        self.assertIsNone(work["source"]["source_binary_sha256"])
        self.assertFalse(work["source"]["stored_in_r2"])
        self.assertFalse(work["evaluation"]["literary_training_performed"])
        self.assertFalse(work["evaluation"]["global_50_work_assessment"])
