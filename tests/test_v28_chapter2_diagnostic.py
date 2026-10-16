"""Later-window cursor regression; public-domain synthetic text only, zero API calls."""
from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from hashlib import sha256
from writerforge.reverse_later_window import later_chapter_diagnostic,LaterWindowError
from writerforge.reverse_real_training import first_chapter_windows,raw_hash
from writerforge.reverse_cloud_ab import CloudABTrial,BASE_TASK


def fake_chapter(chapter):
    return f"第{chapter}章 合成资料标题\n"+ "".join(
        f"人物在第{chapter}段旧林路口遇到第{idx}个障碍，先观察再作出改变方向的决定。\n"
        for idx in range(75))


class LaterWindowTests(unittest.TestCase):
    def make_fixture(self, *, headings=(1,2,3)):
        t=TemporaryDirectory()
        f=Path(t.name)/"novel.txt"
        source="".join(fake_chapter(i) for i in headings)
        f.write_text(source,encoding="utf-8")
        return t,f,sha256(source.encode("utf-8")).hexdigest()

    def test_chapter_two_contiguous_without_touching_chapter_one(self):
        t,f,sha=self.make_fixture()
        try:
            plan,(left,right)=later_chapter_diagnostic(
                f,"utf-8",expected_source_sha256=sha,chapter=2)
            first_plan,(old_first,old_second)=first_chapter_windows(f,"utf-8",sha)
            self.assertEqual(plan["chapter"],2)
            self.assertEqual(plan["windows"][0]["sha256"],raw_hash(left))
            self.assertEqual(plan["windows"][1]["sha256"],raw_hash(right))
            self.assertEqual(plan["windows"][0]["end"],plan["windows"][1]["start"])
            self.assertTrue(plan["full_body_reconstructed"])
            self.assertTrue(plan["diagnostic_only_no_mastery_progress"])
            self.assertFalse(plan["semantic_boundary_verified"])
            self.assertEqual(plan["first_window_literary_gate"],"NOT_PASSED")
            self.assertEqual(plan["next_curriculum_window"],"LOCKED")
            self.assertNotEqual(left,old_first)
            self.assertNotEqual(raw_hash(left),raw_hash(old_first))
            self.assertEqual(first_plan["units"][0]["segment_sha256"],raw_hash(old_first))
        finally:t.cleanup()

    def test_missing_heading_and_skipped_chapter_fail_closed(self):
        for headings in [(1,3,4),(1,2,4),(1,1,2,3)]:
            with self.subTest(headings=headings):
                t,f,sha=self.make_fixture(headings=headings)
                try:
                    with self.assertRaises(LaterWindowError):
                        later_chapter_diagnostic(f,"utf-8",
                                                 expected_source_sha256=sha,chapter=2)
                finally:t.cleanup()

    def test_no_reordering_or_skip_ahead_without_gate(self):
        t,f,sha=self.make_fixture()
        try:
            with self.assertRaises(LaterWindowError):
                later_chapter_diagnostic(f,"utf-8",
                                         expected_source_sha256=sha,chapter=4)
            with self.assertRaises(LaterWindowError):
                later_chapter_diagnostic(f,"utf-8",
                                         expected_source_sha256="invalid",chapter=2)
        finally:t.cleanup()

    def test_v6_changes_source_only_not_writer_model_or_original_task(self):
        from scripts.run_wudong_chapter2_diagnostic_v6 import (
            TRANSFER_TASK as new_task, SOURCE_SHA as new_sha,
            PREFIX as new_prefix,
        )
        from scripts.run_wudong_transfer_baseline30_v5 import (
            TRANSFER_TASK as prior_task,SOURCE_SHA as prior_sha,
            PREFIX as prior_prefix,
        )
        from writerforge.reverse_discovery_models import ROLE_MODELS
        self.assertEqual(new_task,prior_task)
        self.assertEqual(new_sha,prior_sha)
        self.assertNotEqual(new_prefix,prior_prefix)
        self.assertEqual(ROLE_MODELS["writer"],"glm-5.3")
        self.assertEqual(ROLE_MODELS["critic"],"deepseek-v4-flash-0731")

    def test_existing_public_signatures_still_work(self):
        import inspect
        from writerforge.reverse_cloud_ab import CloudABTrial
        signature=inspect.signature(CloudABTrial.run)
        self.assertIn("first",signature.parameters)
        self.assertIn("second",signature.parameters)
        self.assertIn("source_sha",signature.parameters)
        self.assertIn("window_hash",signature.parameters)
        self.assertIn("writing_task",signature.parameters)
        self.assertEqual(BASE_TASK[:4],"创作全新")

if __name__=="__main__":
    unittest.main()
