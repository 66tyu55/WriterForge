"""0.AI RED: decision action already in prose, observed effect still pending.

A semantic relationship is never proved by two ordered quotes. Existing
0.AH DeepSeek original prose is reproduced byte-for-byte for a counterfactual
trace-only control: these were NOT the model's original trace selections.
No model calls, copied novel, grading, memory or Canon writes.
"""
from __future__ import annotations
from hashlib import sha256
import json
import unittest

from writerforge.v96_causal_turns import (
    check_turn, make_turn_instructions, V96CausalDraftError,
    parse_turn_outline,
)
from writerforge.v98_rolling_causal_planner import (
    latest_observed_effect, prepare_replan_instructions, validate_replan,
    V98RollingPlanError,
)

HISTORY_REAL = (
    "秦渊把三封斥候回报并排铺在案上，灯芯已经烧得只剩一线。东面山口有蹄印，西面河谷的火光比昨夜多了两处，北面却没有消息。"
    "这些都可写，也都只能写这些。他提笔核对着时辰：前锋申时末发来的文书，驿马换过两匹，走的是旧道，"
    "最快要到明日卯时才能递进主帅帐前。亲兵问是否用飞鸽，秦渊摇头，鸽只带得动暗号，带不动这本逐条画了地形的册子。"
    "他把三处可疑的数目、方位、所见时辰一一写清，又在封皮下附了驿道换马的标记，叫传令兵不必催马，只许换人。"
    "搁笔时他听见营门外有马蹄踏碎薄冰，抬头看了一眼，没有起身。"
)
HISTORY_REAL_SHA = "4069722777f98ef5b9bc3b3eaea5429def9ab9b61be0a224114fae9d7ff97991"
HISTORY_ACTION = (
    "他把三处可疑的数目、方位、所见时辰一一写清，又在封皮下附了驿道换马的标记，叫传令兵不必催马，只许换人。"
)
HISTORY_REAL_EFFECT = "搁笔时他听见营门外有马蹄踏碎薄冰，抬头看了一眼，没有起身。"


def beat(kind="decision",actor="秦渊",parent=None,id="t01"):
    return {
        "id":id,"kind":kind,"actor":actor,
        "goal":"作者在当前观察限制下作选择，允许真正的后果尚未发生",
        "causal_parent":parent,"craft_focus":[],
    }


def reply(prose,action,effect,parent_effect=None):
    return json.dumps(
        {"prose":prose,"trace":{
            "action_quote":action,
            "effect_quote":effect,
            "parent_effect_quote":parent_effect,
        }},ensure_ascii=False,separators=(",",":")
    )


def pending_history():
    return check_turn(
        reply(HISTORY_REAL,HISTORY_ACTION,None),
        beat(),mode="causal_guard",max_prose_chars=1024,
    )


