"""Private R2 one-book transfer tests: real SQLite sections, mocked S3 transport.

The tests never access private originals or R2 keys. They assert the pipeline
extracts ONLY 星辰变, fails on wrong source, uses a real R2 inventory, and
checks a fresh download's exact SHA-256.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import sqlite3
import unittest

import writerforge.private_single_book_transfer as transfer
from writerforge.private_single_book_transfer import (
    PrivateSingleBookVault, extract_one_book, BOOK_ID, SOURCE_R2_KEY,
)
from writerforge.r2_storage import R2Config, R2StorageError, _digest


class NotFound(Exception):
    response={"Error":{"Code":"404"}}


class FakeS3:
    def __init__(self):
        self.objects={}
        self.upload_count=0

    def put_object(self, *, Bucket,Key,Body,ContentType=None,Metadata=None):
        self.objects[(Bucket,Key)]=(bytes(Body),dict(Metadata or {}))

    def head_object(self, *, Bucket,Key):
        item=self.objects.get((Bucket,Key))
        if item is None:
            raise NotFound()
        data,meta=item
        return {"ContentLength":len(data),"Metadata":meta}

    def upload_file(self,filepath,bucket,key,ExtraArgs=None,Config=None):
        self.upload_count+=1
        self.objects[(bucket,key)]=(
            Path(filepath).read_bytes(),
            dict((ExtraArgs or {}).get("Metadata",{})),
        )

    def download_file(self,bucket,key,path):
        entry=self.objects.get((bucket,key))
        if entry is None:
            raise NotFound()
        Path(path).write_bytes(entry[0])

    def get_object(self, *, Bucket,Key):
        if (Bucket,Key) not in self.objects:
            raise NotFound()
        return {"Body":BytesIO(self.objects[(Bucket,Key)][0])}

    def list_objects_v2(self, *, Bucket,Prefix,MaxKeys):
        rows=[
            {"Key":k,"Size":len(data)}
            for (b,k),(data,meta) in sorted(self.objects.items())
            if b==Bucket and k.startswith(Prefix)
        ]
        return {"Contents":rows[:MaxKeys],"IsTruncated":len(rows)>MaxKeys}


def make_13_work_archive(path: Path, *,ambiguous:bool=False):
    with closing(sqlite3.connect(path)) as con:
        con.executescript("""
        CREATE TABLE corpus_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE works(
            id INTEGER PRIMARY KEY,title TEXT UNIQUE NOT NULL,file_name TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,original_encoding TEXT NOT NULL,
            original_bytes INTEGER NOT NULL,original_chars INTEGER NOT NULL,
            archived_chars INTEGER NOT NULL,section_count INTEGER NOT NULL,
            status TEXT NOT NULL,added_utc TEXT NOT NULL);
        CREATE TABLE sections(
            id INTEGER PRIMARY KEY,work_id INTEGER,ordinal INTEGER,heading TEXT,
            source_line_start INTEGER,source_line_end INTEGER,content TEXT,
            content_sha256 TEXT,char_count INTEGER);
        INSERT INTO corpus_meta VALUES('schema','private_reading_v1');
        """)
        expected=""
        for i in range(1,14):
            is_target=i==4 or (ambiguous and i==5)
            name=("星辰变"+("（校验用第二同名副本）" if ambiguous and i==5 else "")
                  if is_target else "小说"+str(i))
            segments=(
                ("第1章 那夜\n他看见流星落进荒山，便决定离开故乡。\n",
                 "第一卷"),
                ("第2章 再见\n旧友在桥头等候，雨滴落在少年破旧的斗笠上。\n",
                 "第二卷"),
            ) if is_target else ((f"第{i}章 匿名测试内容\n古籍样本{i}。","章节"),)
            text="".join(part for part,_ in segments)
            original_bytes=len(text.encode("gb18030"))
            con.execute(
                "INSERT INTO works VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (i,name,name+".txt",sha256(text.encode("gb18030")).hexdigest(),
                 "gb18030",original_bytes,len(text),len(text),len(segments),
                 "archived_unreviewed","now"),
            )
            for index,(section,heading) in enumerate(segments,1):
                con.execute(
                    """INSERT INTO sections(
                        work_id,ordinal,heading,source_line_start,source_line_end,
                        content,content_sha256,char_count)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (i,index,heading,1,1,section,
                     sha256(section.encode("utf-8")).hexdigest(),len(section)),
                )
            if i==4:
                expected=text
        con.commit()
    return expected


class PrivateOneBookTransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.source=self.root/"private.sqlite3"
        self.expected=make_13_work_archive(self.source)
        self.digest,size=_digest(self.source)
        self.size=size
        self.fake=FakeS3()
        self.config=R2Config(
            account_id="a"*32,bucket="writerforge-private-library",
            access_key_id="fake-key-id",secret_access_key="fake-secret",
        )
        self.fake.objects[(self.config.bucket,SOURCE_R2_KEY)]=(
            self.source.read_bytes(),{},
        )
        self.vault=PrivateSingleBookVault(self.config,client=self.fake)

    def tearDown(self):
        self.tmp.cleanup()

    def run_one(self):
        with patch.object(transfer,"SOURCE_R2_SHA256",self.digest), \
             patch.object(transfer,"SOURCE_R2_BYTES",self.size):
            return self.vault.smoke_transfer(
                source_hash=self.digest,source_bytes=self.size,
            )

    def test_exactly_one_book_extracted_and_each_section_preserved(self):
        output=self.root/"single.txt"
        proof=extract_one_book(self.source,output)
        self.assertEqual(output.read_text(encoding="utf-8"),self.expected)
        self.assertEqual(proof["section_count"],2)
        self.assertEqual(proof["characters"],len(self.expected))
        self.assertEqual(proof["utf8_sha256"],
                         sha256(self.expected.encode("utf-8")).hexdigest())
        self.assertFalse(proof["training_performed"])
        self.assertNotEqual(proof["original_filename_sha256_declared"],
                            proof["utf8_sha256"])
        self.assertEqual(
            len(self.fake.objects),1,
            "reading should not create ANY new R2 objects",
        )

    def test_actual_immutable_upload_listing_fresh_download_sha256(self):
        result=self.run_one()
        self.assertTrue(result["target_bucket_matches_expected"])
        self.assertTrue(result["source_archive_sha256_verified"])
        self.assertTrue(result["fresh_download_sha256_verified"])
        self.assertEqual(result["remote_objects_present"],3)
        self.assertTrue(result["other_12_works_unchanged"])
        self.assertTrue(result["uploaded"])
        self.assertFalse(result["training_performed"])
        self.assertEqual(self.fake.upload_count,1)
        self.assertEqual(len(self.fake.objects),4) # root + blob + manifest + latest
        names=[key for (bucket,key) in self.fake.objects if key!=SOURCE_R2_KEY]
        self.assertTrue(all(
            x.startswith("writerforge/v1/private-reading/single-works/xingchenbian/")
            for x in names
        ))
        self.assertEqual(self.fake.objects[(self.config.bucket,SOURCE_R2_KEY)][0],
                         self.source.read_bytes())

    def test_repeat_is_idempotent_does_not_duplicate_or_clobber(self):
        first=self.run_one()
        count=len(self.fake.objects)
        second=self.run_one()
        self.assertEqual(first["snapshot"],second["snapshot"])
        self.assertFalse(second["uploaded"])
        self.assertEqual(len(self.fake.objects),count)
        self.assertEqual(self.fake.upload_count,1)

    def test_wrong_expected_sha_fails_before_upload(self):
        with patch.object(transfer,"SOURCE_R2_SHA256","0"*64), \
             patch.object(transfer,"SOURCE_R2_BYTES",self.size):
            with self.assertRaisesRegex(R2StorageError,"pinned SHA256"):
                self.vault.smoke_transfer(
                    source_hash="0"*64,source_bytes=self.size,
                )
        self.assertEqual(len(self.fake.objects),1)

    def test_missing_source_fails_closed_without_new_objects(self):
        self.fake.objects.clear()
        with patch.object(transfer,"SOURCE_R2_SHA256",self.digest), \
             patch.object(transfer,"SOURCE_R2_BYTES",self.size):
            with self.assertRaisesRegex(R2StorageError,"source archive missing"):
                self.vault.smoke_transfer(
                    source_hash=self.digest,source_bytes=self.size,
                )
        self.assertFalse(self.fake.objects)

    def test_two_matching_titles_rejected_before_remote_modifications(self):
        source=self.root/"ambiguous.sqlite3"
        make_13_work_archive(source,ambiguous=True)
        with self.assertRaisesRegex(R2StorageError,"unique 星辰变"):
            extract_one_book(source,self.root/"not-safe.txt")

    def test_wrong_private_bucket_rejected(self):
        other=R2Config(
            account_id="a"*32,bucket="different-bucket",
            access_key_id="k",secret_access_key="s",
        )
        with patch.object(transfer,"SOURCE_R2_SHA256",self.digest), \
             patch.object(transfer,"SOURCE_R2_BYTES",self.size):
            with self.assertRaisesRegex(R2StorageError,"does not match"):
                PrivateSingleBookVault(other,client=self.fake).smoke_transfer(
                    source_hash=self.digest,source_bytes=self.size,
                )
        self.assertEqual(len(self.fake.objects),1)


if __name__=="__main__":
    unittest.main()
