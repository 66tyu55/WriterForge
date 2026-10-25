"""0.AG preregistered first batch: offline protocol only, never model calls."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import inspect
import json
import unittest

from experiments import wf_0ag_diverse_micro_paired_20261025 as e
from writerforge.v96_causal_turns import check_turn


class TestFirstBatchProtocol(unittest.TestCase):
    def test_ten_frozen_different_original_task_roles(self):
        self.assertEqual(len(e.GENRES),10)
        self.assertEqual(len(e.SCENE_BY_ID),10)
        self.assertEqual(len(e.BATCH),3)
        self.assertEqual(tuple(e.BATCH),
                         ("wuxia_bridge","horror_flashlight","strategy_ledger"))
        self.assertTrue(set(e.BATCH).issubset(e.SCENE_BY_ID))
        self.assertEqual(len({v["topic"] for v in e.GENRES}),10)
        self.assertEqual(len({v["id"] for v in e.GENRES}),10)
        self.assertIn("灵植",e.SCENE_BY_ID["xianxia_plant"]["topic"])
        self.assertIn("分手协议",e.SCENE_BY_ID["romance_photos"]["topic"])
        self.assertIn("初雪",e.SCENE_BY_ID["lyrical_snow"]["topic"])

    def test_identical_model_author_output_budget_and_prose_target(self):
        self.assertEqual(e.MAX_CALLS,12)
        self.assertEqual(e.AUTHOR_OUTPUT_TOKENS,1400)
        self.assertEqual(e.OUTPUT_RESERVATION_CAP,18000)
        for k in e.BATCH:
            case=e.SCENE_BY_ID[k]
            bare=e.prompt(case,"bare")
            wf=e.prompt(case,"WF")
            self.assertIn(e.scene_prompt(case),bare)
            self.assertIn(e.scene_prompt(case),wf)
            self.assertIn("200至350",bare)
            self.assertIn("200至350",wf)
            self.assertIn("causal",str(inspect.getsource(e.check_source)))
            self.assertNotEqual(e.h(bare),e.h(wf))
        self.assertEqual(len(e.JUDGEMENTS),2)
        self.assertEqual(len(e.CRITERIA),5)

    def test_source_uses_actual_prose_and_wf_existing_gates_not_literary_rewards(self):
        code=inspect.getsource(e.check_source)
        self.assertIn("normalize_model_source_citations",code)
        self.assertIn("check_turn",code)
        self.assertIn("preflight_next_prose",code)
        self.assertIn("external_temporal_step",code)
        self.assertIn("false_positive_count_confirmed",code)
        self.assertIn("false_negative_count_confirmed",code)
        self.assertIn("candidate_accepted_into_Canon",code)
        self.assertEqual(e.BATCH[1],"horror_flashlight")

    def test_grade_prompt_cannot_revert_to_old_0ad_token_scope(self):
        fake=type("Fake",(),{"ask":lambda self,*args,**kwargs:{
            "ratings":[{"id":id,"scores":{c:12 for c in e.CRITERIA},
                        "reason":"具有具体真实的物理动作细节",
                        "weakness":"人物心理表达可以更加含蓄"}
                       for id in ("甲","乙")]}})()
        item=e.SCENE_BY_ID[e.BATCH[0]]
        pair={"bare":{"prose":"甲"*220},"WF":{"prose":"乙"*228}}
        with patch.object(fake,"ask",wraps=fake.ask) as caller:
            r=e.judge_one(fake,item,pair,e.JUDGEMENTS[0],"blind-1")
        self.assertEqual(r["裸模型"]["score"],60)
        self.assertEqual(r["WF辅助"]["score"],60)
        prompt=caller.call_args.args[3]
        self.assertIn("200至350",prompt)
        self.assertNotIn("约260到340",prompt)
        self.assertIn("不把任何技术检测结果作为文学分数",prompt)
        self.assertNotIn("原作家原文",prompt)

    def test_real_deepseek_five_number_array_recovered_losslessly(self):
        # 0.AG original, fixed-criterion order; only representation changes.
        records={"ratings":[
            {"id":"甲","scores":[17,18,17,16,16],
             "reason":"动作位置与伤势相互牵制，叙事具体可信。",
             "weakness":"结尾的动作负担可以再收束一点。"},
            {"id":"乙","scores":[16,17,15,17,15],
             "reason":"受伤角色的身体限制始终存在，没有凭空消除。",
             "weakness":"绳子的处理过程仍可交代得更准确。"},
        ],"type":"json_object"}
        original=json.dumps(records,ensure_ascii=False)
        parsed,receipt=e.parse_micro_judge(records)
        self.assertEqual(sum(parsed["甲"]["scores"].values()),84)
        self.assertEqual(sum(parsed["乙"]["scores"].values()),80)
        self.assertEqual(list(parsed["甲"]["scores"].values()),
                         [17,18,17,16,16])
        self.assertEqual(receipt["score_arrangement_recovered"],2)
        self.assertTrue(receipt["numeric_scores_unchanged"])
        self.assertEqual(json.dumps(records,ensure_ascii=False),original)
        # Unsupported array sizes and bool masquerading as int remain RED.
        with self.assertRaises(RuntimeError):
            e.parse_micro_judge({"ratings":[
                {**records["ratings"][0],"scores":[17,18,17,16]},
                records["ratings"][1]]})
        with self.assertRaises(RuntimeError):
            e.parse_micro_judge({"ratings":[
                {**records["ratings"][0],
                 "scores":[True,18,17,16,16]},
                records["ratings"][1]]})

    def test_original_reverse_paid_rater_labelled_map_not_new_graded_calls(self):
        # 0.AG reverse real DeepSeek wire (wuxia/horror) used a labelled
        # object rather than a ratings list. Preserve numbers and reasons.
        row=lambda nums: {"scores":dict(zip(e.CRITERIA,nums)),
            "reason":"对动作发生位置的判断有具体段内证据，也保留人物犹疑。",
            "weakness":"有几处细节对主线推进仍显得不够集中。"}
        data={"type":"json_object","ratings":{
            "甲":row([17,18,17,15,18]),
            "乙":row([15,16,16,14,16])}}
        source=json.dumps(data,ensure_ascii=False)
        parsed,receipt=e.parse_micro_judge(data)
        self.assertEqual(sum(parsed["甲"]["scores"].values()),85)
        self.assertEqual(sum(parsed["乙"]["scores"].values()),77)
        self.assertEqual(receipt["labelled_map_rows_losslessly_rekeyed"],2)
        self.assertTrue(receipt["model_reason_and_weakness_unchanged"])
        self.assertEqual(json.dumps(data,ensure_ascii=False),source)
        with self.assertRaises(RuntimeError):
            e.parse_micro_judge({"ratings":{"甲":row([1]*5)}})

    def test_real_provider_original_saved_before_json_validation_and_no_retries(self):
        source=inspect.getsource(e.Model)
        main=inspect.getsource(e.main)
        self.assertIn("on_response_wire=self.save_wire",source)
        self.assertIn("path.write_bytes(data)",source)
        self.assertIn("original_wire_preserved",source)
        self.assertIn('OUT/"author-originals"',main)
        self.assertIn('OUT/"STATUS.json"',main)
        self.assertIn("self.task=None",source)
        self.assertNotIn("time.sleep",source)
        self.assertNotIn("retry(",source.lower())
        self.assertIn("model.budget.calls_reserved",main)
        self.assertIn("R2_reads",main)
        self.assertIn("human_semantic_review_still_required",
                      inspect.getsource(e.check_source))

    def test_true_cause_is_a_source_only_candidate_not_accepted_truth(self):
        item=e.SCENE_BY_ID["wuxia_bridge"]
        sentence="周阙用肩背抵着正在倾斜的木板"
        effect="木板被暂时撑住，伤者得以退开半步"
        prose=("天光照着溪谷，镖师在悬桥上摇晃，身后的同行者左腿沾血。"
               +sentence+"。"+effect+"。"
               "随行的老人解下背绳将两人连在一处，桥的另一头有人叫他们赶快。"
               "没人知道桥索还能撑几刻，因此他们并未立刻跨过去。"
               "他摸了摸腰间的药袋，决定先把伤者挪到有护栏的一段。")
        doc={"prose":prose,"trace":{"action_quote":sentence,
             "effect_quote":effect,"parent_effect_quote":None}}
        result=e.check_source(item,{"WF":doc})
        self.assertEqual(result["V96_status"],
                         "SOURCE_QUOTES_ORDER_VERIFIED_CAUSALITY_NOT_PROVEN")
        self.assertFalse(result["V96_causal_relation"]["relation_verified"])
        self.assertFalse(result["candidate_accepted_into_Canon"])
        self.assertIsNone(result["false_positive_count_confirmed"])
        self.assertIsNone(result["false_negative_count_confirmed"])


if __name__=="__main__":
    unittest.main()
