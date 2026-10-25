"""0.AK last two original literary roles: daily item and lyric calm, no forced climax."""
from __future__ import annotations
import inspect
import json
import unittest

from experiments import wf_0ag_diverse_micro_paired_20261025 as first
from experiments import wf_0ah_diverse_micro_paired_20261025 as second
from experiments import wf_0aj_diverse_micro_paired_20261025 as third
from experiments import wf_0ak_diverse_micro_paired_20261025 as fourth
from writerforge.v96_causal_turns import check_turn


class LastTwoGenrePreRegistration(unittest.TestCase):
    def test_all_ten_preregistered_genres_are_unique_not_repeated(self):
        union=[*first.BATCH,*second.BATCH,*third.BATCH,*fourth.BATCH]
        self.assertEqual(len(union),10)
        self.assertEqual(len(set(union)),10)
        self.assertEqual(set(union),set(first.SCENE_BY_ID))
        self.assertEqual(fourth.BATCH,("daily_keys","lyrical_snow"))
        self.assertEqual(fourth.GENRES,first.GENRES)
        self.assertEqual(fourth.MAX_CALLS,8)
        self.assertEqual(fourth.OUTPUT_RESERVATION_CAP,12000)
        self.assertEqual(fourth.AUTHOR_OUTPUT_TOKENS,1400)
        self.assertEqual(fourth.RATER_OUTPUT_TOKENS,1600)
        self.assertEqual(fourth.SCENE_BY_ID["daily_keys"]["kind"],"quiet")
        self.assertEqual(fourth.SCENE_BY_ID["lyrical_snow"]["kind"],"quiet")

    def test_legitimate_lyric_and_mundane_no_hard_effect_requirements(self):
        sources={
            "daily_keys":(
                "田姨找了半天的钥匙，柜台上的茶早已凉透。"
                "孙女翻遍了抽屉，没有急着说是谁把东西弄丢。"
                "门外树影慢慢挪到石阶上，她们仍能平静地交谈。"
                "田姨记起去年冬天穿过的旧鞋，走过去望了两眼。"
                "那把钥匙后来在鞋底旁找到，并不需要一场重大阴谋。"),
            "lyrical_snow":(
                "初雪从屋檐落下来，在路口的砖缝里慢慢化成水。"
                "两个人站在公交站牌下，把本来想说的话又咽回去。"
                "一只纸杯在手心里逐渐变冷，远处的灯仍旧亮着。"
                "其中一人轻轻把围巾理好，没有追问此后的去向。"
                "车到了，她走上车，只留下薄薄的鞋印和一段宁静。"),
        }
        for key,prose in sources.items():
            with self.subTest(genre=key):
                b=fourth.beat(fourth.SCENE_BY_ID[key])
                self.assertEqual(b["kind"],"quiet")
                prompt=fourth.prompt(fourth.SCENE_BY_ID[key],"WF")
                self.assertIn("对安静场景可全部为null",prompt)
                result=check_turn(json.dumps({
                    "prose":prose,
                    "trace":{"action_quote":None,"effect_quote":None,
                             "parent_effect_quote":None}
                },ensure_ascii=False),b,mode="causal_guard")
                self.assertIsNone(result["effect_quote"])
                self.assertIsNone(result["receipt"]["effect_anchor"])
                self.assertFalse(result["receipt"]["source_causal_review_required"])
                self.assertFalse(result["receipt"]["causal_relation_verified"])
                self.assertFalse(result["receipt"]["eligible_for_factjournal_KNOWN"])

    def test_full_source_proof_score_separation_and_no_retry(self):
        for key in fourth.BATCH:
            item=fourth.SCENE_BY_ID[key]
            common=fourth.scene_prompt(item)
            self.assertEqual(fourth.h(common),
                             first.h(first.scene_prompt(item)))
            self.assertTrue(fourth.prompt(item,"bare").startswith(common))
            self.assertTrue(fourth.prompt(item,"WF").startswith(common))
            self.assertIn("200至350",common)
        self.assertIn("candidate_accepted_into_Canon",
                      inspect.getsource(fourth.check_source))
        self.assertIn("on_response_wire=self.save_wire",
                      inspect.getsource(fourth.Model))
        self.assertNotIn("retry(",inspect.getsource(fourth.main).lower())
        self.assertIs(fourth._shared_source_graded_parser,
                      first.parse_micro_judge)


if __name__=="__main__":
    unittest.main()
