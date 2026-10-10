"""Durable study library contract: no manual ZIP, no unbounded archives.

The local fixture is synthetic 100-chapter Chinese text, NOT a claim to have
trained literary skills. CI separately runs the full real Gutenberg original.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import shutil
import unittest
import zipfile

from writerforge import WriterForgeDB, RuntimeEngine, OriginalStudy, VerifiedWritingFlow
from writerforge.study_storage import (
    BUNDLE_NAME, MANIFEST_NAME, RELEASE_PREFIX, StudyStorageError,
    prepare_release, validate_bundle, restore_from_github,
)


class StudyReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.source=self.root/"source"
        self.source.mkdir()
        content="\n\n".join(
            f"第{i}回 虚构测试回目{i}\n猴王忽出石洞，山风大作。他见众人笑道：“此处甚好。”"
            for i in range(1,101)
        )
        (self.source/"xiyouji_23962_original.txt").write_text(content,encoding="utf-8")
        db_path=self.source/"xiyouji_studied.sqlite3"
        db=WriterForgeDB(db_path)
        rt=RuntimeEngine()
        rt.enter_learn()
        report=OriginalStudy(db,rt).ingest(content)
        rt.exit()
        row=db.conn.execute("SELECT MAX(id) FROM snapshots").fetchone()
        rt.enter_write(int(row[0]))
        frame=VerifiedWritingFlow(db,rt,"synthetic-test").prepare(
            "ch001.sc01","写一段完全原创的故事", concerns=("description",)
        )
        (self.source/"verified_draft_context.json").write_text(
            json.dumps({**frame.manifest(),"prompt":frame.prompt},ensure_ascii=False),
            encoding="utf-8",
        )
        report["source_raw_sha256"]=sha256(
            (self.source/"xiyouji_23962_original.txt").read_bytes()
        ).hexdigest()
        report["model_generation_performed"]=False
        report["independent_litcritic_performed"]=False
        (self.source/"training_report.json").write_text(
            json.dumps(report,ensure_ascii=False),encoding="utf-8"
        )
        (self.source/"TRAINING_STATUS.md").write_text(
            "合成原文，用于软件完整性单元测试；并非真实文学训练。",encoding="utf-8"
        )
        (self.source/"PROJECT_GUTENBERG_LICENSE.txt").write_text(
            "Synthetic test fixture, not a redistribution of the Gutenberg file.",
            encoding="utf-8",
        )
        db.close()
        self.bundle_dir=self.root/"bundle"
        self.pack=prepare_release(self.source,self.bundle_dir)
        self.manifest=json.loads(
            (self.bundle_dir/MANIFEST_NAME).read_text(encoding="utf-8")
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_package_and_restore_original_study(self):
        self.assertEqual(self.pack["tag"],RELEASE_PREFIX+self.manifest["source_raw_sha256"][:16])
        self.assertEqual(self.manifest["studied_chapters"],100)
        self.assertTrue(self.pack["compressed_bytes"]>0)
        result=validate_bundle(self.bundle_dir/BUNDLE_NAME,self.bundle_dir/MANIFEST_NAME,
                               self.root/"unpacked")
        self.assertTrue(result["verified"])
        self.assertEqual(result["release_tag"],self.pack["tag"])
        db=WriterForgeDB(result["db"])
        self.assertEqual(db.conn.execute(
            "SELECT COUNT(*) FROM studied_chapters"
        ).fetchone()[0],100)
        self.assertEqual(db.conn.execute(
            "SELECT COUNT(*) FROM studied_works"
        ).fetchone()[0],1)
        db.close()

    def test_restore_never_overwrites_a_working_database(self):
        target=self.root/"my-novel-working-data"
        target.mkdir()
        (target/"author.md").write_text("MY OWN LONG NOVEL",encoding="utf-8")
        with self.assertRaisesRegex(StudyStorageError,"refusing to overwrite"):
            validate_bundle(self.bundle_dir/BUNDLE_NAME,self.bundle_dir/MANIFEST_NAME,target)
        self.assertEqual((target/"author.md").read_text(encoding="utf-8"),
                         "MY OWN LONG NOVEL")

    def test_tampered_or_bad_hash_never_commits_partial_restore(self):
        corrupted=self.root/"tampered.manifest.json"
        data=dict(self.manifest)
        data["archive"]=dict(data["archive"])
        data["archive"]["sha256"]="0"*64
        corrupted.write_text(json.dumps(data),encoding="utf-8")
        target=self.root/"not-installed"
        with self.assertRaisesRegex(StudyStorageError,"hash or size mismatch"):
            validate_bundle(self.bundle_dir/BUNDLE_NAME,corrupted,target)
        self.assertFalse(target.exists())

    def test_disallow_unknown_archive_entries_or_path_traversal(self):
        malicious=self.root/BUNDLE_NAME
        with zipfile.ZipFile(malicious,"w",compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("../../evil.txt",b"malicious")
        meta=dict(self.manifest)
        meta["archive"]=dict(meta["archive"])
        meta["archive"]["sha256"]=sha256(malicious.read_bytes()).hexdigest()
        meta["archive"]["size"]=malicious.stat().st_size
        mpath=self.root/MANIFEST_NAME
        mpath.write_text(json.dumps(meta),encoding="utf-8")
        with self.assertRaisesRegex(StudyStorageError,"unsafe or unexpected"):
            validate_bundle(malicious,mpath,self.root/"safely-declined")
        self.assertFalse((self.root/"evil.txt").exists())

    def test_wrong_source_fails_before_bundle_creation(self):
        wrong=self.source/"xiyouji_23962_original.txt"
        wrong.write_text("Not the approved original!",encoding="utf-8")
        with self.assertRaisesRegex(StudyStorageError,"source hash"):
            prepare_release(self.source,self.root/"bad")

    def test_mocked_github_restore_and_idempotent_cache(self):
        repo="66tyu55/WriterForge"
        tag=self.pack["tag"]
        release={
            "tag_name":tag,"draft":False,"published_at":"2026-10-10T00:00:00Z",
            "assets":[
                {"name":name,"browser_download_url":
                    f"https://github.com/{repo}/releases/download/{tag}/{name}"}
                for name in (MANIFEST_NAME,BUNDLE_NAME)
            ],
        }
        def fake_download(url,target,**_):
            name=url.rsplit("/",1)[-1]
            shutil.copyfile(self.bundle_dir/name,target)
        with patch("writerforge.study_storage._read_limited_json",return_value=[release]),\
             patch("writerforge.study_storage._download_limited",side_effect=fake_download) as download:
            restored=restore_from_github(storage_dir=self.root/"library")
            self.assertTrue(restored["verified"])
            self.assertFalse(restored["from_local_cache"])
            self.assertEqual(download.call_count,2)
            reused=restore_from_github(storage_dir=self.root/"library")
            self.assertTrue(reused["from_local_cache"])
            self.assertEqual(download.call_count,2)

    def test_cache_tampering_is_detected_no_silent_reuse(self):
        repo="66tyu55/WriterForge"
        tag=self.pack["tag"]
        release={"tag_name":tag,"assets":[
            {"name":name,"browser_download_url":
             f"https://github.com/{repo}/releases/download/{tag}/{name}"}
            for name in (MANIFEST_NAME,BUNDLE_NAME)
        ]}
        with patch("writerforge.study_storage._read_limited_json",return_value=release),\
             patch("writerforge.study_storage._download_limited",
                   side_effect=lambda url,dest,**kw: shutil.copyfile(
                       self.bundle_dir/url.rsplit("/",1)[-1],dest)):
            restored=restore_from_github(storage_dir=self.root/"library",tag=tag)
        Path(restored["source"]).write_text("The original text was changed",encoding="utf-8")
        with patch("writerforge.study_storage._read_limited_json",return_value=release):
            with self.assertRaises(StudyStorageError):
                restore_from_github(storage_dir=self.root/"library",tag=tag)

    def test_repo_and_release_tag_input_validation(self):
        with self.assertRaisesRegex(StudyStorageError,"invalid GitHub repo"):
            restore_from_github(repo="evil-host/internal/repo",storage_dir=self.root/"out")
        with self.assertRaisesRegex(StudyStorageError,"invalid study release tag"):
            restore_from_github(tag="../malicious",storage_dir=self.root/"out")


if __name__=="__main__":
    unittest.main()
