"""V69 synthetic regression: existing four folders, metadata only and read probes.

Does NOT access user originals, R2 secrets, GPT models, or GitHub Actions.
"""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import parse_qs,urlsplit
import json
import unittest

from writerforge.bulk_inbox import BulkCatalog, parse_key, BulkCorpusError
from writerforge.private_reading_remote import (
    FOLDERS, WFPrivateReadingClient, PrivateReadingError,
)
ROOT="writerforge/v1/private-reading/"

class Reply:
    def __init__(self,status,headers,raw):
        self.status=status
        self.headers=headers
        self.body=BytesIO(raw)
    def __enter__(self):return self
    def __exit__(self,*args):self.body.close()
    def read(self,n):return self.body.read(n)

class FakePrivateWorker:
    def __init__(self,objects,*,per_page=40):
        self.objects=objects
        self.per_page=per_page
        self.queries=[]
        self.fail_route=False
    def open(self,req,timeout=None):
        uri=urlsplit(req.full_url)
        p={k:v[0] for k,v in parse_qs(uri.query).items()}
        method=req.get_method()
        self.queries.append((uri.path,method))
        if self.fail_route:
            raise HTTPError(req.full_url,404,"missing",{},BytesIO(b""))
        headers={}
        if uri.path.endswith("/list"):
            folder=p["folder"]
            keys=sorted(k for k in self.objects
                    if k.startswith(ROOT+folder+"/"))
            start=int(p.get("cursor","0"))
            subset=keys[start:start+self.per_page]
            more=start+len(subset)<len(keys)
            doc={
              "ok":True,"read_only":True,
              "format":"wf.private-reading-list.v1","folder":folder,
              "objects":[{"key":k,"size":len(self.objects[k]),
                          "etag":'"sha-of-object"',"uploaded":None}
                          for k in subset],
              "complete":not more,
              "next_cursor":str(start+len(subset)) if more else None,
            }
            return Reply(200,headers,json.dumps(doc).encode("utf-8"))
        if uri.path.endswith("/object"):
            key=p["key"]
            if key not in self.objects:
                raise HTTPError(req.full_url,404,"missing",{},BytesIO(b""))
            body=self.objects[key]
            headers={"X-WF-Object-Size":str(len(body)),
                     "ETag":'"sha-of-object"'}
            if method=="HEAD":
                headers["Content-Length"]=str(len(body))
                return Reply(200,headers,b"")
            begin=int(p["offset"])
            length=int(p["length"])
            headers["Content-Range"]=(
                f"bytes {begin}-{begin+length-1}/{len(body)}")
            headers["Content-Length"]=str(length)
            return Reply(206,headers,body[begin:begin+length])
        raise AssertionError("unexpected route")

class PrivateReadingOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.catalog=BulkCatalog(Path(self.tmp.name)/"metadata.sqlite3")
        self.objects={
            ROOT+"single-works/中文新增书名.txt":b"1",
            ROOT+"single-works/old_ENGLISH.txt":b"old",
            ROOT+"仙侠/第一部.txt":b"novel",
            ROOT+"历史/第一部.txt":b"history",
            ROOT+"科幻/第一部.txt":b"sci-fi",
        }
        self.worker=FakePrivateWorker(self.objects,per_page=2)
        self.client=WFPrivateReadingClient(
            endpoint="https://wf-r2-api.3227482831.workers.dev",
            token="synthetic-token-0123456789-anything",
        )
        self.client._opener=self.worker
    def tearDown(self):
        self.catalog.close()
        self.tmp.cleanup()

    def test_four_folders_real_prefix_and_unknown_single_work_genre(self):
        self.assertEqual(len(FOLDERS),4)
        self.assertEqual(parse_key(ROOT+"仙侠/小说1.txt")["category"],"仙侠")
        self.assertEqual(parse_key(ROOT+"历史/小说2.txt")["category"],"历史")
        self.assertEqual(parse_key(ROOT+"科幻/小说3.txt")["category"],"科幻")
        self.assertEqual(parse_key(ROOT+"single-works/中国小说.txt")["category"],"待分类")
        self.assertEqual(parse_key(ROOT+"single-works/玄幻/某书.txt")["category"],"玄幻")
        self.assertEqual(parse_key(ROOT+"仙侠/某书/001.txt")["status"],
                         "GROUPED_FILES_NEED_ASSEMBLY")
        with self.assertRaises(BulkCorpusError):
            parse_key(ROOT+"仙侠/../private.txt")
        with self.assertRaises(BulkCorpusError):
            parse_key(ROOT+"unknown/小说.txt")

    def test_realistic_five_object_scan_no_names_or_prose_in_report(self):
        result=self.client.inventory_to_catalog(self.catalog)
        self.assertEqual(result["total_objects"],5)
        self.assertEqual(result["folder_summary"]["single-works"]["objects"],2)
        self.assertEqual(result["ranged_read_probes_passed"],4)
        self.assertEqual(result["remote_write_requests"],0)
        self.assertFalse(result["newly_uploaded_objects_proven"])
        self.assertEqual(result["catalog"]["objects"],5)
        self.assertEqual(result["catalog"]["distinct_indexed_books"],0)
        self.assertEqual(self.catalog.rows("待分类")[0]["display_no"],1)
        self.assertNotIn("中文新增书名",str(result))
        self.assertNotIn("old_ENGLISH",str(result))
        self.assertTrue(all(method in ("HEAD","GET") for _,method in
                            self.worker.queries))

    def test_repeat_inventory_is_idempotent(self):
        self.client.inventory_to_catalog(self.catalog)
        first=self.catalog.rows("待分类")
        self.client.inventory_to_catalog(self.catalog)
        self.assertEqual(self.catalog.rows("待分类"),first)

    def test_400_objects_chunked_pagination_and_no_contents_download(self):
        self.objects.clear()
        for folder in FOLDERS:
            for i in range(100):
                self.objects[ROOT+folder+f"/book{i:03}.txt"]=b"x"
        result=self.client.inventory_to_catalog(self.catalog)
        self.assertEqual(result["total_objects"],400)
        self.assertEqual(result["ranged_read_probes_passed"],4)
        self.assertEqual(self.catalog.summary()["objects"],400)
        self.assertEqual(self.catalog.ready_count(),0)
        self.assertTrue(result["all_folders_complete"])
        self.assertGreater(result["total_pages"],4)

    def test_route_not_deployed_cannot_be_success(self):
        self.worker.fail_route=True
        with self.assertRaisesRegex(PrivateReadingError,
                                    "WF_PRIVATE_ROUTE_NOT_DEPLOYED"):
            self.client.inventory_to_catalog(self.catalog)
        self.assertEqual(self.catalog.summary()["objects"],0)

    def test_out_of_scope_server_entry_rejected(self):
        self.objects[ROOT+"single-works/../../leak.txt"]=b"x"
        with self.assertRaises(BulkCorpusError):
            self.client.inventory_to_catalog(self.catalog)

    def test_unapproved_folder_and_zero_size_marker(self):
        self.objects[ROOT+"历史/folder/"]=b""
        # Worker must drop zero-size directory markers itself; simulator
        # intentionally does not, validating that client fails closed.
        with self.assertRaises(BulkCorpusError):
            self.client.inventory_to_catalog(self.catalog)
        with self.assertRaisesRegex(PrivateReadingError,"FOLDER_NOT_ALLOWED"):
            self.client.list_page("玄幻")

if __name__=="__main__":
    unittest.main()