class DecisionOutcomePendingSourceTests(unittest.TestCase):
    def test_actual_real_history_prose_unchanged_counterfactual_trace_only(self):
        self.assertEqual(sha256(HISTORY_REAL.encode("utf8")).hexdigest(),
                         HISTORY_REAL_SHA)
        result=pending_history()
        r=result["receipt"]
        self.assertEqual(result["prose"],HISTORY_REAL)
        self.assertIsNone(result["effect_quote"])
        self.assertEqual(r["prose_sha256"],HISTORY_REAL_SHA)
        self.assertEqual(r["source_causal_review_reason"],
                         "DECISION_EFFECT_UNOBSERVED")
        self.assertTrue(r["source_causal_review_required"])
        self.assertTrue(r["outcome_pending_source_only"])
        self.assertIsNotNone(r["action_anchor"])
        self.assertIsNone(r["effect_anchor"])
        self.assertEqual(
            HISTORY_REAL[r["action_anchor"]["start"]:
                         r["action_anchor"]["end"]],HISTORY_ACTION)
        self.assertFalse(r["causal_relation_verified"])
        self.assertFalse(r["eligible_for_factjournal_KNOWN"])
        self.assertFalse(r["eligible_for_experience_promotion"])
        self.assertFalse(r["literary_causality_independently_verified"])
        self.assertTrue(r["candidate_requires_author_acceptance"])

    def test_across_genres_real_choice_can_have_no_instant_effect(self):
        cases=(
            ("仙侠","桑蓉决定等到日出才进入灵圃，先把园门上锁", 
             "她观察水珠的痕迹，想知道昨夜是否有人到过这里。"
             "桑蓉决定等到日出才进入灵圃，先把园门上锁。"
             "她仍不知道是谁碰过灵植，也没宣布灵力已经变化。"
             "她把之前剩下的泥土量记在本子上，暂时没有给出采摘者的名字。"),
            ("历史","秦渊把传令文书封好，决定让驿卒连夜启程",
             "军令从前锋营传来，外面的道路还结着霜。"
             "秦渊把传令文书封好，决定让驿卒连夜启程。"
             "主帅最早要在次日才看到信，他没有假定远方已经做出决策。"
             "火盆的灰慢慢落下，门外仍然无人报告驿卒是否到了驿站。"),
            ("日常","田姨决定明天再去找失落的旧钥匙",
             "炉边的铁盒空着，孙女还在擦餐桌上的水。"
             "田姨决定明天再去找失落的旧钥匙。"
             "两人没有因此突然找回钥匙，只是各自把碗放进柜里。"
             "楼下自行车铃响过一次，她们也没断言那是找钥匙的人。"),
        )
        for genre,action,prose in cases:
            with self.subTest(genre=genre):
                b=beat(actor=genre+"人物")
                r=check_turn(reply(prose,action,None),b,mode="causal_guard")
                self.assertEqual(r["receipt"]["source_causal_review_reason"],
                                 "DECISION_EFFECT_UNOBSERVED")
                self.assertIsNone(r["effect_quote"])

    def test_does_not_let_real_action_or_reversal_skip_required_effect(self):
        for kind in ("action","reversal"):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(
                    V96CausalDraftError,
                    "ACTION_NEEDS_ACTUAL_ACTION_AND_EFFECT",
                ):
                    check_turn(reply(HISTORY_REAL,HISTORY_ACTION,None),
                               beat(kind),mode="causal_guard",
                               max_prose_chars=1024)
        for invalid_action in (None,"凭空已经知道主帅的密令",
                               "没有任何来源的外部事件"):
            with self.subTest(action=invalid_action):
                with self.assertRaises(V96CausalDraftError):
                    check_turn(reply(HISTORY_REAL,invalid_action,None),
                               beat(),mode="causal_guard",
                               max_prose_chars=1024)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "ACTION_NEEDS_ACTUAL_ACTION_AND_EFFECT"):
            check_turn(reply(HISTORY_REAL,None,HISTORY_REAL_EFFECT),
                       beat(),mode="causal_guard",
                       max_prose_chars=1024)

    def test_unchanged_two_quotes_are_still_only_source_not_cause(self):
        r=check_turn(reply(HISTORY_REAL,HISTORY_ACTION,HISTORY_REAL_EFFECT),
                     beat(),mode="causal_guard",
                     max_prose_chars=1024)["receipt"]
        self.assertFalse(r["causal_relation_verified"])
        self.assertFalse(r["outcome_pending_source_only"])
        self.assertIsNone(r["source_causal_review_reason"])
        self.assertIsNotNone(r["effect_anchor"])

    def test_pending_decision_prompt_gives_ai_real_source_option_no_forced_effect(self):
        p=make_turn_instructions(beat(),mode="causal_guard")
        self.assertIn("effect_quote",p)
        self.assertIn("尚未观察",p)
        self.assertIn("JSON null",p)
        self.assertLessEqual(len(p),3500)

    def test_v98_uses_pending_action_as_action_not_as_proven_outcome(self):
        old=pending_history()
        seed=beat(actor="秦渊",parent="t01",id="t02")
        all_beats=parse_turn_outline(json.dumps(
            {"turns":[beat(),seed]},ensure_ascii=False))
        # The old function by definition must still reject no actual effect.
        with self.assertRaisesRegex(V98RollingPlanError,
                                    "NO_ACTUAL_PRIOR_EFFECT"):
            latest_observed_effect((old,))
        instructions=prepare_replan_instructions(
            accepted=(old,),seed_next_beat=seed,
            allowed_actor_names=("秦渊",))
        self.assertIn(HISTORY_ACTION,instructions)
        self.assertIn("后果尚未",instructions)
        self.assertIn("basis_effect_quote",instructions)
        proposal={
            "next_turn":seed,
            "basis_effect_quote":HISTORY_ACTION,
            "pressure_quote":None,"cost_quote":None,
            "unresolved_question":"传令兵是否启程与主帅何时收到情报都还不确定。",
            "reason_for_shift":"写下传令标记并不等于马匹已经发出，更不等于主帅收到情报。",
        }
        _,record=validate_replan(
            json.dumps(proposal,ensure_ascii=False),
            accepted=(old,),accepted_beats=(all_beats[0],),
            seed_next_beat=all_beats[1],allowed_actor_names=("秦渊",))
        self.assertEqual(record["source_basis_kind"],
                         "DECISION_ACTION_ONLY_OUTCOME_PENDING")
        self.assertEqual(record["source_parent_relation_review_reason"],
                         "DECISION_EFFECT_UNOBSERVED")
        self.assertTrue(record["source_parent_relation_review_required"])
        self.assertFalse(record["source_parent_causal_relation_verified"])
        self.assertFalse(record["narrative_semantics_independently_verified"])
        self.assertEqual(record["canon_or_factjournal_writes"],0)
        self.assertTrue(record["source_basis_anchor"]["quote_sha256"])

        # New later prose is authored by the model, and its trace must be
        # literal. Parent has no effect; it is illegal to fake one.
        next_prose=(
            "清晨秦渊仍站在旧驿旁，守军望着远方冰封的道路。"
            "秦渊决定先核对第三封文书的签押。"
            "未时过后驿卒回营，告知秦渊信件还在半路上。"
            "他继续等候主帅的回令，没有宣布战局已经改写。"
        )
        action="秦渊决定先核对第三封文书的签押"
        effect="未时过后驿卒回营，告知秦渊信件还在半路上"
        next_reply=reply(next_prose,action,effect,None)
        next_turn=check_turn(next_reply,seed,mode="causal_guard",
                             accepted=(old,))
        self.assertTrue(next_turn["receipt"]["parent_outcome_pending"])
        self.assertEqual(
            next_turn["receipt"]["parent_source_action_sha256"],
            sha256(HISTORY_ACTION.encode("utf8")).hexdigest())
        self.assertFalse(next_turn["receipt"]["causal_relation_verified"])
        with self.assertRaises(V96CausalDraftError):
            check_turn(reply(next_prose,action,effect,
                             "主帅已经收到并执行军令"),
                       seed,mode="causal_guard",accepted=(old,))

    def test_v98_rejects_modified_prose_and_forged_unsigned_parent_receipt(self):
        old=pending_history()
        seed=beat(actor="秦渊",parent="t01",id="t02")
        cloned={**old,"prose":old["prose"]+"假尾巴"}
        with self.assertRaises(V98RollingPlanError):
            prepare_replan_instructions(
                accepted=(cloned,),seed_next_beat=seed,
                allowed_actor_names=("秦渊",))
        tampered={**old,"receipt":{**old["receipt"],
                                  "receipt_sha256":"0"*64}}
        with self.assertRaises(V98RollingPlanError):
            prepare_replan_instructions(
                accepted=(tampered,),seed_next_beat=seed,
                allowed_actor_names=("秦渊",))


if __name__=="__main__":
    unittest.main()
