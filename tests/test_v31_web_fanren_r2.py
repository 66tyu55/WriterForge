"""Synthetic-only acceptance tests for real web pinned-text R2 transfer."""
from __future__ import annotations

from hashlib import sha1,sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from writerforge.r2_storage import R2Config,R2StorageError,_digest
from writerforge.single_work_runner import SingleWorkVault
import scripts.archive_web_fanren_r2 as web_archive


class Missing(Exception):
    response={"Error":{"Code":"404"}}


class FakeR2:
    def __init__(self):
        self.objects={}
        self.uploads=0
    def head_object(self,*,Bucket,Key):
        item=self.objects.get((Bucket,Key))
        if item is None: raise Missing()
        body,metadata=item
        return {"ContentLength":len(body),"Metadata":metadata}
    def upload_file(self,path,bucket,key,ExtraArgs=None,Config=None):
        self.uploads+=1
        self.objects[(bucket,key)]=(Path(path).read_bytes(),
                                  (ExtraArgs or {}).get("Metadata",{}))
    def put_object(self,*,Bucket,Key,Body,ContentType=None,Metadata=None):
        self.objects[(Bucket,Key)]=(bytes(Body),dict(Metadata or {}))
    def download_file(self,bucket,key,path):
        Path(path).write_bytes(self.objects[(bucket,key)][0])
    def get_object(self,*,Bucket,Key):
        return {"Body":BytesIO(self.objects[(Bucket,Key)][0])}
    def list_objects_v2(self,*,Bucket,Prefix,MaxKeys):
        rows=[{"Key":k,"Size":len(body)} for (b,k),(body,_) in
              sorted(self.objects.items()) if b==Bucket and k.startswith(Prefix)]
        return {"Contents":rows[:MaxKeys],"IsTruncated":len(rows)>MaxKeys}


class WebArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.folder=Path(self.tmp.name)
        self.path=self.folder/"source.txt"
        # Small synthetic source, never user/website copyrighted prose.
        self.raw=("凡人修仙传 作者：忘语\n"+"第一章 合成测试\n"
                  +"韩立正在练习验收代码。\n"*20)*3
        self.raw=self.raw.encode("utf-8")
        self.path.write_bytes(self.raw)
        self.git_sha=sha1(f"blob {len(self.raw)}\0".encode()+self.raw).hexdigest()
        self.vault=SingleWorkVault(
            R2Config(account_id="a"*32,bucket="writerforge-private-library",
                     access_key_id="example",secret_access_key="example"),
            work_id="fanrenxiuxian",client=FakeR2(),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _source(self):
        return {
            "bytes":len(self.raw),"sha256":sha256(self.raw).hexdigest(),
            "git_blob_sha1":self.git_sha,
            "chapter_heading_occurrences":3,
        }

    def test_actual_web_source_is_pinned_to_exact_commit_and_git_blob(self):
        self.assertEqual(web_archive.SOURCE_COMMIT,
                         "cfff249d7191af16cde9e89bc1447d3203d04629")
        self.assertEqual(web_archive.SOURCE_GIT_BLOB,
                         "05bbc28304d231a630e7e7442ab2e5055f707436")
        self.assertIn(web_archive.SOURCE_COMMIT,web_archive.SOURCE_URL)
        self.assertIn("raw.githubusercontent.com",web_archive.SOURCE_URL)

    def test_fresh_private_r2_archive_and_resume_use_no_legacy_master(self):
        with patch.object(web_archive,"SOURCE_SIZE",len(self.raw)):
            first=web_archive.archive_to_private_r2(
                self.vault,self.path,self._source())
            self.assertTrue(first["new_private_archive"])
            self.assertTrue(first["fresh_roundtrip"])
            self.assertEqual(self.vault.client.uploads,1)
            self.assertEqual(len(self.vault.client.objects),3)
            second=web_archive.archive_to_private_r2(
                self.vault,self.path,self._source())
            self.assertFalse(second["new_private_archive"])
            self.assertFalse(second["uploaded_new_blob"])
            self.assertTrue(second["fresh_roundtrip"])

    def test_corrupt_remote_source_not_reported_as_success(self):
        first=web_archive.archive_to_private_r2(
            self.vault,self.path,self._source())
        self.assertTrue(first["fresh_roundtrip"])
        blob=self.vault._blob_key("fanrenxiuxian",self._source()["sha256"])
        old,metadata=self.vault.client.objects[(self.vault.config.bucket,blob)]
        self.vault.client.objects[(self.vault.config.bucket,blob)]=(b"x"+old[1:],metadata)
        with self.assertRaisesRegex(R2StorageError,"fresh download SHA256"):
            web_archive.archive_to_private_r2(self.vault,self.path,self._source())

    def test_source_change_is_refused(self):
        with patch.object(web_archive,"SOURCE_SIZE",len(self.raw)):
            with patch.object(web_archive,"SOURCE_GIT_BLOB","0"*40):
                with self.assertRaisesRegex(web_archive.SourceArchiveError,"GIT_BLOB_MISMATCH"):
                    web_archive.validate_downloaded(self.path)

    def test_source_download_is_separate_from_r2_access(self):
        # Merely inspecting a public source never requests R2 credentials.
        with patch.object(web_archive,"SOURCE_SIZE",len(self.raw)), \
             patch.object(web_archive,"SOURCE_GIT_BLOB",self.git_sha), \
             patch.object(web_archive,"CHAPTER_HEADING",
                          __import__("re").compile(r"^\s*第一章")):
            with patch.object(web_archive,"SOURCE_SIZE",len(self.raw)):
                # Still rejects low chapter count as incomplete, not marked archived.
                with self.assertRaisesRegex(web_archive.SourceArchiveError,"CONTENT_INCOMPLETE"):
                    web_archive.validate_downloaded(self.path)


if __name__=="__main__":
    unittest.main()
