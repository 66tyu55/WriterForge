"""0.AG RED: genuine reversed DeepSeek provider ratings use label-keyed mapping.

Input is the exact response STRUCTURE observed in the saved original
wuxia_bridge/horror_flashlight blind-2 provider wires; no new judge call.
Only lossless presentation adaptation is permitted, never score invention.
"""
from __future__ import annotations
import copy
import unittest

from experiments.wf_0ag_diverse_micro_paired_20261025 import (
    CRITERIA, parse_micro_judge,
)


class ActualReverseRatingShape(unittest.TestCase):
    def test_actual_wuxia_reverse_keyed_two_ratings_losslessly_recovered(self):
        wf=[17,18,17,15,18]  # actual reverse '甲' from WF original
        bare=[15,16,16,14,16]  # actual reverse '乙' from bare original
        doc={"type":"json_object","ratings":{
            "甲":{"scores":dict(zip(CRITERIA,wf)),
                 "reason":"语言干净克制，具体细节服务悬桥上负重行动。",
                 "weakness":"对岸催促尚未产生更明确的动机张力。"},
            "乙":{"scores":dict(zip(CRITERIA,bare)),
                 "reason":"刀鞘、断藤和重落脚等空间行为有连续性。",
                 "weakness":"连续动作挤得稍密，节奏仍然可以更舒缓。"},
        }}
        original=copy.deepcopy(doc)
        parsed,receipt=parse_micro_judge(doc)
        self.assertEqual(sum(parsed["甲"]["scores"].values()),85)
        self.assertEqual(sum(parsed["乙"]["scores"].values()),77)
        self.assertEqual(doc,original)
        self.assertEqual(receipt["extra_model_calls"],0)
        self.assertTrue(receipt["numeric_scores_unchanged"])
        self.assertTrue(receipt["model_reason_and_weakness_unchanged"])
        self.assertEqual(receipt["labelled_map_rows_losslessly_rekeyed"],2)

    def test_malformed_keyed_labels_refused_instead_of_inventing_missing_grade(self):
        record={"scores":{axis:15 for axis in CRITERIA},
                "reason":"细节真实且可核验，表现人物动作状态。",
                "weakness":"因果的细节联系还可进一步说明。"}
        for ratings in (
            {"甲":record},
            {"甲":record,"丙":record},
            {"甲":record,"乙":{**record,"scores":{**record["scores"],
                                            "语言自然与节制":True}}},
        ):
            with self.subTest(ratings=list(ratings)):
                with self.assertRaises((RuntimeError,ValueError)):
                    parse_micro_judge({"ratings":ratings})


if __name__=="__main__":
    unittest.main()
