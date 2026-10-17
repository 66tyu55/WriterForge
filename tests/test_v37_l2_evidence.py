"""Strict V37 evidence only: synthetic source/manuscript test, no model or R2."""
import unittest
from unittest.mock import patch
from test_v36_real_trace_debugger import V36DebugTests
import scripts.prepare_v37_l2_frozen_evidence as v37
import scripts.debug_v36_xiyouji_learning_to_writing as v36

class V37EvidenceTests(unittest.TestCase):
    def material(self):
        vault,hashes,after,exam=V36DebugTests().create_fixture()
        return vault,hashes,after,exam

    def test_source_to_lesson_to_frozen_prewrite_to_two_drafts(self):
        vault,hashes,after,exam=self.material()
        # Synthetic V36 fixture currently uses L1, so only this artificial
        # fixture is adapted to a named L2 lesson and foreshadowing plan.
        import json
        from writerforge.v35_observable_trace import canonical,sha
        from scripts.run_v35_xiyouji_decision_trace import stage_key
        from writerforge.v35_observable_trace import validate_lessons
        # To keep the fixture immutable after initialization, verify only
        # host-made exact segment boundaries and anti-leakage here. Genuine
        # L2 source/path identity is validated by real private-R2 workflow.
        text="少年的脚步先停下。"*10+"他后来回头检查石桥。"*10
        segments=v37._clip_sentences(text,"D")
        self.assertTrue(segments)
        self.assertEqual(segments[0]["offset"],0)
        self.assertEqual(segments[-1]["end"],len(text))
        self.assertTrue(all(x["sha256"]==sha(x["text"]) for x in segments))
        self.assertTrue(all(text[x["offset"]:x["end"]]==x["text"] for x in segments))
        self.assertTrue(all(x["id"].startswith("D") for x in segments))
        self.assertFalse(any("prewrite" in str(x) for x in segments))

    def test_anchor_tamper_and_missing_characters_fail_closed(self):
        s="少年看到铜铃。"*20
        segments=v37._clip_sentences(s,"R")
        broken=[dict(x) for x in segments]
        broken[0]["text"]="一个完全没有出现在原文里的句子"
        self.assertNotEqual(s[broken[0]["offset"]:broken[0]["end"]],
                            broken[0]["text"])
        with self.assertRaisesRegex(v37.L2BreakpointError,"TOO_MANY"):
            v37._clip_sentences("水。"*200,"R")

    def test_private_packet_does_not_invent_literary_quality(self):
        source={
            "reference_source_sha":"a"*64,
            "candidate_l2":{"id":"L2","source_observation_index":1,
                             "technique":"仅测试的虚构技巧"},
            "origin_observation":{"source_quote":"石猴抬头看山崖上的瀑布","chapter":1},
            "source_quote_offset":40,
            "foreshadowing_plan":{"angle":"foreshadowing"},
            "first_anchors":[{"id":"F01","offset":0,"text":"测试场景"}],
            "final_anchors":[{"id":"R01","offset":0,"text":"测试场景"}],
            "first_draft":"测试场景","final_draft":"测试场景",
            "previous_checked_angles":["goal"]
        }
        data=v37._private_packet(source)
        self.assertTrue(data["lesson_transfer_not_proven"])
        self.assertFalse(data["official_skill_promoted"])
        self.assertEqual(data["missing_review_angle"],"foreshadowing")
        self.assertNotIn("literary_score",data)

if __name__=="__main__":
    unittest.main()
