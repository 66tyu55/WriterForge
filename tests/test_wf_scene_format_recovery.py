"""Literary prose must survive narrow provider JSON and model trace errors.

All samples invented for testing. No private books, Atria originals or paid
requests. Structural source guards/author exclusions and bounded outputs stay.
"""
import hashlib
import inspect
import json
import unittest

from writerforge.deepseek_flash_model import (
    DeepSeekFlashModel,FlashBudget,DeepSeekFlashError,
)
from writerforge.v96_causal_turns import (
    check_turn,normalize_model_source_citations,
    review_only_model_turn,V96CausalDraftError,
)
from writerforge.writing_assist import AutonomousWriting


def beat(ident="t01",*,parent=None,kind="decision"):
    return {"id":ident,"kind":kind,"actor":"沈砚",
            "goal":"沈砚仍需依据自己掌握的信息决定是否查明真相",
            "causal_parent":parent,"craft_focus":["interiority"]}


def envelope(prose,action,effect,parent=None):
    return json.dumps({
        "prose":prose,
        "trace":{"action_quote":action,"effect_quote":effect,
                 "parent_effect_quote":parent},
    },ensure_ascii=False,separators=(",",":"))


def fake_wire(message):
    return json.dumps({
        "choices":[{"finish_reason":"stop",
                    "message":{"content":message}}],
        "usage":{"prompt_tokens":100,"completion_tokens":200},
    },ensure_ascii=False).encode("utf8")


class OriginalProviderJsonRecovery(unittest.TestCase):
    def build(self,body,wire_sink=None):
        return DeepSeekFlashModel(
            api_key="synthetic-model-token-not-secret",
            budget=FlashBudget(max_calls=1,
                               max_reserved_output_tokens=1000),
            transport=lambda request:fake_wire(body),
            on_response_wire=wire_sink,
        )

    def test_exact_stray_tail_after_complete_model_prose_json(self):
        prose="沈砚守在驿站门外，手里那封旧信被他折起又展开。"*9
        schema={"prose":prose,
                "trace":{"action_quote":None,"effect_quote":None,
                         "parent_effect_quote":None}}
        original=json.dumps(schema,ensure_ascii=False,
                            separators=(",",":"))
        wire=[]
        model=self.build(original+'"}',wire.append)
        result=model.ask_json(
            role="self_scene_writing",
            system="严格JSON。写作正文原貌绝不能被替换。",
            user="写一个角色安静等待真相的故事。",
            max_tokens=500)
        self.assertEqual(result,schema)
        self.assertEqual(len(wire),1)
        note=model.last_response_format_recovery
        self.assertEqual(note["extra_suffix_codepoints"],2)
        self.assertTrue(note["original_prose_unchanged"])
        self.assertEqual(note["original_content_sha256"],
                         hashlib.sha256((original+'"}').encode()).hexdigest())
        self.assertEqual(note["decoded_object_sha256"],
                         hashlib.sha256(original.encode()).hexdigest())
        self.assertEqual(model.budget.calls_reserved,1)

    def test_unexpected_trailing_text_or_other_role_does_not_get_repaired(self):
        payload=json.dumps({
            "prose":"沈砚在屋内沉默。"*20,
            "trace":{"action_quote":None,"effect_quote":None,
                     "parent_effect_quote":None},
        },ensure_ascii=False)
        for ending,role in (("NON_JSON_SUFFIX","self_scene_writing"),
                            ('"}',"craft_analysis")):
            with self.subTest(ending=ending,role=role):
                model=self.build(payload+ending)
                with self.assertRaisesRegex(
                        DeepSeekFlashError,"INVALID_JSON_RESPONSE"):
                    model.ask_json(
                        role=role,system="仅输出JSON。不能篡改正文。",
                        user="写作有限测试",max_tokens=500)
                self.assertIsNone(model.last_response_format_recovery)


