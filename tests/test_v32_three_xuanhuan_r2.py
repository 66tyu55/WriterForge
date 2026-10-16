"""Synthetic-only tests: no private or copyrighted full novels in this repo."""
from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import scripts.archive_three_xuanhuan_r2 as arch
from writerforge.r2_storage import R2Config
from writerforge.single_work_runner import SingleWorkVault


class Missing(Exception):
    response = {"Error": {"Code": "404"}}


class FakeR2:
    def __init__(self):
        self.objects = {}
        self.upload_count = 0
    def head_object(self, *, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise Missing()
        raw, metadata = self.objects[(Bucket, Key)]
        return {"ContentLength": len(raw), "Metadata": metadata}
    def put_object(self, *, Bucket, Key, Body, ContentType=None, Metadata=None):
        self.objects[(Bucket, Key)] = (bytes(Body), dict(Metadata or {}))
    def upload_file(self, path, bucket, key, ExtraArgs=None, Config=None):
        self.upload_count += 1
        self.objects[(bucket, key)] = (
            Path(path).read_bytes(),
            dict((ExtraArgs or {}).get("Metadata", {})),
        )
    def get_object(self, *, Bucket, Key):
        return {"Body": BytesIO(self.objects[(Bucket, Key)][0])}
    def download_file(self, bucket, key, path):
        Path(path).write_bytes(self.objects[(bucket, key)][0])
    def list_objects_v2(self, *, Bucket, Prefix, MaxKeys):
        rows = [
            {"Key": key, "Size": len(raw)}
            for (bucket, key), (raw, _) in self.objects.items()
            if bucket == Bucket and key.startswith(Prefix)
        ]
        return {"Contents": rows[:MaxKeys], "IsTruncated": len(rows) > MaxKeys}


class ThreeNovelSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.source = Path(self.tmp.name) / "source.txt"
        self.raw = ("斗破苍穹, 萧炎\n" + "第一章 合成演练\n"
                    + "萧炎从屋中走到院里，这不是实际原著。\n" * 40).encode("utf-8")
        self.source.write_bytes(self.raw)
        self.fixture = replace(arch.SOURCES["doupo"],
                               expected_bytes=len(self.raw),
                               min_bytes=1, max_bytes=len(self.raw) + 10,
                               min_heading_occurrences=1,
                               pinned_sha256=sha256(self.raw).hexdigest())
        self.config = R2Config(account_id="a"*32,
                               bucket="writerforge-private-library",
                               access_key_id="fake-id",
                               secret_access_key="fake-secret")
        self.fake = FakeR2()
        self.vault = SingleWorkVault(self.config,work_id="doupo",client=self.fake)

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_sources_independently_named_and_bounded(self):
        self.assertEqual(set(arch.SOURCES),
                         {"doupo", "wudongqiankun", "wanmeishijie"})
        self.assertEqual(len(set(n.source_url for n in arch.SOURCES.values())), 3)
        self.assertTrue(all(n.max_bytes <= arch.MAX_BYTES
                            for n in arch.SOURCES.values()))
        self.assertEqual(len(arch.SOURCES["doupo"].pinned_sha256),64)
        self.assertEqual(len(arch.SOURCES["wudongqiankun"].pinned_sha256),64)

    def test_synthetic_book_upload_fresh_restore_and_resume(self):
        evidence = arch.verify_source(self.fixture, self.source)
        self.assertEqual(evidence["source_sha256"],sha256(self.raw).hexdigest())
        stored = arch.store_verified_source(self.vault,self.fixture,self.source,evidence)
        self.assertTrue(stored["new_private_archive"])
        self.assertTrue(stored["fresh_roundtrip"])
        self.assertEqual(self.fake.upload_count,1)
        again = arch.store_verified_source(self.vault,self.fixture,self.source,evidence)
        self.assertFalse(again["new_private_archive"])
        self.assertFalse(again["uploaded_new_blob"])
        self.assertEqual(self.fake.upload_count,1)

    def test_pin_mismatch_blocks_before_storage(self):
        wrong = replace(self.fixture,pinned_sha256="f"*64)
        with self.assertRaisesRegex(arch.OriginalSourceError,"PINNED_SOURCE_SHA256_CHANGED"):
            arch.verify_source(wrong,self.source)
        self.assertEqual(self.fake.upload_count,0)

    def test_short_or_wrong_book_rejected(self):
        with self.assertRaisesRegex(arch.OriginalSourceError,"SOURCE_SIZE_OUT_OF_RANGE"):
            arch.verify_source(replace(self.fixture,min_bytes=100_000),self.source)
        self.source.write_text("<!doctype html>error",encoding="utf-8")
        with self.assertRaises(arch.OriginalSourceError):
            arch.verify_source(replace(self.fixture,expected_bytes=None,
                                       pinned_sha256=None,min_bytes=1),self.source)

    def test_wrong_bucket_or_work_stops(self):
        evidence=arch.verify_source(self.fixture,self.source)
        wrong=SingleWorkVault(
            self.config,work_id="wudongqiankun",client=self.fake)
        with self.assertRaisesRegex(arch.OriginalSourceError,"WRONG_WORK_OR_PRIVATE_R2_BUCKET"):
            arch.store_verified_source(wrong,self.fixture,self.source,evidence)


if __name__ == "__main__":
    unittest.main()
