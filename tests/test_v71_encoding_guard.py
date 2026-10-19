"""V71 strict text decoding regressions; synthetic files only."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from writerforge.bulk_inbox import BulkCatalog
from writerforge.source_encoding_guard import (
    detect_decoding_for_index,SourceEncodingError,
)

class V71EncodingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def source(self,raw):
        path=self.root/"sample.txt"
        path.write_bytes(raw)
        return path

    def test_bom_utf8_is_detected_without_stripping_original(self):
        raw=b"\xef\xbb\xbf"+("第一章 天边的风云。\n"*200).encode("utf8")
        f=self.source(raw)
        result=detect_decoding_for_index(f)
        self.assertEqual(result["encoding"],"utf-8-sig")
        self.assertFalse(result["provisional_legacy_decoding"])
        self.assertEqual(f.read_bytes(),raw)

    def test_utf16_bom_is_accepted_as_strict_encoding(self):
        raw=("第一章 天边的风云。\n"*200).encode("utf-16")
        result=detect_decoding_for_index(self.source(raw))
        self.assertEqual(result["encoding"],"utf-16")
        self.assertFalse(result["provisional_legacy_decoding"])

    def test_gb18030_is_provisional_and_still_indexable(self):
        plain=("第1章 风雪\n"
               "山风渐渐紧了起来，远处突然响起雷声。\n"*400)
        raw=plain.encode("gb18030")
        file=self.source(raw)
        result=detect_decoding_for_index(file)
        self.assertEqual(result["encoding"],"gb18030")
        self.assertTrue(result["provisional_legacy_decoding"])
        self.assertFalse(result["source_edition_human_verified"])
        self.assertNotIn("远处",str(result))
        catalog=BulkCatalog(self.root/"cat.sqlite3")
        key="writerforge/v1/private-reading/历史/某部作品/正文.txt"
        try:
            catalog.register([{"key":key,"size":len(raw),"etag":None}])
            out=catalog.index_text_file(
                key,file,self.root/"sql",encoding=result["encoding"])
            self.assertGreater(out["units_indexed"],100)
            self.assertEqual(out["encoding"],"gb18030")
            self.assertEqual(file.read_bytes(),raw)
        finally:
            catalog.close()

    def test_binary_control_bytes_refused(self):
        file=self.source(b"\x00"*4096)
        with self.assertRaisesRegex(SourceEncodingError,"BINARY_OR_CONTROL"):
            detect_decoding_for_index(file)

    def test_invalid_legacy_bytes_fail_closed(self):
        file=self.source(b"\xff"*4096)
        with self.assertRaises(SourceEncodingError):
            detect_decoding_for_index(file)

    def test_strict_utf8_sample_does_not_claim_literary_truth(self):
        f=self.source(("少女看向远方，听见钟声。\n"*240).encode("utf8"))
        status=detect_decoding_for_index(f)
        self.assertEqual(status["encoding"],"utf-8")
        self.assertFalse(status["provisional_legacy_decoding"])
        self.assertNotIn("钟声",str(status))

if __name__=="__main__":
    unittest.main()
