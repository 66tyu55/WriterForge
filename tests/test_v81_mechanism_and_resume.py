"""V81 strict model mechanism-schema and paid-resume tests (no real calls)."""
from __future__ import annotations
import json
from hashlib import sha256
from pathlib import Path
import unittest

from writerforge.v81_mechanism_normalizer import (
    normalize_mechanisms,WFMechanismFormatError,
)

SOURCE=("a"*64,"b"*64,"c"*64)

class ProvenanceSafeNormalizationTests(unittest.TestCase):
    def test_old_exact_list_keeps_claim_but_computes_source_sha(self):
        claims={"mechanisms":[{
            "unit":2,"mechanism":"信息延迟",
            "reader_effect":"制造未知感","uncertainty":"缺少独立读者证明",
        }],"summary":"额外自由元数据不能变成文学证据"}
        out,audit=normalize_mechanisms(claims,SOURCE)
        self.assertEqual(out[0]["evidence_unit_sha256"],SOURCE[1])
        self.assertEqual(out[0]["mechanism"],"信息延迟")
        self.assertTrue(audit["model_source_hash_never_trusted"])
    def test_nested_dict_chinese_keys_and_numbered_unit(self):
        value={"analysis":{"techniques":{"3":{
            "叙事手法":"视角遮蔽","读者效果":"信息差造成疑问",
            "不确定性":"不确定是否为作者刻意",
        }}}}
        items,a=normalize_mechanisms(value,SOURCE)
        self.assertEqual(items[0]["unit"],3)
        self.assertEqual(items[0]["evidence_unit_sha256"],SOURCE[2])
        self.assertEqual(items[0]["mechanism"],"视角遮蔽")
    def test_json_string_list_with_real_fields(self):
        raw={"mechanisms":json.dumps([{
             "unit_no":"1","technique":"感官对比",
             "effect":"加剧紧张",
             "limitations":"不能独立断言人类阅读效果"
        }],ensure_ascii=False)}
        lines,a=normalize_mechanisms(raw,SOURCE)
        self.assertEqual(lines[0]["unit"],1)
        self.assertEqual(lines[0]["mechanism"],"感官对比")
    def test_long_list_bounded_without_faking_missing_six(self):
        raw={"mechanisms":[{
           "unit":1,"mechanism":"悬念",
           "reader_effect":"好奇","uncertainty":"猜测"
        } for _ in range(8)]}
        result,a=normalize_mechanisms(raw,SOURCE)
        self.assertEqual(len(result),6)
        self.assertEqual(a["additional_model_mechanisms_not_persisted"],2)
    def test_mismatched_hash_refuses_to_fabricate_source(self):
        raw={"mechanisms":[{
           "unit":1,"evidence_unit_sha256":"z"*64,
           "mechanism":"假说","reader_effect":"效果","uncertainty":"未知"
        }]}
        with self.assertRaisesRegex(WFMechanismFormatError,"FABRICATED"):
            normalize_mechanisms(raw,SOURCE)
    def test_missing_explicit_unit_must_not_be_invented(self):
        raw={"mechanisms":[{
           "mechanism":"声音","reader_effect":"疑问","uncertainty":"未知"
        }]}
        with self.assertRaisesRegex(WFMechanismFormatError,"POSITION"):
            normalize_mechanisms(raw,SOURCE)
    def test_free_text_cannot_be_promoted_to_source_evidence(self):
        with self.assertRaisesRegex(WFMechanismFormatError,"FREE_TEXT"):
            normalize_mechanisms({"mechanisms":"写得不错，很有文学性"},SOURCE)
    def test_resume_references_exact_real_chapter7_and_chapter8_snapshots(self):
        repo=Path(__file__).resolve().parents[1]
        src=(repo/"wf_railway_v81_resume_ch8_12.py").read_text(encoding="utf8")
        compile(src,"wf_railway_v81_resume_ch8_12.py","exec")
        self.assertIn("calls_reserved=22",src)
        self.assertIn("prompt_tokens_reported=19876",src)
        self.assertIn("completion_tokens_reported=6471",src)
        self.assertIn("conservative_tokens_committed=26347",src)
        self.assertIn("chapters[7:12]",src)
        self.assertIn("PRIOR_CHAPTER7_EXPERIENCE_SHA",src)
        self.assertIn("2dcaaa908ca2a5bb3175377cd146870e798d3cc9959631c9264ac9cb846d5eb8",src)
        self.assertNotIn('max_total_tokens=4800',src)

if __name__=="__main__":
    unittest.main()
