"""Source-free checks: each xianxia time dimension has a meaning and provenance."""
from __future__ import annotations
from tempfile import TemporaryDirectory
from pathlib import Path
from fractions import Fraction
import sys, unittest

SCRIPTS=Path(__file__).resolve().parents[1]/".agents/skills/xianxia-time-rule/scripts"
sys.path.insert(0,str(SCRIPTS))
import time_parameters_v3 as v3

def corpus(text,encoding="utf-8"):
    root=TemporaryDirectory()
    path=Path(root.name)/"fiction.txt"
    path.write_bytes(text.encode(encoding))
    return root,path

class XianxiaTimeV3SourceTests(unittest.TestCase):
    def test_explicit_independent_temporal_parameters(self):
        want={"narrative_revelation","world_elapsed","story_relative_order",
              "actor_subjective_elapsed","actor_biological_age",
              "lifespan_ceiling","cultivation_exposure",
              "cultivation_efficiency","local_time_rate",
              "frame_access_schedule","actor_biological_aging_rate",
              "advancement_condition","travel_elapsed",
              "waiting_deadline","recurrence_period","historical_era",
              "parallel_offscreen_time","uncertainty"}
        self.assertEqual(set(v3.DOMAINS),want)

    def test_exact_number_or_unknown_never_mystery_floats(self):
        self.assertEqual(v3.chinese_exact("一百二十"),Fraction(120))
        self.assertEqual(v3.chinese_exact("二十三"),Fraction(23))
        self.assertEqual(v3.chinese_exact("半"),Fraction(1,2))
        self.assertEqual(v3.chinese_exact("十"),Fraction(10))
        self.assertIsNone(v3.chinese_exact("十七八"))
        self.assertIsNone(v3.chinese_exact("三五"))
        self.assertIsNone(v3.chinese_exact("数十"))
        self.assertEqual(v3.qualified_quantity("数十","年")[0],None)
        self.assertEqual(v3.qualified_quantity("约三","年")[0],None)
        self.assertEqual(v3.qualified_quantity("十七八","岁")[0],None)
        self.assertEqual(v3.qualified_quantity("三","年"),("3","EXACT"))

    def test_efficiency_comparison_does_not_infer_time_dilation(self):
        text=("作者附注：大约两百年以前的事情不属于正文。\n"
              "第一章 开始\n"
              "三日修炼的效果抵得上外界半年的苦修。\n")
        tmp,path=corpus(text,"utf-8")
        try:
            result=v3.scan(path)
            self.assertEqual(result["summary"]["unreviewed_semantic_candidates"],
                             len(result["candidates"]))
            self.assertTrue(result["source_spans_byte_verified"])
            rows=[x for x in result["candidates"]
                  if "cultivation_efficiency" in x["candidate_parameter_ids"]]
            self.assertGreaterEqual(len(rows),2)
            self.assertTrue(all(x["time_rate_inference_status"]==
                    "EFFICIENCY_IS_NOT_TIME_DILATION" for x in rows))
            self.assertFalse(any("source_surface_PRIVATE" in x
                                 for x in result["candidates"]))
            self.assertNotIn("两百",str(result["candidates"]))
        finally:tmp.cleanup()

    def test_frontmatter_stripped_and_nonnumeric_era_concurrent_found(self):
        text=("说明：作者用五十年写作但这是章前材料。\n"
              "第一卷 前尘 第1章 路边\n"
              "他到了玄鉴元年，随后与另一边的同伴同时行动。\n"
              "与此同时，村中百姓照常生活。\n")
        tmp,path=corpus(text,"gb18030")
        try:
            result=v3.scan(path)
            labels={lab for row in result["candidates"]
                    for lab in row["candidate_parameter_ids"]}
            self.assertIn("historical_era",labels)
            self.assertIn("story_relative_order",labels)
            self.assertIn("parallel_offscreen_time",labels)
            self.assertFalse(any(x["source_char_start"]<
                             result["story_start_char_offset"] for x in result["candidates"]))
        finally:tmp.cleanup()

    def test_negated_dilation_is_not_positive_multiplier(self):
        text=("第一章 旧镜\n"
              "镜中并无什么不同寻常的时间流速。他只是闭关三年。\n")
        tmp,path=corpus(text,"utf-8")
        try:
            result=v3.scan(path)
            hits=[x for x in result["candidates"] if
                  "local_time_rate" in x["candidate_parameter_ids"]]
            self.assertTrue(hits)
            self.assertTrue(any(x["time_rate_inference_status"]==
                      "NEGATED_UNUSUAL_RATE" for x in hits))
            self.assertTrue(all(x["explicit_quantity"] is None for x in hits))
        finally:tmp.cleanup()

    def test_age_lifespan_not_same_as_lived_history(self):
        text=("第一章 时光\n"
              "村落传承两百年。老人今年十七八岁，寿数一百二十载。\n"
              "十年一届的山门集会，路程约三日。\n")
        tmp,path=corpus(text,"gb18030")
        try:
            result=v3.scan(path)
            self.assertTrue(any("lifespan_ceiling" in row["candidate_parameter_ids"]
                                for row in result["candidates"]))
            self.assertTrue(any("recurrence_period" in row["candidate_parameter_ids"]
                                for row in result["candidates"]))
            approx=[x for x in result["candidates"] if
                    x["quantity_status"]!="EXACT" and
                    x["unit"] in ("age_year","day")]
            self.assertTrue(approx)
        finally:tmp.cleanup()

    def test_evidence_character_byte_offsets_survive_both_codecs(self):
        for encoding in ("gb18030","utf-8"):
            with self.subTest(encoding=encoding):
                text="书前简介写了十年。\n第一章 初试\n一个时辰后，他走出山门。\n"
                tmp,path=corpus(text,encoding)
                try:
                    result=v3.scan(path,include_private_context=True)
                    raw=path.read_bytes()
                    for row in result["candidates"]:
                        surface=row["source_surface_PRIVATE"]
                        begin,end=row["source_byte_start"],row["source_byte_end"]
                        self.assertEqual(raw[begin:end],surface.encode(encoding))
                    self.assertTrue(result["source_spans_byte_verified"])
                finally:tmp.cleanup()

if __name__=="__main__":unittest.main()
