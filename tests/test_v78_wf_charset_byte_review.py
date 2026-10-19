"""V78 whole-source byte/charset comparison (synthetic fiction only)."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge.wf_charset_byte_review import (
   CODECS,WFCharsetReviewError,byte_charset_audit,
)


class V78WholeFileCharsetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.path=Path(self.tmp.name)/"fiction.txt"
    def tearDown(self):
        self.tmp.cleanup()
    def analyze(self,raw):
        self.path.write_bytes(raw)
        return byte_charset_audit(
            self.path,expected_source_sha256=sha256(raw).hexdigest(),
            expected_size=len(raw),expected_key_sha256="a"*64)

    def test_one_utf8_reading_aliases_and_no_original_text_leak(self):
        story=("第一章 山中雨\n"
               "山风吹过高楼，少女听见远方传来钟声，心里有了新的疑问。\n"*200)
        raw=story.encode("utf8")
        report=self.analyze(raw)
        self.assertEqual(report["plausible_distinct_decoded_texts"],1)
        self.assertEqual(report["status"],
                         "WF_CHARSET_ONE_REVERSIBLE_TEXT_READING")
        self.assertIn("utf-8",report["unique_reading_codec_aliases"])
        self.assertIn("utf-8-sig",report["unique_reading_codec_aliases"])
        self.assertFalse(report["source_edition_human_confirmed"])
        self.assertFalse(report["does_not_auto_unlock_frozen_B00_training_gate"] is False)
        self.assertTrue(report["does_not_auto_unlock_frozen_B00_training_gate"])
        self.assertNotIn("少女听见",str(report))
        self.assertEqual(raw,self.path.read_bytes())

    def test_gb18030_and_gbk_may_be_same_exact_decoded_string(self):
        story=("第一章 雨后的城\n"+
               "远处传来钟声，山风吹过庭院，那个人心里感到疑惑。\n"*220+
               "第二章 清晨\n"+
               "有人在门前等待，少女不知道另一个人为什么没有来。\n"*220)
        raw=story.encode("gb18030")
        result=self.analyze(raw)
        self.assertTrue(result["results"]["gb18030"]["strict_full_decode"])
        self.assertTrue(result["results"]["gb18030"]["byte_roundtrip"])
        self.assertTrue(result["results"]["gbk"]["byte_roundtrip"])
        self.assertEqual(
          result["results"]["gb18030"]["decoded_text_sha256"],
          result["results"]["gbk"]["decoded_text_sha256"])
        self.assertFalse(result["source_encoding_human_confirmed"])
        self.assertEqual(raw,self.path.read_bytes())

    def test_utf8_bom_remains_byte_identical_and_rare_controls_rejected(self):
        s=("第一章 流水\n"+"山里的人听到雨声，还在观察天空。\n"*120)
        raw=b"\xef\xbb\xbf"+s.encode("utf8")
        result=self.analyze(raw)
        self.assertTrue(result["results"]["utf-8-sig"]["strict_full_decode"])
        self.assertTrue(result["results"]["utf-8-sig"]["byte_roundtrip"])
        self.assertEqual(result["results"]["utf-8"]["controls_or_unassigned"],1)
        self.assertEqual(raw,self.path.read_bytes())

    def test_legacy_traditional_chinese_never_claims_literary_truth(self):
        s=("第一章 舊城\n"+"遠處傳來鐘聲，心裡有疑問，這是一個關於人的故事。\n"*170)
        raw=s.encode("big5")
        result=self.analyze(raw)
        self.assertTrue(result["results"]["big5"]["byte_roundtrip"])
        self.assertFalse(result["human_reading_quality_assessed"])
        self.assertFalse(result["literary_genre_inferred"])
        self.assertFalse(result["chapter_authorship_verified"])
        self.assertFalse(result["source_edition_human_confirmed"])

    def test_binary_or_control_bytes_never_claim_success(self):
        raw=b"\x00\x01\x02"*1000
        result=self.analyze(raw)
        self.assertEqual(result["plausible_distinct_decoded_texts"],0)
        self.assertEqual(result["status"],
                         "WF_CHARSET_NO_STRICT_PLAUSIBLE_DECODING")
        self.assertFalse(result["results"]["utf-8"]["technically_plausible"])

    def test_source_sha_mutation_fails_closed(self):
        raw=("第一章 山河\n"+"一个人走向城门，突然听见声音。\n"*130).encode("utf8")
        self.path.write_bytes(raw)
        with self.assertRaisesRegex(WFCharsetReviewError,"SOURCE_SHA_MISMATCH"):
            byte_charset_audit(
              self.path,expected_source_sha256="0"*64,
              expected_size=len(raw))

    def test_truncated_size_refused(self):
        raw=b"x"*2500
        self.path.write_bytes(raw)
        with self.assertRaisesRegex(WFCharsetReviewError,"SOURCE_NOT_BOUNDED"):
            byte_charset_audit(self.path,
                expected_source_sha256=sha256(raw).hexdigest(),
                expected_size=len(raw)+1)

    def test_byte_review_does_not_mutate_original_text(self):
        s=("第一章 迷雾\n"+"说话的人走在桥上，谁都不知道怎么回事。\n"*170)
        raw=s.encode("gb18030")
        self.analyze(raw)
        self.assertEqual(self.path.read_bytes(),raw)

if __name__=="__main__":
    unittest.main()
