"""V88 hypothetical blind-answer contract redteam, no private R2 or model calls."""
import unittest
from writerforge.v88_frozen_blind_exam import (
    validate_wf_answer,WF88BlindError,ARM_ORDER,arm_prompt,
    shared_prompt,hexdigest,canonical,SYSTEM_PROMPT,
    MAX_PAID_REQUESTS,MAX_OUTPUT_TOKENS_PER_REQUEST,
    MAX_CONSERVATIVE_INPUT_OUTPUT_TOKENS
)

U1="夜雨过后守桥人收起木牌，远处的钟声停了下来。少年不敢靠近石桥，只能先返回村口。"
U2="路边留下湿润脚印，同行的女子说她从来没有见过那个守桥人，少年仍然决定等天亮再走。"
UNITS=(U1,U2)

def anchor(i,phrase):
    where=UNITS[i-1].index(phrase)
    return {"unit":i,"start":where,"end":where+len(phrase),
            "quote":phrase}

def good():
    return dict(status="HYPOTHESIS",claim_id="claim01",
        question="少年不敢靠近旧桥是否与守桥人突然收牌有关？",
        observation=anchor(1,"守桥人收起木牌，远处"),
        consequence=anchor(2,"少年仍然决定等天亮再走"),
        character_knowledge=dict(
            actor="少年",
            known="少年已经看到桥边的异常，并知道自己没有继续靠近。",
            unknown="少年尚不知道守桥人收牌的真正动机和前情。"),
        hypothesis="收牌可能提示存在障碍，导致少年推迟渡桥。",
        alternative="少年也可能因为下雨和同行者的意见而等待。",
        falsifier="如果后来证明过桥完全畅通，这种直接因果需要重估。",
        uncertainty="没有后文，只能把它作为尚未证实的可能因果。")

class V88ContractTests(unittest.TestCase):
    def test_real_quoted_anchors_pass_but_not_semantics(self):
        out=validate_wf_answer(good(),visible_units=UNITS)
        self.assertTrue(out["schema_valid"])
        self.assertEqual(len(out["source_anchors"]),2)
        self.assertFalse(out["causality_independently_verified"])
        raw=canonical(out).decode("utf8")
        self.assertNotIn("守桥人收起木牌，远处",raw)

    def test_fake_or_unseen_quote_and_offset_rejected(self):
        for broken in ("quote","start","unit"):
            data=good()
            if broken=="quote":
                data["observation"]["quote"]="守桥人忽然走出了屋子"
            elif broken=="start":
                data["observation"]["start"]+=1
            else:
                data["observation"]["unit"]=3
            with self.subTest(broken=broken):
                with self.assertRaisesRegex(WF88BlindError,"ANCHOR_"):
                    validate_wf_answer(data,visible_units=UNITS)

    def test_abstain_is_valid_without_fabricating_anchors(self):
        abstain={
           "status":"ABSTAIN","claim_id":None,
           "question":"","observation":None,"consequence":None,
           "character_knowledge":None,
           "hypothesis":"","alternative":"","falsifier":"",
           "uncertainty":"仅凭两个局部段落不能提出可靠的可反证因果假说。"
        }
        self.assertTrue(validate_wf_answer(
            abstain,visible_units=UNITS)["schema_valid"])
        abstain["observation"]=anchor(1,"守桥人收起木牌，远处")
        with self.assertRaisesRegex(WF88BlindError,"ABSTENTION_MUST_NOT_ASSERT"):
            validate_wf_answer(abstain,visible_units=UNITS)

    def test_fair_fixed_arm_order_and_shared_prompt(self):
        self.assertEqual(ARM_ORDER["历史"],("baseline","experience"))
        self.assertEqual(ARM_ORDER["科幻"],("experience","baseline"))
        shared=shared_prompt(UNITS)
        model_strategy="当文本因果缺少结局时，先区分人物所知再提出可反证假说。"
        base=arm_prompt(shared,arm="baseline",strategy=model_strategy)
        exp=arm_prompt(shared,arm="experience",strategy=model_strategy)
        self.assertTrue(base.endswith(shared))
        self.assertTrue(exp.endswith(shared))
        self.assertNotEqual(hexdigest(base.encode()),hexdigest(exp.encode()))
        self.assertNotIn("未读单位3",shared)
        self.assertIn("JSON",SYSTEM_PROMPT)
        self.assertEqual(MAX_PAID_REQUESTS,4)
        self.assertLessEqual(MAX_PAID_REQUESTS*MAX_OUTPUT_TOKENS_PER_REQUEST,5000)
        self.assertLessEqual(MAX_CONSERVATIVE_INPUT_OUTPUT_TOKENS,40000)

    def test_fabricated_human_certification_never_accepted(self):
        data=good()
        data["literary_grade"]=100
        with self.assertRaisesRegex(WF88BlindError,"RESPONSE_SCHEMA"):
            validate_wf_answer(data,visible_units=UNITS)
        data=good()
        data["character_knowledge"]["actor"]="少年"
        self.assertTrue(validate_wf_answer(data,visible_units=UNITS)["schema_valid"])

if __name__=="__main__":
    unittest.main()
