"""Strict volume grammar regression on fictional synthetic text only."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge.modern_volumes import volume_chapters
from writerforge.source_study import StudyError


class VolumeGrammarTests(unittest.TestCase):
    def run_sample(self,text,scheme):
        with TemporaryDirectory() as t:
            file=Path(t)/"synthetic.txt"
            file.write_text("示例小说\n" + text,encoding="utf-8")
            return list(volume_chapters(file,"utf-8",scheme=scheme))

    def test_real_style_standalone_volumes_reset_chapters(self):
        body=("这是纯合成测试段落，不是原著。"*12)+"\n"
        text=("第一卷 起始\n第一章 开始\n"+body+"第二章 变化\n"+body+
              "第二卷 新卷\n第一章 新起点\n"+body+"第二章 新事件\n"+body)
        chapters=self.run_sample(text,"volume_reset")
        self.assertEqual([x.number for x in chapters],[1,2,3,4])
        self.assertTrue(chapters[2].heading.startswith("第一章"))
        self.assertNotIn("第二卷 新卷",chapters[1].text)

    def test_standalone_volumes_reject_missing_chapters(self):
        body=("这是合成数据，用来测试错误拒绝。"*13)+"\n"
        text="第一卷 卷一\n第一章 一\n"+body+"第三章 三\n"+body
        with self.assertRaisesRegex(StudyError,"expected 2, got 3"):
            self.run_sample(text,"volume_reset")

    def test_volume_coupled_global_chapter_numbers(self):
        body=("这是另一种合成数据片段，不是任何小说。"*13)+"\n"
        text=("第一卷 天地 第一章 起始\n"+body+
              "第一卷 天地 第二章 转折\n"+body+
              "第二卷 江河 第三章 新篇\n"+body)
        chapters=self.run_sample(text,"volume_prefix_global")
        self.assertEqual([x.number for x in chapters],[1,2,3])

    def test_coupled_global_gap_rejected(self):
        body=("这是合成数据片段。"*19)+"\n"
        text="第一卷 名称 第一章 起\n"+body+"第一卷 名称 第三章 错\n"+body
        with self.assertRaisesRegex(StudyError,"expected 2, got 3"):
            self.run_sample(text,"volume_prefix_global")

    def test_invalid_scheme_rejected(self):
        with TemporaryDirectory() as t:
            with self.assertRaises(StudyError):
                list(volume_chapters(Path(t)/"nothing","utf-8",scheme="permissive"))


if __name__=="__main__":
    unittest.main()
