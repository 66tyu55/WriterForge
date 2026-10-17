"""No-network random3 reproducibility and old API preservation tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import unittest
from writerforge.reverse_random_chapters import chosen_chapters,selection_hash,SOURCE_SHA
from writerforge.reverse_later_window import later_chapter_diagnostic,LaterWindowError
from writerforge.reverse_real_training import first_chapter_windows
from writerforge.reverse_discovery_models import ROLE_MODELS

def chapter_text(chapter):
    return f"第{chapter}章 合成固定章节编号\n"+"".join(
        f"第{chapter}章的人物与第{k}个变化源相遇，因果逻辑为先观测再行动。\n"
        for k in range(70)
    )

class Random3Tests(unittest.TestCase):
    def test_fixed_random_without_cherry_picking(self):
        self.assertEqual(chosen_chapters(),(3,15,17))
        self.assertEqual(len(selection_hash()),64)
        self.assertNotIn(1,chosen_chapters())
        self.assertNotIn(2,chosen_chapters())
    def test_three_diverse_chapters_are_structurally_contiguous(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"synthetic.txt"
            src="".join(chapter_text(i) for i in range(1,19))
            p.write_text(src,encoding="utf-8")
            h=hashlib.sha256(src.encode()).hexdigest()
            for ch in chosen_chapters():
                plan,(a,b)=later_chapter_diagnostic(
                    p,"utf-8",expected_source_sha256=h,chapter=ch,sampled_diagnostic=True)
                self.assertTrue(plan["full_body_reconstructed"])
                self.assertEqual(plan["chapter"],ch)
                self.assertTrue(plan["sampled_diagnostic_only"])
                self.assertFalse(plan["semantic_boundary_verified"])
                self.assertNotEqual(a,b)
            with self.assertRaises(LaterWindowError):
                later_chapter_diagnostic(p,"utf-8",expected_source_sha256=h,chapter=15)
            with self.assertRaises(LaterWindowError):
                later_chapter_diagnostic(p,"utf-8",expected_source_sha256=h,chapter=25,sampled_diagnostic=True)
            old_plan,(first,second)=first_chapter_windows(p,"utf-8",h)
            self.assertEqual(old_plan["units"][0]["segment_sha256"],hashlib.sha256(first.encode()).hexdigest())
    def test_writer_and_critic_models_not_switched(self):
        self.assertEqual(ROLE_MODELS["planner"],"deepseek-v4-flash-0731")
        self.assertEqual(ROLE_MODELS["writer"],"glm-5.3")
        self.assertEqual(ROLE_MODELS["critic"],"deepseek-v4-flash-0731")