class SourceOnlyTraceRepair(unittest.TestCase):
    def test_inexact_pronoun_quote_matches_unique_existing_action(self):
        action="沈砚把旧信收回袖口，在灯下停了许久。"
        mismatch="他把旧信收回袖口，在灯下停了许久。"
        effect="他终于决定明天先去查被救孩子的身份，暂时不找唐蜃。"
        prose=("深夜驿站的灯火逐渐熄灭，沈砚孤身坐在窗边，"
               "想着已经读过许多遍的父亲遗信。"
               +action+effect+
               "桌上的追查笔记仍在原处，他没有毁掉，也没有改写。"*3)
        raw=envelope(prose,mismatch,effect)
        with self.assertRaisesRegex(
                V96CausalDraftError,"WF96_ACTION_NOT_UNIQUE"):
            check_turn(raw,beat(),mode="causal_guard")
        normalized,receipt=normalize_model_source_citations(
            raw,beat())
        self.assertIsNotNone(receipt)
        self.assertEqual(json.loads(normalized)["prose"],prose)
        self.assertEqual(json.loads(normalized)["trace"]["action_quote"],
                         action[2:])
        checked=check_turn(normalized,beat(),mode="causal_guard")
        self.assertEqual(checked["receipt"]["causal_check"],
                         "EXACT_OBSERVABLE_ANCHORS_ONLY")
        self.assertEqual(checked["effect_quote"],effect)
        self.assertEqual(receipt["extra_model_calls"],0)

    def test_abbreviated_parent_quote_expands_to_original_actual_effect(self):
        first_action="沈砚从桥板上捡起掉落的铁链，握紧后抵在刀锋下面。"
        first_effect=("刀锋撞上铁链，一股力量将他的左掌震得发麻。"
                      "唐蜃险些失足，脚后跟退到桥边的裂缝旁边。")
        raw1=envelope(
            "沈砚的右臂还不能动。"+first_action+first_effect+
            "桥面上不断滴落雨水，铁链已经松散下来。"*3,
            first_action,first_effect)
        prior=check_turn(raw1,beat(kind="action"),mode="causal_guard")
        second_action="唐蜃转身去踢桥下木桩，想要暂时拉开交锋距离。"
        second_effect="沈砚趁此时机靠着护栏坐下，避免左臂伤口继续渗血。"
        raw2=envelope(
            "铁链的响声仍在桥面震动。"+second_action+second_effect+
            "两人都看不清对方的脸色，雨越下越大。"*4,
            second_action,second_effect,
            first_effect.split("。")[0]+"。")
        b=beat("t02",parent="t01",kind="action")
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "WF96_PARENT_CAUSE_NOT_ANCHORED"):
            check_turn(raw2,b,mode="causal_guard",accepted=(prior,))
        normalized,receipt=normalize_model_source_citations(
            raw2,b,accepted=(prior,))
        self.assertEqual(json.loads(normalized)["trace"][
            "parent_effect_quote"],first_effect)
        self.assertEqual(len(receipt["source_quote_replacements"]),1)
        self.assertEqual(check_turn(
            normalized,b,mode="causal_guard",accepted=(prior,))[
                "receipt"]["parent_effect_sha256"],
                hashlib.sha256(first_effect.encode()).hexdigest())

    def test_overlapping_model_trace_retains_unmodified_prose_for_review(self):
        action="他把一封旧信放进怀里，没有再同任何人解释。"
        effect="写完名字后，他把一封旧信放进怀里，没有再同任何人解释。"
        prose=("沈砚在屋里等了很久，窗外行人走得很慢，"
               "他想起父亲交代的最后几句话。"+
               effect+"这一次他没有假装已经弄清楚真凶。"*5)
        raw=envelope(prose,action,effect)
        with self.assertRaisesRegex(
                V96CausalDraftError,"ACTION_EFFECT_OVERLAP"):
            check_turn(raw,beat(),mode="causal_guard")
        recovered=review_only_model_turn(
            raw,beat(),failure_code=
            "WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED")
        self.assertEqual(recovered["prose"],prose)
        self.assertIsNone(recovered["effect_quote"])
        self.assertEqual(recovered["receipt"]["causal_check"],
                         "TRACE_REJECTED_SOURCE_PROSE_REVIEW_ONLY")
        self.assertFalse(recovered["receipt"][
            "literary_causality_independently_verified"])
        self.assertFalse(recovered["receipt"][
            "eligible_for_experience_promotion"])
        self.assertEqual(recovered["receipt"]["model_calls_for_validation"],0)

    def test_citation_failure_does_not_bypass_author_exclusion(self):
        action="他把一封旧信放进怀里，没有再同任何人解释。"
        effect="写完名字后，他把一封旧信放进怀里，没有再同任何人解释。"
        prose=("沈砚明白这封信绝对不能泄漏秘密消息。"*6+
               effect+"他没有向任何人表示自己已经知道真凶。"*3)
        raw=envelope(prose,action,effect)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "AUTHOR_CONFIRMED_KNOWLEDGE_BOUNDARY"):
            review_only_model_turn(
                raw,beat(),
                failure_code="WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED",
                author_confirmed_forbidden_phrases=("秘密消息",))

    def test_malformed_json_and_missing_parent_are_still_hard_failures(self):
        raw=envelope("沈砚听雨。"*36,None,None)
        with self.assertRaises(V96CausalDraftError):
            review_only_model_turn(
                raw[:-1],beat(),
                failure_code="WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED")
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "PARENT_NOT_WRITTEN"):
            review_only_model_turn(
                raw,beat("t02",parent="t01"),
                failure_code="WF96_PARENT_CAUSE_NOT_ANCHORED_IN_PREVIOUS_PROSE",
                accepted=())
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "NOT_AN_OPTIONAL_CITATION"):
            review_only_model_turn(
                raw,beat(),failure_code="WF96_JSON_INVALID_OR_DUPLICATE_KEYS")

    def test_live_writer_kernel_uses_recovery_without_generating_new_prose(self):
        source=inspect.getsource(AutonomousWriting.run)
        self.assertIn("normalize_model_source_citations(",source)
        self.assertIn("review_only_model_turn(",source)
        self.assertIn("unified_model_trace_review_failures",source)
        self.assertIn("unified_source_citation_normalizations",source)
        self.assertIn("model_trace_review_failures",source)


if __name__=="__main__":
    unittest.main()
