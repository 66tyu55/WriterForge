"""V87.1 raw passage fallback: deterministic and no future-content leakage."""
from __future__ import annotations
from hashlib import sha256
import json
import unittest

from writerforge.v87_contiguous_passage import (
    choose_passage, WF87PassageError,
)

def h(s):
    return sha256(s.encode("utf8")).hexdigest()

class V87PassageTests(unittest.TestCase):
    def test_frozen_offset_same_source_produces_identical_receipt(self):
        novel=("晨雾涌进山门，守夜人发现古井水位忽然下降。"
               "村人说旧桥已经封锁，少年决定追问守桥人的来历。"
               "山林之间突然传来钟声，几个行人停住脚步。")*100
        a=choose_passage(novel,key_sha256=h("work"),
                         source_sha256=h(novel))
        b=choose_passage(novel,key_sha256=h("work"),
                         source_sha256=h(novel))
        self.assertEqual(a,b)
        self.assertEqual(a["fragment_end_char"]-a["fragment_start_char"],2300)
        self.assertEqual(len(a["first_read_visible_unit_sha256"]),2)
        self.assertGreaterEqual(a["fragment_unit_count"],4)
        self.assertFalse(a["precise_chapter_identity_verified"])
        serialized=json.dumps(a,ensure_ascii=False)
        self.assertNotIn("晨雾涌进山门",serialized)
        self.assertNotIn("山林之间突然传来钟声",serialized)

    def test_too_short_source_is_rejected(self):
        with self.assertRaisesRegex(WF87PassageError,"SOURCE_NOT_VERIFIED"):
            choose_passage("晨雾涌进山门。"*50,
                           key_sha256=h("book"),source_sha256=h("source"))

if __name__=="__main__":
    unittest.main()
