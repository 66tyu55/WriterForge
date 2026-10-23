"""Zero-provider protocol checks before the real InkStone writing batch."""
import json
import unittest

from experiments.seven_literary_scenes_inkstone_ab import (
    scenarios,make_packet,diagnose,sha,GENRES,
    FREE_CANDIDATES,MAX_COMPLETIONS,MAX_PROBES,
)


class SevenScenarioBatchProtocolTests(unittest.TestCase):
    def test_fixed_seven_distinct_chinese_categories(self):
        data=scenarios()
        self.assertEqual(tuple(c["genre"] for c in data),GENRES)
        self.assertEqual(len({c["id"] for c in data}),7)
        self.assertEqual(len(data),7)
        self.assertTrue(all(len(c["seed"])>=60 for c in data))
        self.assertEqual(MAX_COMPLETIONS,14)
        self.assertEqual(MAX_PROBES,3)
        self.assertEqual(FREE_CANDIDATES[:2],
                         ("intern-s2","Atria-Dawn-Preview"))

    def test_prompts_are_actual_wf_guarded_packets_and_share_origin(self):
        for case in scenarios():
            with self.subTest(category=case["genre"]):
                bare,guided,temporal,graph,receipt=make_packet(case)
                self.assertIn(case["seed"],bare)
                self.assertIn(case["seed"],guided)
                self.assertIn(case["goal"],bare)
                self.assertIn(case["goal"],guided)
                self.assertIn("原创",guided)
                self.assertIn("【本章当前事件】",guided)
                self.assertTrue(receipt["wf_prompt_verified_hard_context"])
                self.assertNotEqual(sha(bare),sha(guided))
                self.assertEqual(graph["chapter_index"],1)
                self.assertEqual(graph["model_calls"],0)
                self.assertEqual(graph["canon_writes"],0)
                self.assertLessEqual(len(guided),10000)
                self.assertEqual(
                    receipt["bare_prompt_sha256"],sha(bare))
                self.assertEqual(
                    receipt["wf_prompt_sha256"],sha(guided))
                self.assertEqual(
                    temporal["reducer_result"]["model_calls"],0
                    if "model_calls" in temporal["reducer_result"]
                    else 0)

    def test_synthetic_body_receipts_never_claim_human_judgment(self):
        for case in scenarios():
            _,_,source,graph,_=make_packet(case)
            result=diagnose(
                case,"沈砚望着门外的旧雨，没有贸然行动。"*28,
                source,graph,variant="bare",usage={},
                finish_reason="stop")
            self.assertFalse(result["literary_quality_blind_judged"])
            self.assertTrue(result["prose_in_saved_private_artifact"])
            self.assertTrue(result["output_sha256"])
            self.assertIn("source_mechanics_clean",result)


if __name__=="__main__":
    unittest.main()
