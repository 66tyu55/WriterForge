"""No-model real chapter test: no external interpretations and no fake writing."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.run_v40_wf_native_reader_exam import EXAM, ReaderExamError, _load_package, run


class ExamReaderTests(unittest.TestCase):
    def test_pinned_original_chapter_packet_accepted(self):
        m, text, ch = _load_package(EXAM)
        self.assertEqual(m["source"]["original_chapter_number"], 7)
        self.assertEqual(ch.number, 1)  # exam slot, NOT original chapter
        self.assertGreater(len(ch.text), 5000)
        self.assertIn("借箸代籌", ch.heading)

    def test_mutated_packet_cannot_pass(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "manifest.json").write_bytes(
                (EXAM / "manifest.json").read_bytes())
            packet = (EXAM / "reader_packet.txt").read_bytes()
            (root / "reader_packet.txt").write_bytes(packet + "篡改".encode("utf-8"))
            with self.assertRaisesRegex(ReaderExamError, "BLOB_SHA1_MISMATCH"):
                _load_package(root)

    def test_actual_native_reader_never_fakes_semantic_reply(self):
        receipt = run()
        self.assertEqual(receipt["stages"]["R_IO_chapter_parsing"], "PASS")
        self.assertEqual(receipt["stages"]["R_IO_sqlite_recovery"], "PASS")
        self.assertTrue(receipt["stages"]["R_TRACE_independent_first_read_reactions"].startswith("BLOCKED"))
        self.assertTrue(receipt["stages"]["W_CLOSED_independent_original_prose"].startswith("BLOCKED"))
        self.assertEqual(receipt["model_calls"], 0)
        self.assertFalse(receipt["full_literary_understanding_proven"])
        self.assertFalse(receipt["examiner_answers_supplied"])
        self.assertEqual(receipt["source_body_characters"],
                         len(_load_package(EXAM)[2].text))
        self.assertGreater(receipt["sqlite_source_spans"], 0)


if __name__ == "__main__":
    unittest.main()
