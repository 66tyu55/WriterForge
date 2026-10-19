"""V82 phase-safety regression, pure AST/source (no R2/model traffic)."""
from __future__ import annotations
from pathlib import Path
import ast
import unittest

ROOT=Path(__file__).resolve().parents[1]


class V82TrainingContractTests(unittest.TestCase):
    def read(self,name):
        source=(ROOT/name).read_text(encoding="utf-8")
        ast.parse(source)
        return source

    def test_new_paid_runner_only_11_to_15_and_150k(self):
        code=self.read("wf_railway_v82_ch11_to15.py")
        for item in (
            "START_CHAPTER=11",
            "STOP_CHAPTER=15",
            "MAX_TOTAL_TOKENS=150000",
            "max_total_tokens=MAX_TOTAL_TOKENS",
            'batch_id="WF-V82-CH11-15-150K"',
            "chapters[START_CHAPTER-1:STOP_CHAPTER]",
            "WF_V82_CH11_TO_15_R2_BATCH_COMPLETED",
        ):
            self.assertIn(item,code)
        self.assertLess(
            code.index("journal.require_writer_ready()"),
            code.index("new_wf_learn_model(budget=budget)"))
        self.assertLess(
            code.index("projected_total_calls>budget.max_calls"),
            code.index("for chap in chapters[START_CHAPTER-1:STOP_CHAPTER]:"))
        self.assertEqual(code.count("batch.complete(chapter=chap"),1)

    def test_restores_actual_v81_not_chapter1_or_older_batch(self):
        code=self.read("wf_railway_v82_ch11_to15.py")
        self.assertIn(
          'PREV_BATCH="e28490de3f0b17875ed23418726a8b8692b3029c1501b30da314080f4edb0901"',
          code)
        self.assertIn(
          'PREV_JOURNAL="61a52125708a180b3305e28721d6e1797c0ab619df18a1bac7822988707a9c33"',
          code)
        self.assertIn(
          'PREV_EXPERIENCE="feee04808c6b14f84c16989d98b031937a897395f3d008c43e17b3449f9077e3"',
          code)
        self.assertIn('old.get("last_completed_chapter")!=10',code)
        self.assertIn('experience.get("chapter")!=10',code)
        self.assertIn("prior_ten_chapters_not_retrained",code)
        self.assertNotIn("WF_LEARN_UPLOAD_TOKEN",code)

    def test_independent_exam_removes_provider_and_writer_secrets(self):
        code=self.read("wf_railway_v82_reader_only_exam.py")
        self.assertIn('"DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN"',code)
        self.assertIn("os.environ.pop(secret,None)",code)
        self.assertLess(
            code.index("os.environ.pop(secret,None)"),
            code.index("from writerforge.v82_independent_exam import"))
        self.assertIn("read_only=True",code)
        self.assertIn("PENDING_REAL_V82_BATCH_SHA",code)
        self.assertIn("PENDING_REAL_V82_JOURNAL_SHA",code)
        self.assertNotIn("new_wf_learn_model",code)

if __name__=="__main__":
    unittest.main()
