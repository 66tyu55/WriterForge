"""Regression tests: raw reading vault never masquerades as studied Xuehai."""
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from writerforge.private_reading_storage import audit_private_reading, PrivateReadingVault
from writerforge.r2_storage import R2StorageError, R2Config


def make_archive(path):
    db=sqlite3.connect(path)
    db.executescript("""
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
    for i in range(13):
        text="独立原著样本第"+str(i)+"册。"
        db.execute("INSERT INTO works VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (i+1,"小说"+str(i),"original"+str(i)+".txt","a"*64,
             "gb18030",100,len(text),len(text),1,"archived_unreviewed","now"))
        db.execute("INSERT INTO sections VALUES(?,?,?,?,?,?,?,?,?)",
            (i+1,i+1,1,"第一章",1,1,text,hashlib.sha256(text.encode()).hexdigest(),len(text)))
    db.commit()
    db.close()


class RawVaultTest(unittest.TestCase):
    def test_audits_real_reading_schema_without_study_tables(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/"reading.sqlite3"
            make_archive(p)
            result=audit_private_reading(p)
            self.assertEqual(result["works"],13)
            self.assertEqual(result["sections"],13)
            self.assertEqual(result["status"],"archived_unreviewed")
            self.assertFalse(result["semantic_verified"])

    def test_missing_section_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/"reading.sqlite3"
            make_archive(p)
            with sqlite3.connect(p) as db:
                db.execute("DELETE FROM sections WHERE work_id=3")
            with self.assertRaises(R2StorageError):
                audit_private_reading(p)

    def test_corrupt_section_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)/"reading.sqlite3"
            make_archive(p)
            with sqlite3.connect(p) as db:
                db.execute("UPDATE sections SET content='changed' WHERE work_id=3")
            with self.assertRaises(R2StorageError):
                audit_private_reading(p)

    def test_namespace_does_not_change_study_vault(self):
        cfg=R2Config(account_id="a"*32,bucket="writerforge-private-library",
            access_key_id="test",secret_access_key="test")
        self.assertEqual(PrivateReadingVault(cfg)._root("private_reading_v1"),
            "writerforge/v1/private-reading/private_reading_v1")
        with self.assertRaises(R2StorageError):
            PrivateReadingVault(cfg)._root("xiyouji-23962")


if __name__=="__main__":
    unittest.main()
