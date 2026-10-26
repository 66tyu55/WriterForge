"""0.AN RED: source-backed dialogue and unobserved quiet transition in G.

Original six-event 0.AM DeepSeek Flash outline is from immutable provider wire
40257489862, raw SHA 193e2aae6a937e56c54894c9deed24996abf3827ee10e9b38ea8464f7e736bea.
NO original provider novel prose was generated. These fresh micro-prose examples
are SYNTHETIC structural controls, not literary evidence or model training.
Tests distinguish a real quoted dialogue consequence from a chronological
quiet->aftermath link with no verified causal consequence.
"""
from __future__ import annotations

from hashlib import sha256
import json
import unittest

from writerforge.v96_causal_turns import (
    parse_turn_outline,check_turn,V96CausalDraftError,
)

# Exact six planned beats, including model's non-causal-parent references;
# once accepted, no code/host may rewrite actor goals or narrative text.
ORIGINAL_OUTLINE=(
    '{"turns":[{"id":"t01","kind":"decision","actor":"秦渊",'
    '"goal":"把三路斥候回报按到达时辰与驿传路径重新排序，决定哪一路先封发",'
    '"causal_parent":null,"craft_focus":["interiority","detail"]},'
    '{"id":"t02","kind":"dialogue","actor":"秦渊与传令兵",'
    '"goal":"问清旧道换马点是否齐备，传令兵提出催马可省半日",'
    '"causal_parent":"t01","craft_focus":["dialogue"]},'
    '{"id":"t03","kind":"decision","actor":"秦渊",'
    '"goal":"不因门外马蹄声改递送安排，令传令兵依驿道换马、不许催马",'
    '"causal_parent":"t02","craft_focus":["decision","restraint"]},'
    '{"id":"t04","kind":"action","actor":"秦渊",'
    '"goal":"另附一纸单列北面缺报，写明尚属未知、非确报无敌",'
    '"causal_parent":"t03","craft_focus":["detail"]},'
    '{"id":"t05","kind":"quiet","actor":"秦渊",'
    '"goal":"门外马蹄声来源未明，留灯再核换马标记与三处可疑数目",'
    '"causal_parent":"t04","craft_focus":["interiority","restraint"]},'
    '{"id":"t06","kind":"aftermath","actor":"秦渊",'
    '"goal":"文书按旧道递出，主帅何时收到仍不可知，只把所见时辰誊清不留推断",'
    '"causal_parent":"t05","craft_focus":["detail"]}]}'
)
# 0.AM provider saved wire's decoded answer hash, not a literary truth claim.
REAL_DECODED_SHA="193e2aae6a937e56c54894c9deed24996abf3827ee10e9b38ea8464f7e736bea"


def beat(id,kind,parent=None,actor="秦渊"):
    return {"id":id,"kind":kind,"actor":actor,
            "goal":"只据真实可观察的文字延续已写出的决定与未完成结果",
            "causal_parent":parent,"craft_focus":[]}


def reply(prose,action=None,effect=None,parent_effect=None):
    return json.dumps({"prose":prose,"trace":{
        "action_quote":action,"effect_quote":effect,
        "parent_effect_quote":parent_effect}},
        ensure_ascii=False,separators=(",",":"))


INTRO=("驿站里尚未收到主帅的回令，秦渊知道传令一夜才能送达。"
       "秦渊把旧道换马记录摊到灯下，决定先逐项核对已知时辰。"
       "他把最后一行标注好，不能凭空宣布远处的人已经得知。"
       "门外风声很轻，灯光照着木桌上的空白。")
DIALOGUE=("传令兵走进门来，秦渊示意他坐下，桌上仍是未核对完的旧记录。"
          "传令兵说换马点已经重新点过，走旧道不必催马。"
          "秦渊听见这句话，决定继续按原来换人的安排送信。"
          "二人没有说马蹄必定来自驿卒，也不知道主帅后来如何决定。")
QUIET=("入夜后马厩的风吹得门板轻响，秦渊没有看见究竟是谁从院里经过。"
       "他望着窗纸上的一块旧水渍，不打算马上揭晓马蹄的来源。"
       "火盆里最后一点余烬慢慢暗下去，墙角的茶盏也渐渐冷了。"
       "主帅此刻看见了什么仍然不在秦渊已知的信息里。")
AFTERMATH=("天将亮时，驿站里的人继续收拾昨夜剩下的封泥和旧账册。"
           "秦渊按原来的封套顺序登记，没有对门外昨夜的脚步妄作判断。"
           "他只是等候确认到达的回报，不知道主帅是否已经读过文书。"
           "院子里的风停了，薄雪还在檐下，没有人催促他编出一个结论。")


