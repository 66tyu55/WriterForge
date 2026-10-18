"""Offline V67 tests: no private R2 token, external network or GitHub Actions."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from writerforge.r2_literary_exam import (
    LiteraryExamError, run_literary_retrieval_exam,
)


class _MemorySource:
    def __init__(self, data: str):
        self.raw = data.encode("utf-8")

    def pinned_laocan_original(self):
        # Transport's real implementation verifies SHA256; this fake only
        # tests the question parser and chapter/answer logic.
        return self.raw, {
            "source_sha256": "synthetic-test-only",
            "source_size_bytes": len(self.raw),
            "source_full_bytes_verified": False,
            "stored_to_disk": False,
        }


def _original(*, occurrence_chapter: int | None = 9):
    return "".join(
        f"第{i}回 測試章節{i}\n"
        + ("高山流水，老殘走到村口。" if i == occurrence_chapter
           else "高山流水，眾人走到村口。")
        + "\n"
        for i in range(1, 21)
    )


def _question(path: Path, *, term: str = "老殘"):
    path.write_text(json.dumps({
        "format": "writerforge.independent-literary-retrieval-exam.v1",
        "exam_id": "FAKE-OFFLINE-EXAM",
        "question": (f"請自己檢索《老殘遊記》的原著全部20回：“{term}”"
                     "第一次出現在哪一回？給出原文片段和章節位置，"
                     "不要猜測，也不要由考官提供預期答案。"),
        "model_assistance_allowed": False,
        "evaluator_supplies_expected_answer": False,
    }, ensure_ascii=False), encoding="utf-8")


class WFSourceExamTests(unittest.TestCase):
    def test_first_hit_is_grounded_after_scanning_all_twenty(self):
        with TemporaryDirectory() as d:
            q = Path(d) / "question.json"
            _question(q)
            result = run_literary_retrieval_exam(
                _MemorySource(_original()), question_path=q)
        self.assertEqual(result["status"], "PINNED_ORIGINAL_MATCH_VERIFIED")
        self.assertEqual(result["chapters_actually_scanned"], 20)
        self.assertEqual(result["first_occurrence"]["chapter"], 9)
        self.assertIn("老殘", result["first_occurrence"]["evidence_excerpt"])
        self.assertTrue(result["no_model_called"])
        self.assertFalse(result["semantic_literary_understanding_proven"])
        self.assertTrue(result["no_source_saved_to_disk"])

    def test_absent_literal_never_hallucinates(self):
        with TemporaryDirectory() as d:
            q = Path(d) / "question.json"
            _question(q, term="深海仙府")
            result = run_literary_retrieval_exam(
                _MemorySource(_original()), question_path=q)
        self.assertEqual(result["status"], "PINNED_ORIGINAL_NO_MATCH")
        self.assertIsNone(result["first_occurrence"])
        self.assertEqual(result["chapters_actually_scanned"], 20)
        self.assertEqual(result["total_literal_occurrences"], 0)

    def test_malformed_exam_refused(self):
        with TemporaryDirectory() as d:
            q = Path(d) / "question.json"
            _question(q)
            doc = json.loads(q.read_text(encoding="utf-8"))
            doc["model_assistance_allowed"] = True
            q.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(LiteraryExamError):
                run_literary_retrieval_exam(_MemorySource(_original()), question_path=q)

    def test_missing_chapter_refused_not_falsely_complete(self):
        with TemporaryDirectory() as d:
            q = Path(d) / "question.json"
            _question(q)
            with self.assertRaises(ValueError):
                run_literary_retrieval_exam(_MemorySource(
                    _original().replace("第7回 ", "第8回 ")), question_path=q)


if __name__ == "__main__":
    unittest.main()
