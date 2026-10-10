"""R2 backup/restore regression suite with a simulated S3 API.

This tests WriterForge's R2 protocol and storage invariants without access to
the author's Cloudflare account. Live integration requires an R2 bucket/token.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import sqlite3
import unittest

from writerforge import WriterForgeDB
from writerforge.r2_storage import (
    R2Config, R2StudyVault, R2StorageError, r2_configured,
    _sqlite_audit, MAX_DB_BYTES,
)


class S3Missing(Exception):
    response = {"Error":{"Code":"404"}}


class FakeR2:
    def __init__(self):
        self.objects = {}
        self.upload_count = 0
        self.download_count = 0

    def head_object(self, *, Bucket, Key):
        if (Bucket,Key) not in self.objects:
            raise S3Missing()
        data, headers = self.objects[(Bucket,Key)]
        return {"ContentLength":len(data),"Metadata":dict(headers)}

    def put_object(self, *, Bucket, Key, Body, ContentType=None, Metadata=None):
        self.objects[(Bucket,Key)] = (bytes(Body), dict(Metadata or {}))
        return {"ETag":'"test"'}

    def upload_file(self, path, bucket, key, ExtraArgs=None, Config=None):
        self.upload_count += 1
        self.objects[(bucket,key)] = (
            Path(path).read_bytes(),dict((ExtraArgs or {}).get("Metadata",{}))
        )

    def get_object(self, *, Bucket, Key):
        if (Bucket,Key) not in self.objects:
            raise S3Missing()
        return {"Body":BytesIO(self.objects[(Bucket,Key)][0])}

    def download_file(self, bucket, key, path):
        self.download_count += 1
        if (bucket,key) not in self.objects:
            raise S3Missing()
        Path(path).write_bytes(self.objects[(bucket,key)][0])


def _database(path: Path):
    db = WriterForgeDB(path)
    con = db.conn
    cur = con.execute(
        """INSERT INTO snapshots(parent_id,status,layout,note)
           VALUES(NULL,'published','full','study-test')"""
    )
    snap = cur.lastrowid
    con.execute(
        """INSERT INTO studied_works(work_id,title,source_uri,source_sha256,chapter_count)
           VALUES('xiyouji-test','西游记试读','test://original','deadbeef',1)"""
    )
    con.execute(
        """INSERT INTO source_spans(work_id,chapter,paragraph,sentence,excerpt,
                         source_sha256,tracks_json,craft_json)
           VALUES('xiyouji-test',1,1,1,'他朝石门走去。','aa','{}','{}')"""
    )
    con.execute(
        """INSERT INTO xuehai_entries(snapshot_id,work_id,chapter,paragraph,sentence,text,
                    library_class,culture,genre,source_role,function,effect,
                    method_cluster,source_hash)
           VALUES(?, 'xiyouji-test',1,1,1,'他朝石门走去。',
                 '古代白话','中国','古代白话','core','action','unknown','action','hash')""",
        (snap,),
    )
    con.execute(
        """INSERT INTO studied_chapters(work_id,chapter,chapter_sha256,heading,
                                  source_spans,retrieval_entries,snapshot_id)
           VALUES('xiyouji-test',1,'sha','第一回',1,1,?)""",
        (snap,),
    )
    con.commit()
    db.close()


class R2StudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.db_path = self.folder/"writerforge.sqlite3"
        _database(self.db_path)
        self.source = self.folder/"original.txt"
        self.source.write_text("原著中文第一回。\n第二段古代白话。", encoding="utf-8")
        self.report = self.folder/"report.json"
        self.report.write_text('{"stage":"structural"}',encoding="utf-8")
        self.cfg = R2Config(
            account_id="a"*32,bucket="private-writerforge-library",
            access_key_id="test-id",secret_access_key="test-secret",
        )
        self.fake = FakeR2()
        self.store = R2StudyVault(self.cfg,client=self.fake)

    def tearDown(self):
        self.temp.cleanup()

    def test_private_endpoint_and_environment_validation(self):
        self.assertEqual(self.cfg.endpoint,"https://"+"a"*32+".r2.cloudflarestorage.com")
        self.assertEqual(
            R2Config(account_id="a"*32,bucket="private-writerforge-library",
                     access_key_id="x",secret_access_key="y",jurisdiction="eu").endpoint,
            "https://"+"a"*32+".eu.r2.cloudflarestorage.com",
        )
        self.assertFalse(r2_configured({}))
        with self.assertRaisesRegex(R2StorageError,"partial"):
            r2_configured({"WRITERFORGE_R2_BUCKET":"private-writerforge-library"})
        with self.assertRaisesRegex(R2StorageError,"missing environment"):
            R2Config.from_environment({})
        with self.assertRaises(R2StorageError):
            R2Config(account_id="x",bucket="private-writerforge-library",
                     access_key_id="x",secret_access_key="y")
        self.assertNotIn("test-secret",str(self.cfg.endpoint))

    def test_real_sqlite_backup_and_private_restore(self):
        uploaded=self.store.backup(
            database=self.db_path,library="classic-zh",source=self.source,
            extras={"report.json":self.report},
        )
        self.assertTrue(uploaded["verified"])
        self.assertEqual(uploaded["provider"],"Cloudflare R2")
        self.assertEqual(uploaded["file_count"],3)
        self.assertEqual(uploaded["stats"]["studied_chapters"],1)
        self.assertTrue(uploaded["uri"].startswith("r2://private-writerforge-library/"))
        self.assertEqual(self.fake.upload_count,3)
        self.assertIn(("private-writerforge-library",
                       "writerforge/v1/libraries/classic-zh/latest.json"),
                      self.fake.objects)
        restored=self.store.restore(library="classic-zh",
                                    destination=self.folder/"library")
        self.assertFalse(restored["from_local_cache"])
        self.assertTrue(restored["verified"])
        self.assertEqual(
            Path(restored["source"]).read_text(encoding="utf-8"),
            self.source.read_text(encoding="utf-8"),
        )
        self.assertEqual(_sqlite_audit(Path(restored["db"])),uploaded["stats"])
        self.assertTrue((Path(restored["restored_to"])/"report.json").is_file())
        again=self.store.restore(library="classic-zh",
                                 destination=self.folder/"library")
        self.assertTrue(again["from_local_cache"])
        self.assertEqual(self.fake.download_count,3)

    def test_same_content_deduplicated_and_no_growth(self):
        first=self.store.backup(database=self.db_path,library="classics")
        count=len(self.fake.objects)
        result=self.store.backup(database=self.db_path,library="classics")
        self.assertEqual(result["snapshot"],first["snapshot"])
        self.assertEqual(self.fake.upload_count,1)
        self.assertEqual(len(self.fake.objects),count)
        self.assertEqual(result["deduplicated"],1)

    def test_reproducible_training_edition_does_not_grow_on_ci_reruns(self):
        first=self.store.backup(
            database=self.db_path,library="xiyouji-23962",
            source=self.source,edition="gutenberg23962-parser-v1"
        )
        amount=len(self.fake.objects)
        with closing(sqlite3.connect(self.db_path)) as con:
            # SQLite time metadata changes on repeated imports, but the
            # semantically identical source study remains one stored edition.
            con.execute(
                "UPDATE studied_chapters SET created_at='2027-02-02 03:04:05'"
            )
            con.commit()
        second=self.store.backup(
            database=self.db_path,library="xiyouji-23962",
            source=self.source,edition="gutenberg23962-parser-v1"
        )
        self.assertTrue(second["edition_reused"])
        self.assertEqual(first["snapshot"],second["snapshot"])
        self.assertEqual(len(self.fake.objects),amount)
        self.assertEqual(self.fake.upload_count,2)

    def test_reproducible_edition_does_not_hide_actual_study_changes(self):
        old=self.store.backup(
            database=self.db_path,library="xiyouji-23962",
            source=self.source,edition="gutenberg23962-parser-v1"
        )
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute(
                "UPDATE xuehai_entries SET function='dialogue' WHERE chapter=1"
            )
            con.commit()
        fresh=self.store.backup(
            database=self.db_path,library="xiyouji-23962",
            source=self.source,edition="gutenberg23962-parser-v1"
        )
        self.assertNotEqual(old["snapshot"],fresh["snapshot"])
        self.assertFalse(fresh["edition_reused"])

    def test_older_version_restore_after_newer_study(self):
        first=self.store.backup(database=self.db_path,library="classics")
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute("CREATE TABLE review_cache(id INTEGER PRIMARY KEY,note TEXT)")
            con.execute("INSERT INTO review_cache(note) VALUES('new later training')")
            con.commit()
        second=self.store.backup(database=self.db_path,library="classics")
        self.assertNotEqual(first["snapshot"],second["snapshot"])
        self.assertEqual(len(self.fake.objects),5)
        old=self.store.restore(library="classics",snapshot=first["snapshot"],
                               destination=self.folder/"recovery")
        newest=self.store.restore(library="classics",
                                  destination=self.folder/"recovery")
        self.assertNotEqual(old["restored_to"],newest["restored_to"])
        with closing(sqlite3.connect(old["db"])) as con:
            tables=[x[0] for x in con.execute(
                "SELECT name FROM sqlite_master WHERE name='review_cache'"
            )]
        self.assertEqual(tables,[])
        with closing(sqlite3.connect(newest["db"])) as con:
            self.assertEqual(con.execute(
                "SELECT note FROM review_cache"
            ).fetchone()[0],"new later training")

    def test_wal_transaction_in_online_snapshot(self):
        with closing(sqlite3.connect(self.db_path)) as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("INSERT INTO story_events(project_id,event_type) VALUES('novel','ACCEPT')")
            con.commit()
            # Keep the WAL connection open across the backup.
            info=self.store.backup(database=self.db_path,library="project")
            self.assertTrue(info["verified"])
            path=self.store.restore(library="project",destination=self.folder/"live")
            with closing(sqlite3.connect(path["db"])) as recovered:
                self.assertEqual(recovered.execute(
                    "SELECT COUNT(*) FROM story_events"
                ).fetchone()[0],1)

    def test_reject_tampered_remote_blob_and_leave_target_absent(self):
        latest=self.store.backup(database=self.db_path,library="classics")
        digest=sha256(Path(self.db_path).read_bytes()).hexdigest()
        manifest_key=self.store._manifest_key("classics",latest["snapshot"])
        manifest=json.loads(self.fake.objects[(self.cfg.bucket,manifest_key)][0])
        db_hash=manifest["files"]["study.sqlite3"]["sha256"]
        key=self.store._blob_key("classics",db_hash)
        raw,meta=self.fake.objects[(self.cfg.bucket,key)]
        self.fake.objects[(self.cfg.bucket,key)]=(raw[:-1]+b"x",meta)
        with self.assertRaisesRegex(R2StorageError,"SHA256|checksum"):
            self.store.restore(library="classics",destination=self.folder/"no-partial")
        self.assertFalse((self.folder/"no-partial"/"classics"/latest["snapshot"][:16]).exists())

    def test_refuse_overwriting_tampered_cached_study(self):
        self.store.backup(database=self.db_path,library="novel")
        one=self.store.restore(library="novel",destination=self.folder/"safe")
        with Path(one["db"]).open("ab") as out:
            out.write(b"MALICIOUS MODIFICATION")
        with self.assertRaisesRegex(R2StorageError,"modified"):
            self.store.restore(library="novel",destination=self.folder/"safe")

    def test_reject_invalid_library_and_extra_names_before_remote_write(self):
        with self.assertRaisesRegex(R2StorageError,"invalid library"):
            self.store.backup(database=self.db_path,library="../other")
        with self.assertRaisesRegex(R2StorageError,"extra"):
            self.store.backup(database=self.db_path,library="safe",
                              extras={"../../private.db":self.report})
        self.assertFalse(self.fake.objects)

    def test_no_fake_success_without_valid_study(self):
        other=self.folder/"blank.db"
        with closing(sqlite3.connect(other)) as con:
            con.execute("CREATE TABLE abc (id INT)")
        with self.assertRaisesRegex(R2StorageError,"compatible"):
            self.store.backup(database=other,library="not-trained")
        self.assertFalse(self.fake.objects)

    def test_manifest_or_pointer_change_is_detected(self):
        info=self.store.backup(database=self.db_path,library="novel")
        key=self.store._latest_key("novel")
        raw,meta=self.fake.objects[(self.cfg.bucket,key)]
        value=json.loads(raw)
        value["snapshot"]="0"*64
        self.fake.objects[(self.cfg.bucket,key)]=(json.dumps(value).encode("utf-8"),meta)
        with self.assertRaisesRegex(R2StorageError,"inconsistent hashes"):
            self.store.restore(library="novel",destination=self.folder/"bad")
        self.assertEqual(info["stats"]["studied_units"],1)


if __name__ == "__main__":
    unittest.main()
