"""V97 original-fiction real A/B/C protocol tests. No network/model/R2.

Tests freeze shared scenario, B/C same three events, budget and truthful
limitations before any paid request. Existing V96 tests exercise the real
AutonomousWriting + VerifiedWritingFlow + local Xuehai candidate save code.
"""
from __future__ import annotations

from copy import deepcopy
import json
import unittest
from pathlib import Path

from writerforge.v97_real_longform_abc_protocol import (
    ARM_ORDER,ARMS,MAX_PROVIDER_REQUESTS,A_MAX_OUTPUT,
    TURN_MAX_OUTPUT,MAX_RESERVED_OUTPUT_TOKENS,
    MAX_CONSERVATIVE_REQUEST_BUDGET,TARGET_CHARS,
    FROZEN_PLAN,FROZEN_TURNS,OUTLINE,CHAPTER_GOAL,
    ACTOR_KNOWLEDGE,MODEL,PROVIDER,canonical,sha,
    shared_story,make_precommit,frozen_plan_json,
    frozen_turns_json,request_bound,mechanical_prose_fields,
)
from writerforge.v96_causal_turns import parse_turn_outline


class V97ProtocolTests(unittest.TestCase):
    def test_one_shot_seven_provider_requests_and_exact_reserved_max(self):
        self.assertEqual(ARM_ORDER,("single","split_only","causal_guard"))
        self.assertEqual([ARMS[k] for k in ARM_ORDER],["A","B","C"])
        self.assertEqual(MAX_PROVIDER_REQUESTS,7)
        self.assertEqual(MAX_RESERVED_OUTPUT_TOKENS,
                         A_MAX_OUTPUT+6*TURN_MAX_OUTPUT)
        self.assertLess(MAX_RESERVED_OUTPUT_TOKENS,
                        MAX_CONSERVATIVE_REQUEST_BUDGET)
        self.assertEqual(MODEL,"deepseek-flash")
        self.assertEqual(PROVIDER,"deepseek")

    def test_shared_plan_has_no_hidden_source_or_grade(self):
        scope=shared_story()
        self.assertIn(CHAPTER_GOAL,scope)
        self.assertIn(ACTOR_KNOWLEDGE,scope)
        self.assertIn("沈砚",scope)
        self.assertIn("阿蘅",scope)
        self.assertNotIn("第15章经验",scope)
        self.assertTrue(1000<=TARGET_CHARS<=1800)
        self.assertEqual(json.loads(frozen_plan_json()),FROZEN_PLAN)
        self.assertEqual(json.loads(frozen_turns_json()),FROZEN_TURNS)

    def test_same_exact_three_beats_for_B_and_C(self):
        beats=parse_turn_outline(frozen_turns_json())
        self.assertEqual([x["id"] for x in beats],["t01","t02","t03"])
        self.assertEqual([x["causal_parent"] for x in beats],
                         [None,"t01","t02"])
        self.assertEqual([x["kind"] for x in beats],
                         ["action","decision","decision"])
        self.assertEqual(len(beats),3)
        self.assertTrue(all(len(x["craft_focus"])<=2 for x in beats))

    def test_original_fiction_and_unknown_motive_remain_open(self):
        self.assertIn("守桥人的真实动机留给后文",OUTLINE)
        self.assertIn("不可能预知今晚",ACTOR_KNOWLEDGE)
        self.assertIn("同一傍晚到夜间",ACTOR_KNOWLEDGE)
        self.assertIn("时间压力",CHAPTER_GOAL)

    def test_precommit_sha_deterministic_and_denies_promotion(self):
        a=make_precommit()
        b=make_precommit()
        self.assertEqual(a,b)
        self.assertEqual(sha(canonical(a)),sha(canonical(b)))
        self.assertEqual(a["max_paid_requests"],7)
        self.assertTrue(a["same_frozen_turns_for_B_and_C"])
        self.assertFalse(a["independent_human_literary_review"])
        self.assertTrue(a["automatic_retry_and_autopromotion_disabled"])
        self.assertTrue(a["r2_existing_15_chapter_learn_chain_untouched"])
        self.assertFalse(a["real_user_novel_source_transmitted"])
        self.assertTrue(a["all_unaccepted_original_fiction"])

    def test_conservative_request_estimate_is_explicit_and_bounded(self):
        small=request_bound("只输出JSON","正文原创场景",A_MAX_OUTPUT)
        large=request_bound("只输出JSON","正文原创场景"*100,
                            A_MAX_OUTPUT)
        self.assertGreater(large,small)
        self.assertGreater(small,A_MAX_OUTPUT)
        self.assertLess(small,MAX_CONSERVATIVE_REQUEST_BUDGET)

    def test_model_json_no_invented_extra_fields_or_fake_grade(self):
        data={"prose":"沈砚知道渡口已被封闭，但谁收走竹牌仍然未知。"*6}
        self.assertEqual(mechanical_prose_fields(data,is_turn=False),
                         data["prose"])
        with self.assertRaisesRegex(ValueError,"SINGLE_SCHEMA"):
            mechanical_prose_fields({**data,"grade":100},is_turn=False)
        with self.assertRaisesRegex(ValueError,"TURN_SCHEMA"):
            mechanical_prose_fields(data,is_turn=True)
        with self.assertRaisesRegex(ValueError,"MODEL_SINGLE"):
            mechanical_prose_fields({"prose":data["prose"],
                                    "literary_quality":True},is_turn=False)

    def test_real_runner_source_compiles_without_executing_or_network(self):
        # The actual Railway paid entrypoint is compiled but NEVER run
        # by the offline suite. A syntax issue must be caught before R2
        # precommit or any API billing.
        path=Path(__file__).parents[1]/"wf_railway_v97_real_original_longform_abc.py"
        source=path.read_text(encoding="utf8")
        compile(source,str(path),"exec")
        self.assertIn("WF97_DUPLICATE_PRECOMMIT_REFUSE_TO_REBILL",source)
        self.assertIn("WF97_TOTAL_REAL_MODEL_CALL_OR_TOKEN_CEILING",source)
        self.assertIn("model_generated_plan",source)
        self.assertIn("writer._put_content(rr)",source)

    def test_invalid_short_corrupt_or_misleading_response_rejected(self):
        with self.assertRaisesRegex(ValueError,"PROSE_LENGTH"):
            mechanical_prose_fields({"prose":"几句话结束了。"},
                                    is_turn=False)
        with self.assertRaisesRegex(ValueError,"PROSE_LENGTH"):
            mechanical_prose_fields({"prose":"错码\ufffd"*100},
                                    is_turn=False)
        with self.assertRaisesRegex(ValueError,"NOT_JSON_OBJECT"):
            mechanical_prose_fields(["not", "json"],is_turn=False)
        line="少年站在桥前犹豫。他低头翻看旧账，却没有证据。"*7
        doc={"prose":line,
             "trace":{"action_quote":"沈砚决心找船工",
                      "effect_quote":"他后来撤退",
                      "parent_effect_quote":None}}
        # V97 here checks output TYPE only; V96 C is the actual quote gate.
        self.assertEqual(mechanical_prose_fields(doc,is_turn=True),line)


if __name__=="__main__":
    unittest.main()
