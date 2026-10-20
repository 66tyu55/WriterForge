"""V89 aggressive synthetic no-model source grounding regression.

Do not test with private novels. Host resolves quote coordinates only from
two pinned visible units; neither hidden text nor original model prose is
written to stdout/R2. A matching quote is not a causal or literary grade.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import unittest

from writerforge.v88_frozen_blind_exam import (
    validate_wf_answer,WF88BlindError,canonical,
)
from writerforge.v89_source_anchor_gate import (
    resolve_quote_only_answer,diagnose_existing_v88_answer,
    quote_only_question_contract,WF89AnchorError,
)

U1=("暮色笼罩着河岸，守桥人突然收起了最后一块木牌。"
    "几名村民互相张望，没有人继续走向石桥。")
U2=("远处传来一声钟响，少年带着妹妹退回村口，决定等天亮再查明前路。"
    "同行女子却始终没有回答他的疑问。")
VISIBLE=(U1,U2)

def h(value):
    return sha256(value.encode("utf8")).hexdigest()

def question():
    return {
        "status":"HYPOTHESIS","claim_id":"fresh01",
        "question":"守桥人收起木牌是否导致少年选择推迟过桥？",
        "observation":{
            "unit":1,"quote":"守桥人突然收起了最后一块木牌"},
        "consequence":{
            "unit":2,"quote":"少年带着妹妹退回村口"},
        "character_knowledge":{
            "actor":"少年",
            "known":"少年看到了桥边的异常，并且选择暂时返回。",
            "unknown":"还不知道守桥人收牌的原因及前路是否危险。",
        },
        "hypothesis":"异常的收牌可能促使少年暂时停下渡桥计划。",
        "alternative":"少年也可能由于钟声和天色而决定稍后再走。",
        "falsifier":"若原文后续表明早已计划留宿，这种因果应当修订。",
        "uncertainty":"当前只有局部片段，无法核实作出决定的真正动机。",
    }

class HostSourceV89Tests(unittest.TestCase):
    def opts(self,units=VISIBLE):
        return {
            "visible_units":units,
            "pinned_visible_unit_sha256":[h(s) for s in VISIBLE],
            "original_source_sha256":h("frozen original"),
            "frozen_fragment_sha256":h("frozen 2300-char passage"),
            "sealed_future_unit_sha256":h("private third unit"),
        }

    def test_unique_host_spans_pass_as_only_hypothesis(self):
        source=question()
        receipt=resolve_quote_only_answer(source,**self.opts())
        a,b=receipt["located_anchor_meta"]
        self.assertEqual(a["unit"],1)
        self.assertEqual(b["unit"],2)
        self.assertEqual(a["start"],U1.index(source["observation"]["quote"]))
        self.assertEqual(b["start"],U2.index(source["consequence"]["quote"]))
        self.assertTrue(receipt["model_numeric_offsets_not_used"])
        self.assertEqual(receipt["mechanical_result"],
                         "SOURCE_GROUNDED_CANDIDATE_ONLY")
        self.assertFalse(receipt["literary_semantics_independently_verified"])
        self.assertFalse(receipt["eligible_to_direct_writing"])
        self.assertFalse(receipt["skill_promotion_approved"])
        self.assertEqual(receipt["model_calls"],0)
        self.assertEqual(receipt["r2_writes"],0)
        self.assertNotIn("start",source["observation"])
        result=canonical(receipt).decode("utf8")
        self.assertNotIn("守桥人突然收起",result)
        self.assertNotIn("异常的收牌可能促使少年",result)

    def test_rejects_fabricated_quote(self):
        source=question()
        source["observation"]["quote"]="守桥人突然转身打开了破旧房门"
        with self.assertRaisesRegex(WF89AnchorError,
                                    "QUOTE_NOT_IN_VISIBLE_SOURCE"):
            resolve_quote_only_answer(source,**self.opts())

    def test_rejects_quote_wrong_unit(self):
        source=question()
        source["observation"]["unit"]=2
        with self.assertRaisesRegex(WF89AnchorError,
                                    "QUOTE_IN_WRONG_UNIT"):
            resolve_quote_only_answer(source,**self.opts())

    def test_rejects_hidden_unit_and_no_hidden_passed(self):
        source=question()
        source["observation"]["unit"]=3
        with self.assertRaisesRegex(WF89AnchorError,"UNIT_NOT_VISIBLE"):
            resolve_quote_only_answer(source,**self.opts())
        source=question()
        source["observation"]["quote"]="未知的第三单元突然揭示了人物的真正动机"
        with self.assertRaisesRegex(WF89AnchorError,
                                    "QUOTE_NOT_IN_VISIBLE_SOURCE"):
            resolve_quote_only_answer(source,**self.opts())

    def test_rejects_duplicate_quote_across_units(self):
        unit="少年在钟声结束后停止前进。那是众人没有料到的结果。"
        words="钟声结束后停止前进"
        units=(unit,unit)
        q=question()
        q["observation"]={"unit":1,"quote":words}
        q["consequence"]={"unit":2,"quote":words}
        with self.assertRaisesRegex(WF89AnchorError,
                                    "QUOTE_NOT_GLOBALLY_UNIQUE"):
            args=self.opts(units=units)
            args["pinned_visible_unit_sha256"]=[h(s) for s in units]
            resolve_quote_only_answer(q,**args)

    def test_rejects_overlapping_quote_occurrences(self):
        # 8 identical chars within 9 chars contains TWO overlapping matches.
        phrase="哒"*8
        u1=("哒"*9)+"这是重复含糊的原始来源句段，不可选某一次出现。"
        u2=U2
        q=question()
        q["observation"]={"unit":1,"quote":phrase}
        with self.assertRaisesRegex(WF89AnchorError,
                                    "QUOTE_NOT_GLOBALLY_UNIQUE"):
            resolve_quote_only_answer(
                q,visible_units=(u1,u2),
                pinned_visible_unit_sha256=[h(u1),h(u2)],
                original_source_sha256=h("fictional"),
                frozen_fragment_sha256=h("another"),
                sealed_future_unit_sha256=h("hidden"))

    def test_rejects_overlapping_distinct_anchors(self):
        q=question()
        q["consequence"]={
            "unit":1,"quote":"突然收起了最后一块木牌"}
        with self.assertRaisesRegex(WF89AnchorError,"OVERLAPPING"):
            resolve_quote_only_answer(q,**self.opts())

    def test_rejects_same_anchor_as_observation_and_consequence(self):
        q=question()
        q["consequence"]=deepcopy(q["observation"])
        with self.assertRaisesRegex(WF89AnchorError,"SAME_SOURCE_EVENT"):
            resolve_quote_only_answer(q,**self.opts())

    def test_reverse_text_order_requires_review_not_false_semantics(self):
        q=question()
        q["observation"],q["consequence"]=(
            q["consequence"],q["observation"])
        with self.assertRaisesRegex(WF89AnchorError,
                                    "BACKWARD_NARRATIVE_ORDER_NEEDS_REVIEW"):
            resolve_quote_only_answer(q,**self.opts())

    def test_same_visible_units_sha_must_match_frozen_cold_exam(self):
        with self.assertRaisesRegex(WF89AnchorError,
                                    "VISIBLE_SOURCE_CHANGED_FROM_COLD_PIN"):
            resolve_quote_only_answer(question(),
                **self.opts(units=(U1,U2+"篡改")))
        with self.assertRaisesRegex(WF89AnchorError,
                                    "PINNED_VISIBLE_SHA_MISSING"):
            args=self.opts()
            args["pinned_visible_unit_sha256"]=["0"*63,"0"*64]
            resolve_quote_only_answer(question(),**args)

    def test_abstain_has_no_source_or_literary_assertions(self):
        q={
            "status":"ABSTAIN","claim_id":None,"question":"",
            "observation":None,"consequence":None,
            "character_knowledge":None,"hypothesis":"",
            "alternative":"","falsifier":"",
            "uncertainty":"文本没有足够的不同因果锚点，应该保留疑问并弃权。"
        }
        result=resolve_quote_only_answer(q,**self.opts())
        self.assertEqual(result["mechanical_result"],"ABSTAIN_NO_INFERENCE")
        self.assertEqual(result["located_anchor_meta"],[])
        self.assertFalse(result["eligible_to_direct_writing"])
        q["hypothesis"]="这个弃权记录不得携带额外因果判断。"
        with self.assertRaisesRegex(WF89AnchorError,
                                    "ABSTENTION_MUST_NOT_ASSERT"):
            resolve_quote_only_answer(q,**self.opts())

    def test_model_offsets_rejected_new_and_legacy_never_promoted(self):
        fresh=question()
        fresh["observation"]["start"]=23
        with self.assertRaisesRegex(WF89AnchorError,
                                    "MODEL_MUST_SUPPLY_ONLY"):
            resolve_quote_only_answer(fresh,**self.opts())
        legacy=question()
        for field in ("observation","consequence"):
            legacy[field]["start"]=0
            legacy[field]["end"]=len(legacy[field]["quote"])
        with self.assertRaisesRegex(WF88BlindError,"ANCHOR_NOT_EXACT"):
            validate_wf_answer(legacy,visible_units=VISIBLE)
        old=deepcopy(legacy)
        diagnosis=diagnose_existing_v88_answer(
            legacy,**self.opts())
        self.assertEqual(diagnosis["retrospective_result"],
                         "RETROSPECTIVE_SOURCE_QUOTE_ONLY_MATCH")
        self.assertEqual(diagnosis["candidate_anchor_count"],2)
        self.assertFalse(diagnosis["can_be_used_for_WF_write"])
        self.assertFalse(diagnosis["can_be_used_for_v86_approval"])
        self.assertEqual(legacy,old)

    def test_rejects_extra_fields_and_false_grade(self):
        q=question()
        q["human_approval"]=True
        with self.assertRaisesRegex(WF89AnchorError,
                                    "MODEL_ANSWER_CONTRACT_INVALID"):
            resolve_quote_only_answer(q,**self.opts())
        q=question()
        q["character_knowledge"]["actor"]="少年"
        self.assertTrue(resolve_quote_only_answer(
            q,**self.opts())["located_anchor_meta"])
        self.assertIn("不要输出start/end",quote_only_question_contract())

if __name__=="__main__":
    unittest.main()
