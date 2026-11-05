"""Offline gates for 0.EM paid Intern-S2 practice. No provider calls in tests."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from experiments import wf_0em_paid_intern_s2_behavior_practice as em
from writerforge.reverse_discovery_models import DiscoveryCallBudget, DiscoveryError

class BoundedInternS2BehaviorPractice(unittest.TestCase):
    def test_exact_existing_public_snapshot_and_readings(self):
        data=em.dry_run()
        self.assertEqual(data["reference_library"],"wf-0el-xuehai-literary-408-20261103-v1")
        self.assertEqual(data["max_provider_wire_calls"],8)
        self.assertEqual(data["max_reserved_completion_tokens"],21000)
        self.assertEqual(len(data["tasks"]),2)
        self.assertEqual({x["source_id"] for x in data["tasks"]},
                         {"classic-0el-2-hh","classic-0el-4-jm"})
        self.assertTrue(data["uses_public_domain_sources_only"])
        self.assertFalse(data["user_private_prose_sent"])
        self.assertFalse(data["model_weight_training"])
        self.assertEqual(data["literary_winner"],"UNDETERMINED")

    def test_no_payment_without_named_gate(self):
        with patch.dict("os.environ",{
            "DISCOVERY_API_KEY":"test-not-real-key-and-never-used"},clear=True):
            with self.assertRaisesRegex(em.PracticeError,"EXPLICIT_PAID"):
                em.paid_run(__import__("pathlib").Path("/tmp/do-not-create"))
        with patch.dict("os.environ",{
            "WF0EM_PAID_EXPERIMENT":"WF0EM_BOUNDED_S2_20261105"
            },clear=True):
            with self.assertRaisesRegex(em.PracticeError,"DISCOVERY_KEY"):
                em.paid_run(__import__("pathlib").Path("/tmp/do-not-create"))

    def test_teacher_cannot_hallucinate_source_anchor_or_single_view(self):
        source=em.load_public_sources()["ford-tax"]
        good={
            "use":"PARTIAL",
            "reason":"原文存在不同角色的误解，能够启发对当前写作问题的审视，但不必照搬。",
            "source_anchors":source["anchors"][:2],
            "habit_questions":[
                {"ask":"谁最先误以为亲眼见过真相？","not_when":"文本已明示事实时无需制造无谓悬念。"},
                {"ask":"眼前决定会让谁失去生计或安宁？","not_when":"这场戏没有相关物质冲突时可以跳过。"},
            ],
            "perspectives":[
                {"actor":"甲船工","wants":"救病人","knows":"见过病船","cost":"损失舟船"},
                {"actor":"乙巡使","wants":"守城门","knows":"听过城令","cost":"失去职位"},
                {"actor":"丙徒弟","wants":"不被牵连","knows":"只听传闻","cost":"受到责打"},
            ],
            "disagreement":"有人认为必须封江，有人认为城令只是迁怒百姓，两者都缺少直接证据。",
        }
        clean=em.validate_coach(good,source["original"])
        self.assertEqual(clean["use"],"PARTIAL")
        broken={**good,"source_anchors":["凭空捏造的原句绝不应该存在","另一个不存在的句子"]}
        with self.assertRaisesRegex(em.PracticeError,"COACH_ANCHORS"):
            em.validate_coach(broken,source["original"])
        broken={**good,"perspectives":[good["perspectives"][0]]*3}
        with self.assertRaisesRegex(em.PracticeError,"COACH_DISTINCT"):
            em.validate_coach(broken,source["original"])

    def test_optional_habits_influence_prompt_not_acceptance(self):
        premise=em.EXERCISES[0]
        a=em.writer_prompt(premise,None)[1]
        source=em.load_public_sources()["ford-tax"]
        coach={
            "use":"USE",
            "habit_questions":[
                {"ask":"谁掌握局部事实","not_when":"角色全知之时"},
                {"ask":"谁为决定付钱","not_when":"场景没有价款"}
            ],
            "perspectives":[
                {"actor":"甲船工","wants":"通行","knows":"天黑","cost":"冻伤"},
                {"actor":"乙巡使","wants":"封河","knows":"传闻","cost":"失职"},
                {"actor":"丙徒弟","wants":"送药","knows":"病情","cost":"误期"}
            ],"disagreement":"不同人物会以不同证据解释封河的目的。"}
        b=em.writer_prompt(premise,coach)[1]
        self.assertNotIn("可选写作问题",a)
        self.assertIn("可选写作问题",b)
        self.assertIn("并非命令",b)
        self.assertNotIn(source["original"][:200],b)
        skip={**coach,"use":"SKIP"}
        self.assertEqual(em.writer_prompt(premise,skip)[1],a)

    def test_call_budget_fail_closed_before_network(self):
        budget=DiscoveryCallBudget(max_calls=2,max_reserved_output_tokens=5000)
        budget.reserve(2000,2500,role="planner")
        budget.reserve(2000,2500,role="writer")
        with self.assertRaises(DiscoveryError):
            budget.reserve(2000,2500,role="writer")
        self.assertEqual(budget.calls,2)

    def test_long_verbatim_source_copy_is_rejected(self):
        source=em.load_public_sources()["herb-well"]["original"]
        self.assertTrue(em._copied_from_source(
            "他写道"+source[:100]+"从此发生变化",source))
        self.assertFalse(em._copied_from_source(
            "一道白色的雨落到城墙，守门人想起了自己的孩子。",source))

if __name__=="__main__":
    unittest.main()
