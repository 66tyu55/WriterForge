"""V71 one-TXT R2 Range->SHA->temporary SQLite synthetic contract tests.

No user novels, no Cloudflare credentials, no paid models, no R2 writes.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge.bulk_inbox import BulkCatalog
from writerforge.private_reading_remote import WFPrivateReadingClient
from writerforge.private_r2_sql_smoke import (
    MAX_ONE_FILE_BYTES, MIN_ONE_FILE_BYTES,
    SourceIndexSmokeError, choose_one_source,
    download_one_verified, _locally_check_search,
)
ROOT="writerforge/v1/private-reading/"

class FakeClient(WFPrivateReadingClient):
    def __init__(self,objects,bad_etag=False,short_range=False):
        super().__init__(
            endpoint="https://wf-r2-api.3227482831.workers.dev",
            token="synthetic-testing-token-123456789")
        self.objects=objects
        self.bad_etag=bad_etag
        self.short_range=short_range
        self.methods=[]
    def _request(self,path,params,method="GET",cap=None):
        self.methods.append(method)
        assert path=="/r2/private-reading/object"
        data=self.objects[params["key"]]
        etag='"immutable-test-etag"'
        if method=="HEAD":
            return {"Content-Length":str(len(data)),
                    "X-WF-Object-Size":str(len(data)),
                    "ETag":etag},b""
        offset=params["offset"];length=params["length"]
        raw=data[offset:offset+length]
        if self.short_range:raw=raw[:-1]
        return {
          "Content-Length":str(length),
          "X-WF-Object-Size":str(len(data)),
          "Content-Range":f"bytes {offset}-{offset+length-1}/{len(data)}",
          "ETag":'"altered-etag"' if self.bad_etag else etag,
        },raw

class V71OneRealSourceSmokeSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.cat=BulkCatalog(self.root/"catalog.sqlite3")
    def tearDown(self):
        self.cat.close()
        self.tmp.cleanup()
    def add(self,key,size):
        self.cat.register([{"key":ROOT+key,
                            "size":size,
                            "etag":'"immutable-test-etag"'}])

    def test_selection_rejects_archive_pairs_and_picks_size_only(self):
        self.add("仙侠/某书/正文.txt",20000)
        self.add("仙侠/某书/备份.rar",20000)
        self.add("历史/另一本/正文.txt",17000)
        self.add("科幻/第三本/正文.txt",35000)
        row,count=choose_one_source(self.cat)
        self.assertEqual(row["category"],"历史")
        self.assertEqual(count,2)
        self.assertEqual(row["size_bytes"],17000)

    def test_one_complete_synthetic_txt_is_indexed_and_queried(self):
        src=("第1章 雨夜\n"+
             "远处传来脚步声，少年停下了动作。\n"*300+
             "第2章 归来\n" +
             "天空逐渐暗了下来。\n"*200).encode("utf8")
        key=ROOT+"科幻/某独立作品/正文.txt"
        self.add("科幻/某独立作品/正文.txt",len(src))
        row,count=choose_one_source(self.cat)
        self.assertEqual(count,1)
        client=FakeClient({key:src})
        target=self.root/"source.txt"
        transferred=download_one_verified(client,row,target)
        self.assertEqual(transferred["source_sha256"],sha256(src).hexdigest())
        self.assertEqual(transferred["bytes"],len(src))
        self.assertTrue(all(x in ("GET","HEAD") for x in client.methods))
        index=self.cat.index_text_file(
             row["object_key"],target,self.root/"shards")
        self.assertGreater(index["units_indexed"],0)
        self.assertEqual(index["source_sha256"],transferred["source_sha256"])
        readback=_locally_check_search(
            self.cat,index["book_id"],"科幻",self.root/"shards")
        self.assertEqual(readback["status"],"SELF_DERIVED_LEXICAL_HIT")
        self.assertGreater(readback["hits"],0)
        self.assertFalse(readback["real_source_excerpt_returned"])
        self.assertFalse(readback["independent_relevance_or_literary_understanding_proven"])

    def test_http_etag_flip_fails_closed_without_leaving_file(self):
        raw=b"abcxyz"*4000
        key=ROOT+"仙侠/单文件/正文.txt"
        self.add("仙侠/单文件/正文.txt",len(raw))
        row,_=choose_one_source(self.cat)
        client=FakeClient({key:raw},bad_etag=True)
        target=self.root/"would-not-remain.txt"
        with self.assertRaisesRegex(SourceIndexSmokeError,"RANGE_RESPONSE_INCONSISTENT"):
            download_one_verified(client,row,target)
        self.assertFalse(target.exists())

    def test_truncated_range_refused(self):
        raw=b"xyz"*5000
        key=ROOT+"历史/单文件/正文.txt"
        self.add("历史/单文件/正文.txt",len(raw))
        row,_=choose_one_source(self.cat)
        client=FakeClient({key:raw},short_range=True)
        target=self.root/"partial.txt"
        with self.assertRaisesRegex(SourceIndexSmokeError,"RANGE_RESPONSE_INCONSISTENT"):
            download_one_verified(client,row,target)
        self.assertFalse(target.exists())

    def test_multichunk_download_stays_bounded(self):
        raw=b"src-v71-data"*100000
        key=ROOT+"历史/测试分块/正文.txt"
        self.add("历史/测试分块/正文.txt",len(raw))
        row,_=choose_one_source(self.cat)
        client=FakeClient({key:raw})
        report=download_one_verified(
            client,row,self.root/"local-test.bin")
        self.assertEqual(report["source_sha256"],sha256(raw).hexdigest())
        self.assertGreater(report["requests"],2)
        self.assertLessEqual(report["requests"],17)

    def test_invalid_size_and_multiple_file_siblings_not_selected(self):
        self.add("科幻/微小/正文.txt",MIN_ONE_FILE_BYTES-1)
        self.add("历史/过大/正文.txt",MAX_ONE_FILE_BYTES+1)
        self.add("仙侠/拆卷/上.txt",15000)
        self.add("仙侠/拆卷/下.txt",14000)
        with self.assertRaisesRegex(SourceIndexSmokeError,"NO_SAFE_SINGLE"):
            choose_one_source(self.cat)

if __name__=="__main__":
    unittest.main()
