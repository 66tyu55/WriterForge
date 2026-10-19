"""V78 source-prefix trials are exact and do not pretend to read whole chapters."""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
from tempfile import TemporaryDirectory
import unittest

from writerforge.wf_b01_prefix_prepare import (
    review_first_chapter_windows,WFPrefixReviewError,_split_into_ordered_units,
)

class V78PrefixOnlyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.path=Path(self.tmp.name)/"synthetic.txt"
    def tearDown(self):
        self.tmp.cleanup()
    def trial(self,*,codec="utf8",second="第2章",unit_count=3):
        first=("第1章 几个疑问\n"+
               "\n山风吹过远方的城门，谁都不知道发生了什么。\n"*125+
               "一名旅人看见天空突然变暗，他开始思考未知的原因。\n"*65)
        other=(second+" 另一段情节\n"+
               "月光落在屋顶上，一个陌生人正在等待新的事件。\n"*65)
        raw=(first+other).encode(codec)
        self.path.write_bytes(raw)
        chosen,receipt=review_first_chapter_windows(
            self.path,
            source_sha256=sha256(raw).hexdigest(),
            source_bytes=len(raw),
            source_key_sha256="a"*64,
            unit_count=unit_count)
        return first,chosen,receipt,raw

    def test_utf8_contiguous_opening_and_no_literary_claim(self):
        full,units,proof,raw=self.trial()
        chapter=full.split("\n",1)[1]
        self.assertEqual(len(units),3)
        self.assertTrue(chapter.startswith("".join(units)))
        self.assertEqual(proof["small_trial_units"],3)
        self.assertFalse(proof["chapter_coverage_is_100_percent"])
        self.assertFalse(proof["source_edition_human_confirmed"])
        self.assertEqual(proof["chapters_claimed_fully_read"],0)
        self.assertEqual(proof["deepseek_model_requests"],0)
        self.assertGreater(proof["whole_chapter_unit_count"],3)
        self.assertNotIn("山风吹过",str(proof))
        self.assertEqual(self.path.read_bytes(),raw)

    def test_same_source_gbk_gb18030_exact_prefix(self):
        full,units,report,raw=self.trial(codec="gb18030")
        self.assertIn("gb18030",report["charset_variants_identical"])
        self.assertIn("gbk",report["charset_variants_identical"])
        self.assertEqual(len(units),3)
        self.assertTrue(full.split("\n",1)[1].startswith("".join(units)))
        self.assertEqual(sha256(raw).hexdigest(),report["source_sha256"])
        self.assertEqual(report["r2_learn_events_written"],0)

    def test_different_source_hash_rejected_before_unit_selection(self):
        full,units,report,raw=self.trial()
        with self.assertRaisesRegex(Exception,"SOURCE_SHA_MISMATCH"):
            review_first_chapter_windows(
                self.path,source_sha256="0"*64,
                source_bytes=len(raw),source_key_sha256="a"*64)

    def test_chapter_number_gap_blocks_partial_trial(self):
        with self.assertRaisesRegex(WFPrefixReviewError,
                                    "STRUCTURE_NOT_AGREED"):
            self.trial(second="第3章")

    def test_all_units_reconstruct_full_original_chapter(self):
        txt=("少年在树林里听到声音，不知道还有谁在靠近。\n"*40+
             "\n\n"+
             "另一名旅人走进城门后，继续观察远处的路。\n"*40)
        pieces=_split_into_ordered_units(txt)
        self.assertEqual("".join(pieces),txt)
        self.assertGreaterEqual(len(pieces),4)
        self.assertTrue(all(30<=len(p)<=900 for p in pieces))

if __name__=="__main__":
    unittest.main()
