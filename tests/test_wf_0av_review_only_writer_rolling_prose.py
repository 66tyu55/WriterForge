"""0.AV REAL literary RED: B's third paragraph exists, V96 trace is REVIEW,
then G+V98 silently fell back to frozen t04/t05 and repeated opening orders.

Immutable real experiment: GitHub Actions 40323596997.
B third prose SHA256: 3f22dd574a949a74bd5004f6fb54e33d1196ea3cb561e33dfe5dde1ebf334a0f
B fourth prose SHA256: 18a742cb534521909750d9bb1fb1e2a3474d9d3b283e710a8d9984d978b9bb70
B t04/t05 skips: PREVIOUS_TRACE_REVIEW_ONLY, no V98 new author choice.
This RED tests source-only opportunity, NOT literary truth or passing the old
V96 technical trace. Review-only prose must NEVER become a verified effect,
world fact, or automatic causal-parent promotion.
"""
from __future__ import annotations
import json
import unittest
from copy import deepcopy
from writerforge.v96_causal_turns import (
    check_turn,review_only_model_turn,canonical,digest,
)
from writerforge.v98_rolling_causal_planner import (
    g_source_replan_eligibility,prepare_replan_instructions,validate_replan,
    V98RollingPlanError,
)
from test_v96_causal_turns import (
    ACTION1,prose1,response,plan,
)
from test_v98_rolling_causal_planner import proposed,raw

ALT="他本来答应朋友当夜入城"

def invalid_trace_but_real_writer_prose():
    return review_only_model_turn(
        response(prose1(),ACTION1,ACTION1),plan()[0],
        failure_code="WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED",
    )

