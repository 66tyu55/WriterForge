"""Unified-core source-first scene outcome / payoff review tests.

A payoff cannot be proven by a genre label, keyword, writer's claimed trace
or model self-evaluation. Generic evidence can be source-anchored but remains
an UNVERIFIED literary proposal. Only exact long-replay is hard rejected.
"""
import hashlib
import inspect
import json
import tempfile
from pathlib import Path
import unittest

from writerforge.narrative_core import (
    audit_scene_delivery,validate_scene_delivery_contract,
    NarrativeCoreError,
)
from writerforge.writing_assist import AutonomousWriting,WritingExecutionError

HUMOR_CONTRACT={
    "id":"umbrella-comedy","function":"REVERSAL",
    "due":"THIS_SCENE","author_confirmed":True,
    "story_question":"冒充巡察使取回雨伞的尝试，最终造成了什么新误会",
}
OPEN_CONTRACT={
    "id":"secret-long-arc","function":"QUESTION",
    "due":"DEFERRED","author_confirmed":True,
    "story_question":"旧案幕后的真相究竟是什么，是否需要延后揭示",
}


def long_original():
    # Deliberately original fixture, not an existing user/manuscript sample.
    chunks=[]
    for i in range(24):
        chunks.append(
            f"第{i}次换岗，沈砚从廊下望向石桥，抬手碰了碰衣袖上的雨迹。"
            "他在犹豫是否把证物交出去，但从未认定唐蜃就是凶手。"
        )
    return "".join(chunks)


