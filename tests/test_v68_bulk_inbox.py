"""Synthetic V68 stress and correctness tests. No real novels, R2 or models."""
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from writerforge.bulk_inbox import (
    INBOX, BulkCatalog, BulkCorpusError, local_inventory, parse_key,
)

PREFIX=INBOX+"20261018/"

class BulkIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.catalog=BulkCatalog(self.root/"catalog.sqlite3")
    def tearDown(self):
        self.catalog.close()
        self.temp.cleanup()

    def record(self,name="01、玄幻/a.txt",size=120,etag=None):
        return {"key":PREFIX+name,"size":size,"etag":etag}

    def test_category_preservation_and_monotonic_virtual_numbering(self):
        self.assertEqual(parse_key(PREFIX+"01、玄幻/x.txt")["category"],"玄幻")
        self.assertEqual(parse_key(PREFIX+"02、仙侠/x.txt")["category"],"仙侠")
        self.assertEqual(parse_key(PREFIX+"07、历史/唐z.txt")["raw_title"],"唐z")
        self.catalog.register([self.record("01、玄幻/c.txt"),
                               self.record("01、玄幻/a.txt")])
        self.catalog.register([self.record("01、玄幻/b.txt")])
        self.assertEqual([(r["display_no"],r["filename"])
           for r in self.catalog.rows("玄幻")],
           [(1,"a.txt"),(2,"c.txt"),(3,"b.txt")])
        self.assertEqual(self.catalog.register(
            [self.record("01、玄幻/c.txt")])["added"],0)

    def test_append_only_refuses_remote_replacement(self):
        self.catalog.register([self.record(etag="v1")])
        with self.assertRaisesRegex(BulkCorpusError,"MUTATED"):
            self.catalog.register([self.record(etag="v2")])
        self.assertEqual(self.catalog.summary()["objects"],1)

    def test_unsupported_and_malicious_paths_never_count_as_studied(self):
        for key in ("evil/foo",INBOX+"20261018/玄幻/../x.txt",
                    INBOX+"20261018/x.txt",INBOX+"20261018/玄幻/x\x00.txt"):
            with self.assertRaises(BulkCorpusError):
                parse_key(key)
        self.assertEqual(parse_key(PREFIX+"01、玄幻/abc.rar")["status"],
                         "ARCHIVE_NEEDS_LOCAL_EXTRACTION")
        self.assertEqual(parse_key(PREFIX+"01、玄幻/program.exe")["status"],
                         "UNSUPPORTED_REVIEW")
        self.assertEqual(self.catalog.summary()["distinct_indexed_books"],0)

    def test_sql_index_real_plaintext_source_position_and_read_only_query(self):
        p=self.root/"original.txt"
        p.write_text("第1章 风雨\n雨声敲打窗棂。少年突然停住脚步！\n"
                     "第2章 旧城\n天空暗了下来；门外有脚步声。\n",encoding="utf8")
        key=PREFIX+"01、玄幻/缩写作者.txt"
        self.catalog.register([{"key":key,"size":p.stat().st_size}])
        out=self.catalog.index_text_file(key,p,self.root/"shards")
        self.assertEqual(out["chapters_detected"],2)
        self.assertEqual(self.catalog.ready_count(),1)
        search=self.catalog.search(category="玄幻",book_id=out["book_id"],
                                   text="雨声敲打",shard_dir=self.root/"shards")
        self.assertEqual(search["matches"][0]["chapter"],1)
        self.assertEqual(search["matches"][0]["paragraph"],1)
        self.assertFalse(search["literary_understanding_verified"])
        self.assertEqual(self.catalog.search(
          category="玄幻",book_id=out["book_id"],text="根本不存在",
          shard_dir=self.root/"shards")["matches"],[])
        with self.assertRaisesRegex(BulkCorpusError,"CROSS_CATEGORY"):
            self.catalog.search(category="仙侠",book_id=out["book_id"],
                text="雨声敲打",shard_dir=self.root/"shards")
        with sqlite3.connect(self.root/"shards"/(out["book_id"]+".sqlite3")) as db:
            self.assertEqual(db.execute("PRAGMA quick_check").fetchone()[0],"ok")

    def test_duplicate_content_is_one_book_with_two_original_keys(self):
        p=self.root/"same.txt"
        p.write_text("第1章 起\n一行清楚的句子。\n",encoding="utf8")
        ka,kb=PREFIX+"01、玄幻/a.txt",PREFIX+"02、仙侠/b.txt"
        self.catalog.register([{"key":ka,"size":p.stat().st_size},
                               {"key":kb,"size":p.stat().st_size}])
        a=self.catalog.index_text_file(ka,p,self.root/"shards")
        b=self.catalog.index_text_file(kb,p,self.root/"shards")
        self.assertTrue(b["duplicate_alias"])
        self.assertEqual(a["book_id"],b["book_id"])
        self.assertEqual(self.catalog.ready_count(),1)
        self.assertEqual(self.catalog.rows("仙侠")[0]["status"],"DUPLICATE_ALIAS")

    def test_non_utf8_does_not_silently_guess_encoding(self):
        p=self.root/"gb.txt"
        p.write_bytes("古代小说中的文字。".encode("gb18030"))
        key=PREFIX+"01、玄幻/gb.txt"
        self.catalog.register([{"key":key,"size":p.stat().st_size}])
        with self.assertRaisesRegex(BulkCorpusError,"ENCODING_UNCERTAIN"):
            self.catalog.index_text_file(key,p,self.root/"shards")
        self.assertEqual(self.catalog.ready_count(),0)
        self.assertEqual(self.catalog.index_text_file(
            key,p,self.root/"shards",encoding="gb18030")["units_indexed"],1)

    def test_local_preview_no_source_text_or_symlink_read(self):
        root=self.root/"files"
        (root/"01、玄幻").mkdir(parents=True)
        (root/"01、玄幻"/"novel.txt").write_text("私有正文",encoding="utf8")
        preview=local_inventory(root,"20261018")
        self.assertEqual(len(preview),1)
        self.assertNotIn("私有正文",str(preview))
        self.assertEqual(preview[0]["category"],"玄幻")

    def test_400_metadata_objects_no_full_text_read(self):
        categories=("01、玄幻","02、仙侠","03、科幻","04、历史","05、古典")
        items=[self.record(f"{categories[i%5]}/book{i:04}.txt",size=i+1)
               for i in range(400)]
        started=time.perf_counter()
        doc=self.catalog.register(items)
        elapsed=time.perf_counter()-started
        self.assertEqual(doc["added"],400)
        self.assertFalse(doc["original_text_read"])
        self.assertEqual(self.catalog.summary()["objects"],400)
        self.assertEqual(self.catalog.summary()["distinct_indexed_books"],0)
        for category in ("玄幻","仙侠","科幻","历史","古典"):
            self.assertEqual(self.catalog.rows(category)[-1]["display_no"],80)
        self.assertLess(elapsed,15)

if __name__=="__main__":
    unittest.main()