class OptInReviewOnlyWriterPerspective(unittest.TestCase):
    def test_old_G_baseline_source_does_not_claim_cause(self):
        turn=invalid_trace_but_real_writer_prose()
        doc=g_source_replan_eligibility((turn,))
        self.assertFalse(doc["eligible"])
        self.assertEqual(doc["reason"],"PREVIOUS_TRACE_REVIEW_ONLY")

    def test_same_writer_may_rethink_next_from_actual_review_only_prose(self):
        turn=invalid_trace_but_real_writer_prose()
        elig=g_source_replan_eligibility((turn,),allow_prose_only=True)
        self.assertTrue(elig["eligible"])
        self.assertTrue(elig["prose_only_unverified"])
        self.assertEqual(elig["source_basis_kind"],"REVIEW_ONLY_PROSE_AUTHOR_ONLY")
        self.assertFalse(elig["causal_truth_verified"])
        prompt=prepare_replan_instructions(
            accepted=(turn,),seed_next_beat=plan()[1],
            allowed_actor_names=("少年","女子"),allow_g_prose_only=True)
        self.assertIn(prose1()[-110:],prompt)
        self.assertIn("不得把",prompt)
        self.assertIn("仅供复核",prompt)
        p=proposed(basis=ALT,pressure=None,cost=None)
        p["next_turn"]["goal"]="女子重新考虑是否先探查旧堤，不用重复过桥决定"
        beat,receipt=validate_replan(
            raw(p),accepted=(turn,),accepted_beats=(plan()[0],),
            seed_next_beat=plan()[1],
            allowed_actor_names=("少年","女子"),
            allow_g_prose_only=True)
        self.assertEqual(beat["goal"],p["next_turn"]["goal"])
        self.assertEqual(beat["causal_parent"],"t01")
        self.assertEqual(receipt["source_basis_kind"],"REVIEW_ONLY_PROSE_AUTHOR_ONLY")
        self.assertTrue(receipt["source_parent_relation_review_required"])
        self.assertFalse(receipt["source_basis_is_observed_effect"])
        self.assertFalse(receipt["source_parent_causal_relation_verified"])
        self.assertFalse(receipt["narrative_semantics_independently_verified"])
        self.assertFalse(receipt["character_knowledge_promoted_to_KNOWN"])
        self.assertEqual(receipt["canon_or_factjournal_writes"],0)
        self.assertEqual(receipt["grounded_prior_prose_sha256"],digest(
            turn["prose"].encode("utf8")))

    def test_forged_or_repeated_prior_quotes_not_rescued(self):
        turn=invalid_trace_but_real_writer_prose()
        false=proposed(basis="他已经找到身后全部真凶",pressure=None,cost=None)
        with self.assertRaises(V98RollingPlanError):
            validate_replan(raw(false),accepted=(turn,),
                accepted_beats=(plan()[0],),seed_next_beat=plan()[1],
                allowed_actor_names=("少年","女子"),allow_g_prose_only=True)
        prior=deepcopy(turn)
        prior["prose"]+="，"+ALT
        prior["receipt"]["prose_sha256"]=digest(prior["prose"].encode("utf8"))
        prior["receipt"]["receipt_sha256"]=digest(canonical(
            {k:v for k,v in prior["receipt"].items() if k!="receipt_sha256"}))
        with self.assertRaises(V98RollingPlanError):
            validate_replan(raw(proposed(basis=ALT,pressure=None,cost=None)),
                accepted=(prior,),accepted_beats=(plan()[0],),
                seed_next_beat=plan()[1],allowed_actor_names=("少年","女子"),
                allow_g_prose_only=True)

    def test_recent_signed_prose_not_old_static_beats_must_inform_t04_choice(self):
        """0.AV actual B+: t04 re-cut a signal already cut in t01.

        The real t04 V98 prompt had only t03's actual prose and the
        initial stale seed. The model couldn't see the literal t01 action.
        Expose a small, source-SHA-verified prior prose window instead of
        inventing an item state or enforcing 'no repeats' instructions.
        """
        from test_v96_causal_turns import prose2,ACTION2,EFFECT1,EFFECT2
        beat1,beat2=plan()
        a=check_turn(response(prose1(),ACTION1,EFFECT1),beat1,
                     mode="causal_guard")
        b=check_turn(response(prose2(),ACTION2,EFFECT2,EFFECT1),
                     beat2,mode="causal_guard",accepted=(a,))
        third_beat={"id":"t03","kind":"dialogue","actor":"少年",
                    "goal":"人物暂时失去回话后，仍需记得先前已经做过的动作",
                    "causal_parent":"t02","craft_focus":["dialogue"]}
        third=review_only_model_turn(response(
            "三更时女子已经停下与少年争论，驿站窗纸发出响声。"
            "他们听见河边有人叫了一声，却没有看见到底是谁。"
            "从此刻到风雨停下，他们仍未得到河边人的回应，既不能断定来人已经过桥，"
            "也不能把刚才听见的声音当作通行结果；屋檐下的人都不知道下一步该怎么走。",
            ACTION1,None,EFFECT2),third_beat,
            failure_code="WF96_PARTIAL_ACTION_EFFECT_NOT_ALLOWED",
            accepted=(a,b))
        next_seed={"id":"t04","kind":"decision","actor":"女子",
                   "goal":"女子在当前失联与未知条件下决定下一步行动",
                   "causal_parent":"t03","craft_focus":["detail"]}
        prompt=prepare_replan_instructions(
            accepted=(a,b,third),seed_next_beat=next_seed,
            allowed_actor_names=("少年","女子"),
            allow_g_prose_only=True)
        self.assertIn(ACTION1,prompt)
        self.assertIn(ACTION2,prompt)
        self.assertIn('下一事件编号必须为 t04',prompt)
        self.assertIn('不代表已确认因果',prompt)
        self.assertLess(len(prompt),3101)

        tampered=deepcopy(a)
        tampered["prose"]+="伪造先前已经开阀成功"
        with self.assertRaises(V98RollingPlanError):
            prepare_replan_instructions(
                accepted=(tampered,b,third),seed_next_beat=next_seed,
                allowed_actor_names=("少年","女子"),
                allow_g_prose_only=True)

    def test_tampered_old_original_hash_fail_closed(self):
        turn=invalid_trace_but_real_writer_prose()
        turn["prose"]+="假后果"
        with self.assertRaises(V98RollingPlanError):
            g_source_replan_eligibility((turn,),allow_prose_only=True)

    def test_legitimate_quiet_source_supports_choices_not_facts(self):
        beat={"id":"t01","kind":"quiet","actor":"少年",
              "goal":"雨夜等候时观察木桥并思索另一个去处",
              "causal_parent":None,"craft_focus":["restraint"]}
        prose=("雨滴从瓦檐落在水缸里，响声慢得像一只旧钟。"
               "少年默默擦去木盒上的泥渍，迟迟没有推开那扇门。"
               "女子站在院外，没再追问他为什么选择绕路。"
               "远处的船笛声渐渐消失，窗前的灯也暗下来。")
        turn=check_turn(response(prose,None,None),beat,mode="causal_guard")
        target={"id":"t02","kind":"decision","actor":"女子",
                "goal":"女子根据新一轮真实对话决定是否先去找船工",
                "causal_parent":"t01","craft_focus":["detail"]}
        self.assertFalse(g_source_replan_eligibility((turn,))["eligible"])
        self.assertEqual(
            g_source_replan_eligibility((turn,),allow_prose_only=True)["source_basis_kind"],
            "QUIET_PROSE_AUTHOR_ONLY")
        model={
          "next_turn":target,
          "basis_effect_quote":"少年默默擦去木盒上的泥渍",
          "pressure_quote":None,"cost_quote":None,
          "unresolved_question":"船工什么时候回来还没有人知道。",
          "reason_for_shift":"之前没有确切行动后果，先让女子选择核对渡口情况。",
        }
        chosen,receipt=validate_replan(json.dumps(model,ensure_ascii=False),
            accepted=(turn,),accepted_beats=(beat,),
            seed_next_beat=target,allowed_actor_names=("少年","女子"),
            allow_g_prose_only=True)
        self.assertEqual(chosen["id"],"t02")
        self.assertEqual(receipt["source_basis_kind"],"QUIET_PROSE_AUTHOR_ONLY")
        self.assertFalse(receipt["source_parent_causal_relation_verified"])

if __name__=="__main__":
    unittest.main()
