"""Offline regressions for pinned private-R2 modern-work transfer runner."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.learn_archived_modern_r2 import (
    WORKS, DIAGNOSTIC_HEAD, heading_audit,
)

class ModernArchiveContinuationTests(unittest.TestCase):
    def test_only_already_archived_editions_are_eligible(self):
        self.assertEqual(set(WORKS),
                         {"fanrenxiuxian", "doupo", "wudongqiankun", "wanmeishijie", "zhetian", "manghuangji", "qiumo"})
        self.assertEqual(len({w.source_sha256 for w in WORKS.values()}), 7)
        for spec in WORKS.values():
            self.assertEqual(len(spec.source_sha256), 64)
            self.assertGreater(spec.source_bytes, 8_000_000)
            self.assertGreater(spec.min_chapters, 500)

    def test_heading_probe_does_not_accept_prose(self):
        self.assertIsNotNone(DIAGNOSTIC_HEAD.fullmatch("第一章 开篇"))
        self.assertIsNotNone(DIAGNOSTIC_HEAD.fullmatch("正文 第2章：序幕"))
        self.assertIsNone(DIAGNOSTIC_HEAD.fullmatch("他在第2章做过这样的事。"))
        self.assertIsNone(DIAGNOSTIC_HEAD.fullmatch("前言 第一章 序幕"))

    def test_probe_reports_bounded_sequence_breaks_without_source_text(self):
        with TemporaryDirectory() as t:
            path = Path(t) / "synthetic.txt"
            path.write_text("测试\n第一章 开端\n原文仅为测试\n第二章 变化\n第四章 结尾\n",
                            encoding="utf-8")
            summary = heading_audit(path)
        self.assertEqual(summary["heading_matches_not_verified_chapter_count"], 3)
        self.assertEqual(summary["first_ordinal"], 1)
        self.assertEqual(summary["last_ordinal"], 4)
        self.assertEqual(summary["sequence_anomaly_sample"],
                         [{"heading_index": 3, "previous": 2, "current": 4}])

if __name__ == "__main__":
    unittest.main()
