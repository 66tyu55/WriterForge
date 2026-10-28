"""WF 0.BO: exact version source byte provenance and actual READ→staging.

No third-party novel training, model, private R2, external signer keys or Canon.
The full-source integration uses a pinned public file only when supplied by
the dedicated GitHub Action. Other default repo tests do not download it.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from experiments.wf_0bo_pinned_gutenberg_source_review import (
    load_source_manifest,pin_source_bytes,stage_pinned_first_chapter,
    MANIFEST,RAW_SHA256,NORMALIZED_SHA256,FIRST_CHAPTER_SHA256,
    SOURCE_BYTES,BLOB_SHA1,PINNED_COMMIT,PINNED_URL,
)


class WF0BOPinnedPublicSourceReview(unittest.TestCase):
    def setUp(self):
        self.t=TemporaryDirectory()
        self.root=Path(self.t.name)

    def tearDown(self):
        self.t.cleanup()

    def test_source_catalog_pins_actual_byte_identity_and_zero_authorization(self):
        obj,digest=load_source_manifest()
        self.assertEqual(len(digest),64)
        self.assertEqual(obj["pinned_git_commit"],PINNED_COMMIT)
        self.assertEqual(obj["pinned_raw_source_uri"],PINNED_URL)
        self.assertEqual(obj["pinned_git_blob_sha1"],BLOB_SHA1)
        self.assertEqual(obj["raw_source_sha256"],RAW_SHA256)
        self.assertEqual(obj["normalized_source_sha256"],NORMALIZED_SHA256)
        self.assertEqual(obj["first_chapter_sha256"],FIRST_CHAPTER_SHA256)
        self.assertEqual(obj["raw_source_size_bytes"],SOURCE_BYTES)
        self.assertFalse(obj["actual_unverified_methods_published_to_writer"])
        self.assertFalse(obj["reviewer_keys_or_signatures_in_repo"])
        self.assertFalse(obj["literary_benefit_proven"])

    def test_source_manifest_and_wrong_source_bytes_fail_closed(self):
        data=json.loads(MANIFEST.read_text("utf8"))
        data["raw_source_sha256"]="0"*64
        p=self.root/"tampered-source.json"
        p.write_text(json.dumps(data,ensure_ascii=False),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"SOURCE_IDENTITY"):
            load_source_manifest(p)
        with self.assertRaisesRegex(ValueError,"BYTE_LENGTH_DRIFT"):
            pin_source_bytes(b"not the source")
        with self.assertRaisesRegex(ValueError,"BYTE_LENGTH_DRIFT"):
            pin_source_bytes(b"X"*15)

    def test_actual_pinned_first_chapter_and_review_packet_have_no_permissions(self):
        path=os.getenv("WF0BO_PINNED_SOURCE_FILE")
        if not path:
            self.skipTest("dedicated pinned source workflow only; no network in default tests")
        source=Path(path)
        self.assertTrue(source.is_file())
        raw=source.read_bytes()
        text,identity=pin_source_bytes(raw)
        self.assertEqual(identity["source_bytes"],SOURCE_BYTES)
        self.assertEqual(identity["chapter_1_sha256"],FIRST_CHAPTER_SHA256)
        self.assertIn("我等即拜他為王",text)
        self.assertIn("所以不能修行",text)
        db=self.root/"real-source-study.sqlite3"
        dest=self.root/"reviewer-evidence"
        result=stage_pinned_first_chapter(source,db,dest)
        self.assertEqual(result["actual_original_chapters_structurally_studied"],1)
        self.assertEqual(result["pending_method_cards"],2)
        self.assertEqual(result["write_admissible_method_cards"],0)
        self.assertEqual(result["real_externally_signed_reviewers"],0)
        self.assertEqual(result["model_calls"],0)
        self.assertEqual(result["production_canon_writes"],0)
        self.assertFalse(result["literary_benefit_proven"])
        packet=json.loads((dest/"REVIEW_PACKET.json").read_text("utf8"))
        self.assertEqual(packet["status"],"PENDING_TWO_REAL_EXTERNAL_REVIEWERS")
        self.assertFalse(packet["has_authenticated_human_review"])
        self.assertEqual(len(packet["cases"]),2)
        self.assertEqual({c["method_id"] for c in packet["cases"]},
                         {"classic-xiyou-001-cave-pledge",
                          "classic-xiyou-001-woodcutter"})
        for c in packet["cases"]:
            self.assertEqual(c["source_raw_sha256"],RAW_SHA256)
            self.assertEqual(c["source_chapter_sha256"],FIRST_CHAPTER_SHA256)
            self.assertEqual(c["source_locator"]["chapter"],1)
            self.assertTrue(c["source_anchor"] in c["short_review_excerpt_only"])
            self.assertIsNone(c["signed_rights_authorization"])
            self.assertIsNone(c["signed_craft_approval"])
            self.assertFalse(c["production_admission"])
        guide=(dest/"REVIEW_GUIDE.md").read_text("utf8")
        self.assertIn(PINNED_URL,guide)
        self.assertIn("不可自动审批",guide)
        with sqlite3.connect(db) as con:
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM studied_chapters"
            ).fetchone()[0],1)
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM xuehai_method_cards"
            ).fetchone()[0],2)
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM xuehai_method_attestations"
            ).fetchone()[0],0)
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM snapshots WHERE status='staging'"
            ).fetchone()[0],1)
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM snapshots WHERE status='published'"
            ).fetchone()[0],1)
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM accepted_prose"
            ).fetchone()[0],0)
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM xuehai_method_cards WHERE rights_status='RIGHTS_VERIFIED'"
            ).fetchone()[0],0)
        with self.assertRaises(FileExistsError):
            stage_pinned_first_chapter(source,db,dest)


if __name__=="__main__":
    unittest.main()
