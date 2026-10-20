"""V96 purely offline narrative causality gate redteam; NO real model.

Checks actual generated prose quotation existence, ordering, dependency,
approved knowledge boundary, and strict bounded candidate-only status.
Lexical proof is never claimed to establish literary causation.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import unittest

from writerforge.v96_causal_turns import (
    V96CausalDraftError,parse_turn_outline,check_turn,
    make_turn_instructions,assemble_prose,receipts_only,
    canonical,digest,
)


ACTION1="守桥人取下门前的告示"
EFFECT1="少年停下脚步决定绕开石桥"
ACTION2="女子翻出一页旧账册"
EFFECT2="众人不得不暂缓渡河的决定"
GUARD="箱底密钥只有长老知道"


def turns():
    return {"turns":[
        {"id":"t01","kind":"action","actor":"少年",
         "goal":"少年发现桥边异常后必须做出可信的绕路决定",
         "causal_parent":None,"craft_focus":["action","restraint"]},
        {"id":"t02","kind":"decision","actor":"女子",
         "goal":"女子查看旧账册使众人改变原来的渡河计划",
         "causal_parent":"t01","craft_focus":["dialogue","detail"]},
    ]}


def plan():
    return parse_turn_outline(json.dumps(turns(),ensure_ascii=False))


def prose1():
    return ("黄昏最后一点天光落到桥头时，"+ACTION1+
            "。少年在对岸看见几条船同时靠近码头，没有立即开口解释。"
            "他本来答应朋友当夜入城，此刻却听见桥下的铁链刮过石壁。"
            "他望了望随行的药箱，"+EFFECT1+
            "。同伴问他是否反悔，他只是把地图重新摊在船板上。")


def prose2():
    return ("他们沿着旧堤走到废弃的驿站，门上的锁已经生锈。"
            "女子翻找许久后，"+ACTION2+
            "。纸面记着三年前水灾前后各船的去向，却没有写明谁动过桥索。"
            "她把那一页递给少年，要求先核对幸存船工的口供。"
            "两人争论了半刻，"+EFFECT2+
            "。窗外仍有雨声，没人能据此断言守桥人的真正目的。")


def response(prose,action,effect,parent=None):
    return json.dumps({
        "prose":prose,
        "trace":{"action_quote":action,"effect_quote":effect,
                 "parent_effect_quote":parent}
    },ensure_ascii=False)


class V96GateTests(unittest.TestCase):
    def test_actual_action_effect_spans_and_dependency_replay(self):
        beats=plan()
        a=check_turn(response(prose1(),ACTION1,EFFECT1),beats[0],
                     mode="causal_guard")
        b=check_turn(response(prose2(),ACTION2,EFFECT2,EFFECT1),beats[1],
                     mode="causal_guard",accepted=(a,))
        self.assertEqual(a["receipt"]["causal_check"],
                         "EXACT_OBSERVABLE_ANCHORS_ONLY")
        self.assertEqual(b["receipt"]["parent_effect_sha256"],
                         digest(EFFECT1.encode("utf8")))
        self.assertFalse(b["receipt"]["literary_causality_independently_verified"])
        self.assertFalse(b["receipt"]["eligible_for_factjournal_KNOWN"])
        self.assertFalse(b["receipt"]["eligible_for_experience_promotion"])
        self.assertLess(a["receipt"]["action_anchor"]["start"],
                        a["receipt"]["effect_anchor"]["start"])
        content=assemble_prose([a,b])
        self.assertIn(EFFECT2,content)
        manifest=receipts_only([a,b],mode="causal_guard",
                               outline_sha="0"*64)
        self.assertFalse(manifest["independent_literary_quality_verified"])
        self.assertEqual(manifest["canonical_fact_write_count"],0)
        self.assertNotIn(ACTION1,str(manifest))
        self.assertNotIn(EFFECT2,str(manifest))

    def test_same_response_split_only_vs_guard_detects_fabrication(self):
        beats=plan()
        forged=response(prose1(),"守桥人打开不曾存在的密室",EFFECT1)
        no_gate=check_turn(forged,beats[0],mode="split_only")
        self.assertEqual(no_gate["receipt"]["causal_check"],
                         "SPLIT_ONLY_UNVERIFIED")
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "ACTION_NOT_UNIQUE_IN_ACTUAL_PROSE"):
            check_turn(forged,beats[0],mode="causal_guard")

    def test_rejects_effect_before_action_in_actual_prose(self):
        beat=plan()[0]
        wrong=(EFFECT1+"。老船工忽然停了话头，少年仍站在雨里。"
               +ACTION1+"。没人因此敢说出隐藏的原委，桥上水声依旧。"
               "几人各自等候对方先开口，低声交谈后又沉默下来。")
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "ACTION_EFFECT_OVERLAP_OR_REVERSED"):
            check_turn(response(wrong,ACTION1,EFFECT1),beat,
                       mode="causal_guard")

    def test_duplicate_evidence_cannot_pick_arbitrary_appearance(self):
        beat=plan()[0]
        text=prose1().replace(ACTION1,ACTION1+"，又"+ACTION1)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "ACTION_NOT_UNIQUE_IN_ACTUAL_PROSE"):
            check_turn(response(text,ACTION1,EFFECT1),beat,
                       mode="causal_guard")

    def test_negated_action_does_not_falsely_become_actual_event(self):
        beat=plan()[0]
        text=prose1().replace(ACTION1,"没有"+ACTION1)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "POLARITY_UNCERTAIN_NEEDS_REVIEW"):
            check_turn(response(text,ACTION1,EFFECT1),beat,
                       mode="causal_guard")

    def test_parent_must_reference_actual_previous_effect(self):
        a=check_turn(response(prose1(),ACTION1,EFFECT1),plan()[0],
                     mode="causal_guard")
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "PARENT_CAUSE_NOT_ANCHORED"):
            check_turn(response(prose2(),ACTION2,EFFECT2,
                                "他们已证明真凶"),plan()[1],
                       mode="causal_guard",accepted=(a,))
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "CAUSAL_PARENT_NOT_YET_WRITTEN"):
            check_turn(response(prose2(),ACTION2,EFFECT2,EFFECT1),
                       plan()[1],mode="causal_guard",accepted=())

    def test_author_guard_blocks_only_explicitly_approved_phrases(self):
        bad=prose1()+"。"+GUARD+"，这个说法突然出现在少年耳边。"
        sample=response(bad,ACTION1,EFFECT1)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "AUTHOR_CONFIRMED_KNOWLEDGE_BOUNDARY"):
            check_turn(sample,plan()[0],mode="causal_guard",
                       author_confirmed_forbidden_phrases=(GUARD,))
        # B: deliberately no hard causal/knowledge guard; comparable calls.
        b=check_turn(sample,plan()[0],mode="split_only",
                     author_confirmed_forbidden_phrases=(GUARD,))
        self.assertEqual(b["receipt"]["causal_check"],
                         "SPLIT_ONLY_UNVERIFIED")

    def test_quiet_aftermath_requires_no_bogus_action_or_reversal(self):
        beat={"id":"t02","kind":"quiet","actor":"少年",
              "goal":"在沉默里让读者察觉两人之间尚未说出的隔阂",
              "causal_parent":None,"craft_focus":["restraint"]}
        text=("雨滴从瓦檐落在水缸里，响声慢得像一只旧钟。"
              "少年默默擦去木盒上的泥渍，迟迟没有推开那扇门。"
              "女子站在院外，没再追问他为什么选择绕路。"
              "远处的船笛声渐渐消失，窗前的灯也暗下来。")
        raw=response(text,None,None)
        accepted=check_turn(raw,beat,mode="causal_guard")
        self.assertIsNone(accepted["effect_quote"])
        self.assertIsNone(accepted["receipt"]["action_anchor"])
        self.assertEqual(accepted["receipt"]["causal_check"],
                         "EXACT_OBSERVABLE_ANCHORS_ONLY")

    def test_plan_rejects_skipped_order_future_and_synthetic_causality(self):
        bad=turns()
        bad["turns"][1]["id"]="t03"
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "PLAN_FIELDS_ID"):
            parse_turn_outline(json.dumps(bad,ensure_ascii=False))
        bad=turns()
        bad["turns"][0]["causal_parent"]="t02"
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "PARENT_NOT_PRIOR"):
            parse_turn_outline(json.dumps(bad,ensure_ascii=False))
        bad=turns()
        bad["turns"][0]["kind"]="quiet"
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "PARENT_NOT_PRIOR"):
            parse_turn_outline(json.dumps(bad,ensure_ascii=False))
        bad=turns()
        bad["turns"][0]["craft_focus"]=[{"model_trick":"fake"}]
        with self.assertRaises(V96CausalDraftError):
            parse_turn_outline(json.dumps(bad,ensure_ascii=False))

    def test_duplicate_json_keys_future_schemas_and_surrogate_blocked(self):
        with self.assertRaises(V96CausalDraftError):
            parse_turn_outline('{"turns":[],"turns":[]}')
        with self.assertRaisesRegex(V96CausalDraftError,"JSON_BAD_UNICODE"):
            parse_turn_outline('{"text":"\ud800"}')
        bad=turns();bad["forged_canon_known"]=True
        with self.assertRaises(V96CausalDraftError):
            parse_turn_outline(json.dumps(bad,ensure_ascii=False))

    def test_memory_prompt_bounded_and_based_on_actual_prose_tail(self):
        beats=plan()
        accepted=check_turn(response(prose1(),ACTION1,EFFECT1),
                            beats[0],mode="causal_guard")
        text=make_turn_instructions(
            beats[1],mode="causal_guard",accepted=(accepted,),
            author_confirmed_forbidden_phrases=(GUARD,))
        self.assertIn(EFFECT1,text)
        self.assertIn(prose1()[-100:],text)
        self.assertIn(GUARD,text)
        self.assertLessEqual(len(text),3500)

    def test_no_token_padding_and_length_budget_rejected(self):
        too_short=response("只有五个字",ACTION1,EFFECT1)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "PROSE_OR_TRACE"):
            check_turn(too_short,plan()[0],mode="split_only")
        oversized=response(prose1()+"填"*950,ACTION1,EFFECT1)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "PROSE_OR_TRACE"):
            check_turn(oversized,plan()[0],mode="causal_guard")

if __name__=="__main__":
    unittest.main()
