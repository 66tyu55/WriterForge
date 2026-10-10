"""V24 Chinese original catalog and literary-stage truthfulness tests."""
from __future__ import annotations
from hashlib import sha1
from io import BytesIO
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.source_study import (
    StudyError, parse_original, OriginalStudy, Chapter, _unitize, _structural_analysis,
)
from writerforge.classics_catalog import (
    CATALOG, ClassicBook, verify_edition, download_book,
    catalog_progress_local, MIN_WORKS_FOR_CROSS_CORPUS_REVIEW,
)
from writerforge.r2_storage import R2Config, R2StudyVault


def synthetic_book(key="unit", chapter_count=70, prologue=False) -> str:
    parts = []
    if prologue:
        parts.append("楔子　張天師祈禳瘟疫　洪太尉誤走妖魔\n\n"
                     "　　" + "洪太尉走入古殿，有人苦勸他不可開門。" * 12)
    for n in range(1,chapter_count+1):
        # The real editions use mixed Chinese numerals: 第七十回 vs 第一二零回.
        numeral = str(n)
        parts.append(
            f"第{numeral}回　古典小说测试第{n}回\n\n"
            "　　石猴聽到山外聲響，道：「這裏到底藏著甚麼？」\n"
            "原來外頭來了一位老者，身披青衫，慢慢走進洞來。"
            "　　眾人心中暗自思量，卻不肯將話說破。\n"
            "他又問道：「當真要走麼？」老者只把袖子一拂，便不再作聲。"
            "門外竹影搖動，後生各自思量，天色漸晚，卻無一人先開口。"
            "月光照進院中，老人慢慢轉身，這才說出多年隱藏的往事。"
        )
    return "\n\n".join(parts)


class CatalogAndStageTests(unittest.TestCase):
    def test_verified_catalog_never_links_translations(self):
        self.assertEqual(set(CATALOG),{"honglou","shuihu"})
        self.assertEqual(CATALOG["honglou"].expected_chapters,120)
        self.assertEqual(CATALOG["shuihu"].expected_chapters,70)
        self.assertTrue(CATALOG["shuihu"].include_prologue)
        self.assertEqual(MIN_WORKS_FOR_CROSS_CORPUS_REVIEW,50)
        self.assertTrue(all("gutenberg.org/ebooks/" in b.source_page for b in CATALOG.values()))
        self.assertTrue(all(b.source_filename.endswith("-0.txt") for b in CATALOG.values()))

    def test_parser_accepts_120_chapter_honglou_original_numerals(self):
        a=synthetic_book(chapter_count=120)
        # Exercise Chinese chapter numbering used near the end.
        a=a.replace("第119回","第一一九回").replace("第120回","第一二零回")
        chapters=parse_original(a,require_hundred=False,expected_count=120)
        self.assertEqual(len(chapters),120)
        self.assertEqual(chapters[-1].number,120)
        with self.assertRaisesRegex(StudyError,"expected 119"):
            parse_original(a,require_hundred=False,expected_count=119)

    def test_prologue_preserved_and_not_counted_as_a_separate_book(self):
        text=synthetic_book(chapter_count=70,prologue=True)
        chapters=parse_original(text,require_hundred=False,expected_count=70,include_prologue=True)
        self.assertEqual([c.number for c in chapters[:3]],[0,1,2])
        self.assertEqual(len(chapters),71)
        self.assertIn("張天師",chapters[0].heading)
        with self.assertRaisesRegex(StudyError,"楔子"):
            parse_original(synthetic_book(chapter_count=70),require_hundred=False,
                           expected_count=70,include_prologue=True)

    def test_wrapped_lines_are_not_false_paragraphs(self):
        # A Gutenberg physical line wrap should remain within one paragraph;
        # a Chinese ideographic indentation marks a true new paragraph.
        ch=Chapter(1,"opening",
            "　　太尉走進古殿，這裏四下\n"
            "無人；但聽有哭聲。\n"
            "　　眾人忽見那燈火\n"
            "搖晃，只好退去。")
        raw=list(_unitize(ch))
        wrapped=list(_unitize(ch,wrapped_lines=True))
        self.assertGreater(len({p for p,s,x in raw}),len({p for p,s,x in wrapped}))
        self.assertEqual(len({p for p,s,x in wrapped}),2)
        self.assertTrue(any("四下無人" in x for _,_,x in wrapped))
        self.assertTrue(any("燈火搖晃" in x for _,_,x in wrapped))

    def test_pin_sha_prevents_silent_upstream_translation_or_changes(self):
        data=synthetic_book(chapter_count=70).encode("utf-8")
        sha=sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
        book=ClassicBook("test","古籍","test-original",9,"test.txt",sha,70,False,("dialogue",))
        self.assertEqual(len(verify_edition(book,data)),len(data.decode()))
        with self.assertRaisesRegex(StudyError,"source content changed"):
            verify_edition(book,b"ENGLISH TRANSLATION")
        class Remote(BytesIO):
            def __enter__(self):return self
            def __exit__(self,*a):self.close();return False
        with TemporaryDirectory() as d:
            with patch("writerforge.classics_catalog.urllib.request.urlopen",
                       return_value=Remote(data)):
                out=download_book(book,Path(d)/"book.txt")
            self.assertEqual(out["expected_chapters"],70)
            self.assertEqual(Path(out["source_path"]).read_bytes(),data)

    def test_real_db_studies_70_plus_prologue_with_resume(self):
        book_text=synthetic_book(chapter_count=70,prologue=True)
        with TemporaryDirectory() as d:
            db=WriterForgeDB(Path(d)/"study.sqlite3")
            rt=RuntimeEngine()
            rt.enter_learn()
            src=OriginalStudy(db,rt)
            result=src.ingest(book_text,work_id="shuihu-test",
                title="水滸傳",source_uri="test://shuihu",
                require_hundred=False,expected_count=70,include_prologue=True,
                wrapped_lines=True)
            self.assertEqual(result["studied_chapters"],71)
            self.assertTrue(result["structure_complete"])
            self.assertGreater(result["studied_units"],100)
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM studied_chapters WHERE chapter=0"
            ).fetchone()[0],1)
            again=src.ingest(book_text,work_id="shuihu-test",
                title="水滸傳",source_uri="test://shuihu",
                require_hundred=False,expected_count=70,include_prologue=True,
                wrapped_lines=True)
            self.assertEqual(again["newly_studied"],0)
            progress=catalog_progress_local(db)
            self.assertEqual(progress["complete_distinct_works"],1)
            self.assertEqual(progress["remaining"],49)
            self.assertFalse(progress["cross_corpus_review_eligible"])
            self.assertFalse(progress["global_assessment_performed"])
            db.close()


if __name__=="__main__":
    unittest.main()
