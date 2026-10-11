"""Synthetic-only tests: no modern copyrighted novel is part of this repo."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import tracemalloc
import unittest

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.modern_source import (
    MAX_MODERN_SOURCE_BYTES, _chapters, _encoding, inspect_modern_source,
    study_modern_source,
)
from writerforge.source_study import StudyError


def write_fake_novel(path: Path, *, chapters=3, codec="utf-8",
                     long_body=False, omit=None, duplicate=None):
    with path.open("w", encoding=codec, newline="\n") as file:
        file.write("《凡人修仙传》 合成测试资料，不是真实小说\n作者：忘语\n")
        for n in range(1, chapters + 1):
            if n == omit:
                continue
            file.write(f"第{n}章 山中修炼\n")
            if long_body:
                file.write("韩立练气，" * 450 + "\n")
            else:
                file.write("韩立望着院中旧屋，想起山脚下少年时的种种往事。\n" * 8)
            if n == duplicate:
                file.write(f"第{n}章 错误的重复章节\n")
                file.write("韩立练气。\n" * 40)


class ModernSourceStreamingTests(unittest.TestCase):
    def test_small_utf8_source_ingests_transactionally_and_is_idempotent(self):
        with TemporaryDirectory() as tmp:
            text = Path(tmp) / "novel.txt"
            write_fake_novel(text)
            db = WriterForgeDB(Path(tmp) / "study.sqlite3")
            rt = RuntimeEngine()
            rt.enter_learn()
            options = dict(
                work_id="fanrenxiuxian-private-original",
                title="凡人修仙传", protagonist="韩立",
                genre="仙侠", source_uri="private-synthetic-test",
                min_chapters=3, max_chapters=3, min_bytes=1,
            )
            first = study_modern_source(text, db, rt, **options)
            self.assertEqual(first["newly_studied"], 3)
            self.assertEqual(first["studied_chapters"], 3)
            self.assertTrue(first["structure_complete"])
            self.assertFalse(first["literary_learning_verified"])
            self.assertFalse(first["model_training_performed"])
            self.assertGreater(first["studied_units"], 0)
            self.assertEqual(first["source_chapters"], 3)
            self.assertEqual(
                db.conn.execute("SELECT COUNT(*) FROM snapshots WHERE status='published'").fetchone()[0],3)
            second = study_modern_source(text, db, rt, **options)
            self.assertEqual(second["newly_studied"], 0)
            self.assertEqual(second["studied_chapters"], 3)
            self.assertEqual(
                db.conn.execute("SELECT COUNT(*) FROM studied_chapters").fetchone()[0],3)
            self.assertEqual(db.conn.execute("PRAGMA quick_check").fetchone()[0], "ok")
            db.close()

    def test_gb18030_original_can_be_streamed(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "gb18030.txt"
            write_fake_novel(path, chapters=3, codec="gb18030")
            info = inspect_modern_source(
                path, title="凡人修仙传", protagonist="韩立",
                min_chapters=3, max_chapters=3)
            self.assertEqual(info["encoding"], "gb18030")
            self.assertEqual(info["chapters"], 3)

    def test_missing_or_duplicate_chapter_is_rejected(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.txt"
            write_fake_novel(path, chapters=4, omit=3)
            with self.assertRaisesRegex(StudyError, "order malformed"):
                inspect_modern_source(
                    path, title="凡人修仙传", protagonist="韩立", min_chapters=3)
            write_fake_novel(path, chapters=4, duplicate=3)
            with self.assertRaisesRegex(StudyError, "order malformed"):
                inspect_modern_source(
                    path, title="凡人修仙传", protagonist="韩立", min_chapters=3)

    def test_hash_mismatch_rejected_before_any_db_write(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "novel.txt"
            write_fake_novel(path)
            with self.assertRaisesRegex(StudyError, "SHA256 differs"):
                inspect_modern_source(
                    path, title="凡人修仙传", protagonist="韩立",
                    min_chapters=3, expected_sha256="0" * 64)

    def test_15_mib_source_stays_bounded_in_memory(self):
        # Full fake novel is GENERATED INSIDE CI and never uploaded to R2.
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic-large.txt"
            write_fake_novel(path, chapters=2400, long_body=True)
            self.assertGreater(path.stat().st_size, 8 * 1024 * 1024)
            self.assertLess(path.stat().st_size, MAX_MODERN_SOURCE_BYTES)
            tracemalloc.start()
            try:
                result = inspect_modern_source(
                    path, title="凡人修仙传", protagonist="韩立",
                    min_chapters=2200, max_chapters=3200,
                    min_bytes=10 * 1024 * 1024,
                )
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertEqual(result["chapters"], 2400)
            self.assertLess(peak, 8 * 1024 * 1024,
                            "modern preflight must not keep the entire novel in RAM")


if __name__ == "__main__":
    unittest.main()
