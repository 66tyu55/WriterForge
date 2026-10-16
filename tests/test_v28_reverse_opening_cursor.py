"""V28 story beginning is strictly from chapter 1, not random source search."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge.reverse_source_cursor import opening_chapter_plan, CursorError, digest
from writerforge.reverse_craft import ReverseCraftCoordinator, ReverseCraftError, _hash

SYNTHETIC_LINE = "他走进雨夜，想起仍在等候的承诺。于是继续向前。\n"


def make_text(*, start=1, missing=None):
    one = SYNTHETIC_LINE * 42
    two = "另一个测试章节，场景承接仅供工程验证。\n" * 10
    titles = [f"第{start}章 起始\n", f"第{start+1}章 承接\n", f"第{start+2}章 后文\n"]
    if missing == "third":
        titles = titles[:2]
    return titles[0]+one+titles[1]+two+(titles[2] if len(titles)>2 else "")


class SourceOpeningTests(unittest.TestCase):
    def plan(self,text):
        with TemporaryDirectory() as t:
            file=Path(t)/"original.txt"
            file.write_text(text,encoding="utf-8")
            return opening_chapter_plan(file,"utf-8",
                expected_source_sha256=digest(text),min_unit_chars=200)

    def test_two_contiguous_windows_from_chapter_one(self):
        content=make_text()
        result=self.plan(content)
        self.assertEqual(result["stage"],"opening_layout_candidate_only")
        a,b=result["units"]
        self.assertEqual(a["start"],0)
        self.assertEqual(a["end"],b["start"])
        self.assertEqual(b["end"],result["chapter_body_chars"])
        self.assertEqual(b["prior_unit_sha256"],a["segment_sha256"])
        self.assertEqual([x["number"] for x in result["first_three_chapter_headers"]],[1,2,3])
        self.assertFalse(result["semantic_scene_boundary_verified"])
        self.assertFalse(result["writer_model_called"])
        self.assertTrue(result["coverage_exact"])

    def test_starting_in_middle_or_missing_future_header_refused(self):
        with self.assertRaisesRegex(CursorError,"expected 1, got 2"):
            self.plan(make_text(start=2))
        with self.assertRaisesRegex(CursorError,"first three"):
            self.plan(make_text(missing="third"))

    def test_no_safe_boundary_does_not_randomly_cut_story(self):
        src=("测试文本仅供演练，不可充当真实文学阅读，" * 30)
        data="第一章 起始\n"+src+"\n第二章 继续\n第三章 收尾\n"
        with self.assertRaisesRegex(CursorError,"no safe paragraph boundary"):
            self.plan(data)

    def test_training_unit_one_must_not_jump_chapters(self):
        with TemporaryDirectory() as t:
            obj=ReverseCraftCoordinator(Path(t)/"v28.sqlite3","start",
                                        create=True)
            try:
                with self.assertRaisesRegex(ReverseCraftError,"begin at chapter 1"):
                    obj.open_unit(2,1,_hash("anchor"),_hash("context"))
                with self.assertRaisesRegex(ReverseCraftError,"begin at chapter 1"):
                    obj.open_unit(1,2,_hash("anchor"),_hash("context"))
                self.assertEqual(obj.open_unit(1,1,_hash("anchor"),_hash("context")),1)
            finally:obj.close()


if __name__=="__main__":
    unittest.main()
