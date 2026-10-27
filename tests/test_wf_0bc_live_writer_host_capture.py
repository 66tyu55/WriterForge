"""WF 0.BC opt-in in REAL autonomous writer host call site; zero new calls."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.writing_assist import InvisibleWritingAssist, AutonomousWriting
from test_v26_invisible_writer import make_db, PLAN, BODY


class WF0BCLiveHostCaptureTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.file = Path(self.folder.name) / "story.db"
        snapshot = make_db(self.file)
        self.db = WriterForgeDB(self.file)
        self.rt = RuntimeEngine()
        self.rt.enter_write(snapshot)
        self.assist = InvisibleWritingAssist(
            self.db, self.rt, "novel", "s1", "两个故友为了少年人的选择发生冲突",
            model="synthetic-host", api_base="http://127.0.0.1:1234/v1")

    def tearDown(self):
        self.db.close()
        self.folder.cleanup()

    def run_once(self, callback):
        return AutonomousWriting(self.assist).run(
            outline="年轻镖师带领少年人穿越险峻山道，在旧友与陌生人的承诺中作出艰难选择。",
            chapter_goals=["在险峻山路中选择是否相信陌生同伴，并承受可能发生的后果"],
            output_dir=Path(self.folder.name) / "writing",
            host_nutrient_observer=callback)

    def test_actual_autonomous_writer_exposes_sha_only_two_model_events(self):
        receipts = []
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=[PLAN, BODY]) as model:
            result = self.run_once(receipts.append)
        self.assertEqual(model.call_count, 2)
        self.assertEqual(len(receipts), 2)
        self.assertEqual(result["host_nutrient_application_events"], 2)
        self.assertEqual(result["host_nutrient_observer_failures"], 0)
        self.assertEqual(
            [r["application_response_sha256"] for r in receipts],
            [sha256(PLAN.encode()).hexdigest(),
             sha256(BODY.encode()).hexdigest()])
        for event in receipts:
            self.assertEqual(event["format"],
                             "wf.first-host.application-payload-only.v1")
            self.assertFalse(event["provider_wire_verified"])
            self.assertFalse(event["literary_improvement_proven"])
            self.assertTrue(event["source_is_untrusted_application_payload"])
            self.assertEqual(event["new_host_requests_for_observation"], 0)
            self.assertNotIn("prose", event)
            self.assertNotIn("raw_prompt", event)
            self.assertNotIn(BODY, json.dumps(event, ensure_ascii=False))
        self.assertTrue(result["all_generated_prose_requires_author_review"])
        self.assertEqual(
            Path(result["chapters"][0]["candidate"]).read_text("utf8"), BODY)

    def test_failed_opt_in_observer_does_not_retry_model_or_delete_author_text(self):
        seen = []
        def fail(receipt):
            seen.append(receipt["application_response_sha256"])
            raise RuntimeError("synthetic-local-observer-failure")
        with patch("writerforge.writing_assist.local_chat_completion",
                   side_effect=[PLAN, BODY]) as model:
            result = self.run_once(fail)
        self.assertEqual(model.call_count, 2)
        self.assertEqual(len(seen), 2)
        self.assertEqual(result["host_nutrient_application_events"], 2)
        self.assertEqual(result["host_nutrient_observer_failures"], 2)
        self.assertEqual(
            Path(result["chapters"][0]["candidate"]).read_text("utf8"), BODY)
        self.assertEqual(result["host_nutrient_candidates_promoted"], 0)

    def test_invalid_observer_is_rejected_before_provider_or_job_directory(self):
        with patch("writerforge.writing_assist.local_chat_completion") as model:
            with self.assertRaises(ValueError):
                self.run_once("not-a-callback")
        model.assert_not_called()
        self.assertFalse((Path(self.folder.name)/"writing").exists())


if __name__ == "__main__":
    unittest.main()
