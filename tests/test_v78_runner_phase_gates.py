"""V78 safety lint for all one-shot preflight/model/exam Railway entrypoints.

AST only: it does not import/run those scripts or contact DeepSeek/R2.
These guardrails preserve phase separation even when a later editor revises
the code without re-executing the complete integration workflow.
"""
from __future__ import annotations

from pathlib import Path
import ast
import unittest


REPO=Path(__file__).resolve().parents[1]
B01="wf_railway_v78_b01_one_book.py"
EXAM="wf_railway_v78_reader_only_exam.py"
PREFLIGHT="wf_railway_v78_prefix_preflight.py"


class V78EntrypointSafetyTests(unittest.TestCase):
    def content(self,name):
        raw=(REPO/name).read_text(encoding="utf8")
        ast.parse(raw)
        return raw

    def test_all_v78_entrypoints_syntax_compiles_offline(self):
        for name in (
            "wf_railway_v78_frozen_charset_review.py",
            PREFLIGHT,B01,EXAM,
        ):
            with self.subTest(entry=name):
                self.assertGreater(len(self.content(name)),150)

    def test_paid_runner_authenticates_writer_before_source_download(self):
        text=self.content(B01)
        self.assertLess(text.index("journal.require_writer_ready()"),
                        text.index("download_one_verified("))
        self.assertLess(text.index("journal.require_writer_ready()"),
                        text.index("new_wf_learn_model("))
        self.assertIn("max_calls=4",text)
        self.assertIn("max_reserved_output_tokens=2000",text)
        self.assertIn("WF_B01_THREE_UNITS_PASS_A_B_R2_LOCKED",text)
        self.assertIn("complete_chapter_claimed",text)
        self.assertNotIn("WF_LEARN_UPLOAD_TOKEN",text)

    def test_examiner_removes_paid_and_writer_credentials_before_import(self):
        text=self.content(EXAM)
        self.assertLess(text.index('os.environ.pop(secret,None)'),
                        text.index('from writerforge.r2_learn_journal'))
        self.assertIn("read_only=True",text)
        self.assertIn("independently_recheck_r2_events",text)
        self.assertIn(' "claims_complete_chapter":False',text)

    def test_real_preflight_has_no_paid_model_or_write_token(self):
        text=self.content(PREFLIGHT)
        self.assertIn('os.environ.pop(secret,None)',text)
        self.assertIn("review_first_chapter_windows(",text)
        self.assertNotIn("new_wf_learn_model(",text)
        self.assertNotIn("journal.append_first_read",text)
        self.assertIn("real_deepseek_model_calls",text)

if __name__=="__main__":
    unittest.main()