class SourceCheckedNonActionDependency(unittest.TestCase):
    def test_real_author_outline_is_preserved_not_relabelled_to_match_host_formula(self):
        self.assertEqual(
            sha256(ORIGINAL_OUTLINE.encode("utf8")).hexdigest(),REAL_DECODED_SHA)
        from writerforge.writing_assist import (
            _normalize_optional_model_craft_labels)
        cleaned,meta=_normalize_optional_model_craft_labels(
            ORIGINAL_OUTLINE)
        self.assertTrue(meta["only_model_optional_craft_fields_adjusted"])
        self.assertTrue(meta["events_or_goals_unchanged"])
        self.assertEqual(meta["original_model_plan_sha256"],
                         REAL_DECODED_SHA)
        turns=parse_turn_outline(cleaned)
        self.assertEqual(len(turns),6)
        self.assertEqual((turns[2]["causal_parent"],turns[1]["kind"]),
                         ("t02","dialogue"))
        self.assertEqual((turns[5]["causal_parent"],turns[4]["kind"]),
                         ("t05","quiet"))
        old=json.loads(ORIGINAL_OUTLINE)["turns"]
        for before,after in zip(old,turns):
            self.assertEqual({k:v for k,v in before.items()
                              if k!="craft_focus"},
                             {k:v for k,v in after.items()
                              if k!="craft_focus"})

    def test_real_observable_dialogue_can_be_parent_with_literal_cause_source(self):
        a=check_turn(reply(INTRO),beat("t01","quiet"),
                     mode="causal_guard")
        spoken="传令兵说换马点已经重新点过，走旧道不必催马"
        effect="秦渊听见这句话，决定继续按原来换人的安排送信"
        b=check_turn(
            reply(DIALOGUE,spoken,effect),beat("t02","dialogue"),
            mode="causal_guard",accepted=(a,))
        self.assertEqual(b["receipt"]["causal_check"],
                         "EXACT_OBSERVABLE_ANCHORS_ONLY")
        c=check_turn(reply(
            "秦渊不急着催马，只去查验门外那封仍未送走的记录。"
            "他说昨夜换马的安排照旧，人心不能因为一句传闻乱起来。"
            "他等候外面实际送达的消息，不敢宣称主帅已经知道。"
            "直到夜尽，他仍然把缺报的北路标作未知。",
            None,None,effect),
            beat("t03","quiet",parent="t02"),
            mode="causal_guard",accepted=(a,b))
        self.assertEqual(c["receipt"]["parent_effect_sha256"],
                         sha256(effect.encode("utf8")).hexdigest())
        self.assertFalse(c["receipt"]["causal_relation_verified"])
        self.assertFalse(c["receipt"]["eligible_for_factjournal_KNOWN"])

    def test_quiet_parent_temporal_link_is_unproven_not_bogus_effect(self):
        q=check_turn(reply(QUIET),beat("t01","quiet"),
                     mode="causal_guard")
        self.assertIsNone(q["effect_quote"])
        a=check_turn(reply(AFTERMATH),beat("t02","aftermath",parent="t01"),
                     mode="causal_guard",accepted=(q,))
        receipt=a["receipt"]
        self.assertTrue(receipt["parent_temporal_link_unverified"])
        self.assertEqual(receipt["source_causal_review_reason"],
                         "PARENT_UNOBSERVED_TEMPORAL_LINK")
        self.assertTrue(receipt["source_causal_review_required"])
        self.assertEqual(receipt["parent_temporal_source_sha256"],
                         sha256(QUIET.encode("utf8")).hexdigest())
        self.assertIsNone(receipt["parent_effect_sha256"])
        self.assertFalse(receipt["causal_relation_verified"])
        self.assertFalse(receipt["eligible_for_experience_promotion"])
        self.assertFalse(receipt["eligible_for_factjournal_KNOWN"])
        self.assertEqual(a["prose"],AFTERMATH)

    def test_v119_source_repair_guide_keeps_quiet_temporal_parent_unverified(self):
        from writerforge.v119_revision_transaction import (
            prepare_source_repair_contract)
        parent=check_turn(reply(QUIET),beat("t01","quiet"),
                          mode="causal_guard")
        child=beat("t02","aftermath",parent="t01")
        doc=prepare_source_repair_contract(
            source=AFTERMATH,
            source_sha256=sha256(AFTERMATH.encode("utf8")).hexdigest(),
            beat=child,accepted=(parent,),
            original_trace={"action_quote":None,"effect_quote":None,
                            "parent_effect_quote":None})
        self.assertEqual(doc["previous_causal_parent_id"],"t01")
        self.assertIsNone(doc["actual_previous_effect_quote"])
        self.assertTrue(doc["previous_parent_temporal_link_unverified"])
        self.assertEqual(doc["actual_previous_temporal_source_sha256"],
                         sha256(QUIET.encode("utf8")).hexdigest())
        self.assertFalse(doc["no_literary_grade_or_host_authored_text"] is False)
        self.assertEqual(doc["canon_writes"],0)

    def test_forged_quiet_outcome_or_parent_receipt_must_not_pass(self):
        q=check_turn(reply(QUIET),beat("t01","quiet"),
                     mode="causal_guard")
        for invalid in (
            {**q,"prose":q["prose"]+"伪造的一句后文"},
            {**q,"receipt":{**q["receipt"],"receipt_sha256":"0"*64}},
        ):
            with self.subTest(case="tampered"):
                with self.assertRaises(V96CausalDraftError):
                    check_turn(
                        reply(AFTERMATH),beat("t02","aftermath",parent="t01"),
                        mode="causal_guard",accepted=(invalid,))
        with self.assertRaises(V96CausalDraftError):
            check_turn(
                reply(AFTERMATH,parent_effect="这句话根本没有写在前一场里"),
                beat("t02","aftermath",parent="t01"),
                mode="causal_guard",accepted=(q,))

    def test_future_or_missing_parent_id_still_rejected(self):
        for invalid in ("t03","t99","t00"):
            with self.subTest(parent=invalid):
                with self.assertRaisesRegex(V96CausalDraftError,
                                           "CAUSAL_PARENT_NOT_PRIOR"):
                    parse_turn_outline(json.dumps({"turns":[
                        beat("t01","quiet"),
                        beat("t02","action",parent=invalid)]},
                        ensure_ascii=False))


if __name__=="__main__":
    unittest.main()