class SourcePayoffAudit(unittest.TestCase):
    def test_explicitly_due_payoff_is_unverified_not_false_success(self):
        text=long_original()
        report=audit_scene_delivery(
            prose=text,scene_goal="沈砚取回自己的伞，同时引发新的误会",
            scene_kind="chapter",
            author_delivery_contract=HUMOR_CONTRACT)
        self.assertFalse(report["blocked"])
        self.assertTrue(report["needs_review"])
        self.assertIn("WFCORE_DUE_SCENE_PAYOFF_NOT_YET_VERIFIED",
                      report["review_findings"])
        self.assertFalse(report["scene_function_verified"])
        self.assertTrue(report["open_story_questions_are_permitted"])
        self.assertFalse(report["literary_quality_verified"]
                         if "literary_quality_verified" in report else
                         report["scene_function_verified"])
        self.assertEqual(report["model_calls"],0)
        self.assertEqual(report["canon_writes"],0)

    def test_accepted_model_effect_quote_is_not_independent_payoff_proof(self):
        source=("沈砚拿起一把雨伞，试图从宴席里逃走。"
                "他发现拿的是唐蜃的伞，众人的目光又投过来。")
        receipt=audit_scene_delivery(
            prose=source,scene_goal="沈砚取回雨伞却引出新误会",
            scene_kind="reversal",
            anchored_effect_quotes=("他发现拿的是唐蜃的伞，众人的目光又投过来。",),
            author_delivery_contract=HUMOR_CONTRACT)
        self.assertEqual(len(receipt["source_effect_quote_anchors"]),1)
        self.assertIn("WFCORE_DUE_SCENE_PAYOFF_NOT_YET_VERIFIED",
                      receipt["review_findings"])
        self.assertFalse(receipt["scene_function_verified"])
        self.assertTrue(receipt["source_effect_quote_anchors"][0][
            "citation_from_model_trace_not_semantic_truth"])

    def test_optional_reviewer_proposal_is_tied_to_source_but_unverified(self):
        source=("沈砚伸手抓住柜台旁的油纸伞。"
                "他忽然看见两把一模一样的伞，原来拿错了唐蜃的那一把。")
        result=audit_scene_delivery(
            prose=source,scene_goal="把取伞的计划变成新的误会",
            scene_kind="reversal",
            author_delivery_contract=HUMOR_CONTRACT,
            reviewer_proposal={
                "judgment":"TRANSFORMED",
                "action_quote":"沈砚伸手抓住柜台旁的油纸伞。",
                "outcome_quote":"他忽然看见两把一模一样的伞，原来拿错了唐蜃的那一把。",
            })
        self.assertFalse(result["blocked"])
        self.assertFalse(result["scene_function_verified"])
        self.assertIsNotNone(result["independent_review_proposal"])
        self.assertEqual(result["independent_review_proposal"][
            "suggested_function_status"],"TRANSFORMED")
        self.assertFalse(result["needs_review"])
        self.assertNotIn("WFCORE_DUE_SCENE_PAYOFF_NOT_YET_VERIFIED",
                         result["review_findings"])

    def test_source_quote_not_just_model_judgment_is_required(self):
        text="沈砚坐在席间，眼看掌柜和唐蜃走进大门。"
        with self.assertRaisesRegex(NarrativeCoreError,
                                     "REVIEW_QUOTE_NOT_SOURCE_PROVEN"):
            audit_scene_delivery(
                prose=text,scene_goal="伞被拿错",
                scene_kind="decision",
                reviewer_proposal={
                    "judgment":"CHANGED",
                    "action_quote":"沈砚伸手去拿伞。",
                    "outcome_quote":"他才发现自己拿错了。",
                })

    def test_deliberately_deferred_mystery_is_not_forced_to_settle(self):
        result=audit_scene_delivery(
            prose="叶青梧听见矿井传来三次敲击，仍找不到敲击者。",
            scene_goal="调查矿井的未知声源",
            scene_kind="quiet",author_delivery_contract=OPEN_CONTRACT)
        self.assertFalse(result["blocked"])
        self.assertFalse(result["needs_review"])
        self.assertTrue(result["open_story_questions_are_permitted"])
        self.assertEqual(result["registered_delivery_contract"]["due"],
                         "DEFERRED")

    def test_psychological_stillness_does_not_force_a_physical_action(self):
        text=("沈砚把信纸铺平，想起父亲去世那天的雨。"
              "他暂时没有出门，只是决定明日去查医院的旧档案。")
        result=audit_scene_delivery(
            prose=text,scene_goal="面临是否复仇的困境",
            scene_kind="quiet")
        self.assertFalse(result["blocked"])
        self.assertFalse(result["needs_review"])
        self.assertFalse(result["scene_function_verified"])

    def test_source_effect_may_repeat_without_false_hard_failure(self):
        q="叶青梧把伞递给沈砚，两人都没有认出藏在门后的唐蜃。"
        r=audit_scene_delivery(
            prose=q+q,scene_goal="交接雨伞",
            scene_kind="action",anchored_effect_quotes=(q,))
        self.assertFalse(r["blocked"]) # short refrain, no full long replay
        self.assertTrue(r["needs_review"])
        self.assertIn("WFCORE_SCENE_EFFECT_ANCHOR_NOT_UNIQUE",
                      r["review_findings"])
        self.assertEqual(len(r["source_effect_quote_anchors"]),0)

    def test_source_first_long_replay_has_hard_stop_even_if_reviewer_says_good(self):
        single=long_original()
        report=audit_scene_delivery(
            prose=single+"\n\n"+single,
            scene_goal="取伞的误会引发反转",
            scene_kind="chapter",
            author_delivery_contract=HUMOR_CONTRACT)
        self.assertTrue(report["blocked"])
        self.assertEqual(report["long_prose_replay"]["finding"],
                         "WFCORE_ENTIRE_LONG_PROSE_REPEATED")
        self.assertFalse(report["scene_function_verified"])

    def test_slightly_changed_distant_long_passage_is_review_only(self):
        first="沈砚在长廊深处查看旧账本，雨水敲打窗格。"*8
        second="叶青梧终于问出了那条失踪的名单；掌柜从后院拿来火盆。"*6
        changed=first.replace("旧账本","破账本",1)
        r=audit_scene_delivery(
            prose=first+"。"+second+"。"+changed,
            scene_goal="人物在行动中缓慢重认识",
            scene_kind="chapter")
        self.assertFalse(r["blocked"])
        self.assertFalse(r["scene_function_verified"])
        # Whether thresholds trigger review is deterministic and conservative,
        # not proof of semantic repetition.
        self.assertEqual(r["model_calls"],0)

    def test_not_author_confirmed_contract_is_rejected_before_writing(self):
        bad=dict(HUMOR_CONTRACT)
        bad["author_confirmed"]=False
        with self.assertRaisesRegex(
                NarrativeCoreError,"CONTRACT_UNTRUSTED"):
            validate_scene_delivery_contract(bad)
        class FakeAssist:
            project_id="wf-test"
            scene_id="chapter-2"
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"never-create"
            with self.assertRaisesRegex(
                    WritingExecutionError,
                    "CONTRACT_UNTRUSTED"):
                AutonomousWriting(FakeAssist()).run(
                    outline="测试玄幻小说长篇写作，人物面对秘密与真实选择。",
                    chapter_goals=["沈砚面对唐蜃时要判断是否交代密令"],
                    output_dir=out,
                    draft_mode="continuity_guard",
                    scene_delivery_contracts=(bad,))
            self.assertFalse(out.exists())

    def test_wrong_mode_cannot_silently_ignore_scene_due_policy(self):
        class FakeAssist:
            project_id="wf-test"
            scene_id="chapter-2"
        with self.assertRaisesRegex(
                WritingExecutionError,"TEXT_CONTINUITY_ONLY_PARAMETERS"):
            AutonomousWriting(FakeAssist()).run(
                outline="测试玄幻小说长篇写作，人物面对秘密与真实选择。",
                chapter_goals=["沈砚面对唐蜃时要判断是否交代密令"],
                output_dir="/tmp/wf_scene_contract_inert_path",
                draft_mode="single",
                scene_delivery_contracts=(HUMOR_CONTRACT,))

    def test_real_turn_acceptance_checks_scene_delivery_not_only_trace(self):
        body=inspect.getsource(AutonomousWriting.run)
        assert "turn_delivery=audit_scene_delivery(" in body
        assert body.index("turn_delivery=audit_scene_delivery(") < body.index(
            "accepted_turns.append(evidence)")
        assert "whole_delivery=audit_scene_delivery(" in body
        assert body.index("whole_delivery=audit_scene_delivery(") < body.index(
            "saved=save_candidate(packet,body")
        assert '"unified_scene_delivery_turn_checks"' in body
        assert '"unified_scene_delivery_chapter"' in body
        assert "author_delivery_contract=chapter_contract" in body

    def test_receipt_signature_and_novel_text_not_leaked(self):
        original="沈砚从桌上拿起密令。叶青梧听见窗外有脚步声。"
        r=audit_scene_delivery(
            prose=original,scene_goal="人物找到密令",
            scene_kind="action")
        digest=r["receipt_sha256"]
        data={k:v for k,v in r.items() if k!="receipt_sha256"}
        canon=hashlib.sha256(json.dumps(
            data,sort_keys=True,ensure_ascii=False,
            separators=(",",":")).encode()).hexdigest()
        self.assertEqual(digest,canon)
        self.assertNotIn(original,json.dumps(r,ensure_ascii=False))
        self.assertTrue(r["model_claim_not_promoted_to_fact"])
        self.assertEqual(r["canon_writes"],0)


if __name__=="__main__":
    unittest.main()
