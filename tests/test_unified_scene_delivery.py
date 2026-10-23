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
        self.assertTrue(result["needs_review"])
        self.assertIn("WFCORE_DUE_SCENE_PAYOFF_NOT_YET_VERIFIED",
                      result["review_findings"])
        self.assertTrue(result["independent_review_proposal"][
            "model_or_reviewer_cannot_settle_story_obligation"])

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
        assert '"unified_scene_function_review_needed"' in body
        assert '"unified_scene_function_review_findings"' in body
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



class CrossChapterDeliveryDebt(unittest.TestCase):
    """Synthetic candidate fixtures only; original seven-genre Atria sealed."""
    PROJECT="scene-debt-probe"
    STREAM="novel-stream"
    GOAL="沈砚面对唐蜃的误解，决定是否改变查案计划"
    QUESTION="沈砚是否会违背查案大纲，自主选择如何面对唐蜃的误解"
    CONTRACT={
        "id":"inner-choice-arc","function":"CHOICE","due":"THIS_SCENE",
        "author_confirmed":True,"story_question":QUESTION,
    }
    PROSE=(
        "沈砚第一次没有回信，而是决定再查一夜旧账。"
        "窗外灯火还亮着，他知道自己要承担被唐蜃误解的代价。"
    )
    ACTION="沈砚第一次没有回信，而是决定再查一夜旧账。"
    OUTCOME="窗外灯火还亮着，他知道自己要承担被唐蜃误解的代价。"

    def previous_graph(self):
        from writerforge.narrative_core import new_graph
        return new_graph(project_id=self.PROJECT,scene_id=self.STREAM)

    def candidate_graph(self,root,prose=None,prev=None):
        from writerforge.narrative_core import (
            advance_graph,record_chapter_memory,
        )
        if prose is None:prose=self.PROSE
        if prev is None:prev=self.previous_graph()
        chapter=prev["chapter_index"]+1
        graph=advance_graph(
            prev,project_id=self.PROJECT,scene_id=self.STREAM,
            chapter_index=chapter,prose=prose,events=())
        file=Path(root)/("candidate-"+str(chapter)+".md")
        file.write_text(prose,encoding="utf8")
        graph=record_chapter_memory(
            graph,project_id=self.PROJECT,scene_id=self.STREAM,
            chapter_index=chapter,source_path=str(file),prose=prose)
        return graph

    def receipt(self,prose=None,contract=None):
        return audit_scene_delivery(
            prose=prose or self.PROSE,scene_goal=self.GOAL,
            scene_kind="chapter",
            author_delivery_contract=contract or self.CONTRACT)

    def review(self,decision="CARRY_FORWARD",**changes):
        row={
            "decision":decision,"author_confirmed":True,
            "candidate_read":True,"owner":"沈砚","target":"唐蜃",
            "reason":"亲自读过正文，按人物选择保留或结清场景问题",
            "action_quote":None,"outcome_quote":None,
        }
        if decision=="SETTLE_WITH_SOURCE":
            row.update(action_quote=self.ACTION,outcome_quote=self.OUTCOME)
        row.update(changes)
        return row

    def apply(self,graph,review,prose=None,contract=None,receipt=None):
        from writerforge.narrative_core import review_scene_delivery_on_graph
        return review_scene_delivery_on_graph(
            graph,project_id=self.PROJECT,scene_id=self.STREAM,
            prose=prose or self.PROSE,scene_goal=self.GOAL,
            scene_kind="chapter",
            author_delivery_contract=contract or self.CONTRACT,
            author_review=review,
            delivery_receipt=receipt or self.receipt(
                prose=prose,contract=contract))

    def test_contract_is_proposal_only_no_automatic_graph_thread(self):
        from writerforge.narrative_core import propose_scene_delivery_debt
        prior=self.previous_graph()
        proposal=propose_scene_delivery_debt(
            prior,project_id=self.PROJECT,scene_id=self.STREAM,
            chapter_index=1,prose=self.PROSE,
            scene_goal=self.GOAL,scene_kind="chapter",
            author_delivery_contract=self.CONTRACT,
            delivery_receipt=self.receipt())
        self.assertEqual(proposal["status"],"NOT_REGISTERED")
        self.assertEqual(proposal["auto_thread_writes"],0)
        self.assertEqual(proposal["canon_writes"],0)
        self.assertNotIn(proposal["thread_key"],prior["nodes"])
        self.assertEqual(proposal["candidate_prose_sha256"],
                         hashlib.sha256(self.PROSE.encode()).hexdigest())

    def test_reviewed_unpaid_promise_survives_resume_and_next_chapter(self):
        from writerforge.narrative_core import (
            schedule,advance_graph,
        )
        from writerforge.v117_continuity_trace import make_resume,read_resume
        from writerforge.v114_external_story_state import external_temporal_step
        from writerforge.narrative_core import review_scene_delivery_resume
        with tempfile.TemporaryDirectory() as folder:
            graph=self.candidate_graph(folder)
            unchanged_sha=graph["receipt_sha256"]
            carried=self.apply(graph,self.review())
            self.assertEqual(graph["receipt_sha256"],unchanged_sha)
            self.assertEqual(len(graph["nodes"]),0)
            node=next(n for n in carried["nodes"].values()
                      if n["kind"]=="THREAD")
            self.assertEqual(node["props"]["status"],"OPEN")
            self.assertEqual(node["props"]["truth_scope"],"AUTHOR_INTENT")
            self.assertTrue(node["props"]["past_original_due"])
            self.assertEqual(carried["canon_writes"],0)
            self.assertEqual(
                carried["memory"]["hot"][-1]["source_sha256"],
                hashlib.sha256(self.PROSE.encode()).hexdigest())
            packet=make_resume(
                project_id=self.PROJECT,scene_id=self.STREAM,
                chapter_index=1,
                checkpoint=external_temporal_step(
                    self.PROSE,cast=("沈砚","唐蜃")),
                unified_narrative_core=graph)
            reviewed_resume=review_scene_delivery_resume(
                packet,project_id=self.PROJECT,scene_id=self.STREAM,
                prose=self.PROSE,scene_goal=self.GOAL,
                scene_kind="chapter",
                author_delivery_contract=self.CONTRACT,
                author_review=self.review())
            read_resume(reviewed_resume,project_id=self.PROJECT,
                        scene_id=self.STREAM)
            self.assertEqual(reviewed_resume["unified_narrative_core"],
                             carried)
            self.assertFalse(reviewed_resume["author_accepted"])
            self.assertNotIn("v123_open_character_arc",reviewed_resume)
            lanes=schedule(
                carried,project_id=self.PROJECT,scene_id=self.STREAM,
                chapter_index=2,
                beat={"kind":"decision","actor":"沈砚",
                      "goal":"沈砚不愿按计划向唐蜃道歉"})
            self.assertIn("作者审阅的未偿写作意图",
                          lanes["required_context"])
            self.assertIn(self.QUESTION,lanes["required_context"])
            other=schedule(
                carried,project_id=self.PROJECT,scene_id=self.STREAM,
                chapter_index=2,
                beat={"kind":"decision","actor":"叶青梧",
                      "goal":"叶青梧在沈砚与唐蜃面前独自判断局势"})
            self.assertNotIn(self.QUESTION,other["required_context"])
            still=advance_graph(
                carried,project_id=self.PROJECT,scene_id=self.STREAM,
                chapter_index=2,
                prose="沈砚收起旧信，尚未对唐蜃解释自己的计划。")
            self.assertEqual(node["props"]["status"],"OPEN")
            self.assertEqual(
                next(n for n in still["nodes"].values()
                     if n["kind"]=="THREAD")["props"]["status"],"OPEN")
            self.assertEqual(still["canon_writes"],0)

    def test_source_anchored_mental_choice_can_be_settled_by_author(self):
        from writerforge.narrative_core import schedule
        with tempfile.TemporaryDirectory() as folder:
            graph=self.candidate_graph(folder)
            done=self.apply(graph,self.review("SETTLE_WITH_SOURCE"))
            thread=next(n["props"] for n in done["nodes"].values()
                        if n["kind"]=="THREAD")
            self.assertEqual(thread["status"],"SETTLED_AUTHOR_REVIEW_ONLY")
            self.assertFalse(thread["independent_literary_payoff_verified"])
            self.assertTrue(thread["candidate_only_not_story_canon"])
            self.assertEqual(done["canon_writes"],0)
            self.assertEqual(schedule(
                done,project_id=self.PROJECT,scene_id=self.STREAM,
                chapter_index=2,
                beat={"kind":"decision","actor":"沈砚",
                      "goal":"沈砚与唐蜃讨论旧案"})["required_context"],"")

    def test_unreviewed_model_effect_quote_cannot_settle_or_open(self):
        with tempfile.TemporaryDirectory() as folder:
            graph=self.candidate_graph(folder)
            fake=self.review("SETTLE_WITH_SOURCE",author_confirmed=False)
            with self.assertRaisesRegex(
                NarrativeCoreError,"SEPARATE_AUTHOR_REVIEW_REQUIRED"):
                self.apply(graph,fake)
            fake=self.review("SETTLE_WITH_SOURCE",candidate_read=False)
            with self.assertRaisesRegex(
                NarrativeCoreError,"SEPARATE_AUTHOR_REVIEW_REQUIRED"):
                self.apply(graph,fake)
            self.assertEqual(len(graph["nodes"]),0)

    def test_source_and_contract_tamper_refused(self):
        from writerforge.narrative_core import propose_scene_delivery_debt
        before=self.previous_graph()
        old=self.receipt()
        forged=dict(old,prose_sha256="0"*64)
        with self.assertRaisesRegex(
                NarrativeCoreError,"RECEIPT_SOURCE_OR_CONTRACT_MISMATCH"):
            propose_scene_delivery_debt(
                before,project_id=self.PROJECT,scene_id=self.STREAM,
                chapter_index=1,prose=self.PROSE,scene_goal=self.GOAL,
                scene_kind="chapter",
                author_delivery_contract=self.CONTRACT,
                delivery_receipt=forged)
        with tempfile.TemporaryDirectory() as folder:
            graph=self.candidate_graph(folder)
            with self.assertRaisesRegex(
                    NarrativeCoreError,"RECEIPT_SOURCE_OR_CONTRACT_MISMATCH"):
                self.apply(graph,self.review(),receipt=forged)
            with self.assertRaisesRegex(
                    NarrativeCoreError,"SAVED_EXACT_CANDIDATE"):
                self.apply(graph,self.review(),
                           prose=self.PROSE+"被添加的额外一句。")

    def test_duplicate_anchor_and_hypothetical_cannot_settle(self):
        with tempfile.TemporaryDirectory() as folder:
            graph=self.candidate_graph(folder)
            bad=self.review("SETTLE_WITH_SOURCE",
                            action_quote="沈砚绝没有做出的行动。",
                            outcome_quote=self.OUTCOME)
            with self.assertRaisesRegex(
                    NarrativeCoreError,"UNIQUE_ORDERED_SOURCE"):
                self.apply(graph,bad)
            reverse=self.review("SETTLE_WITH_SOURCE",
                                action_quote=self.OUTCOME,
                                outcome_quote=self.ACTION)
            with self.assertRaisesRegex(
                    NarrativeCoreError,"UNIQUE_ORDERED_SOURCE"):
                self.apply(graph,reverse)
            with self.assertRaisesRegex(
                    NarrativeCoreError,"DEFER_OR_ABANDON_CANNOT_FAKE_PAYOFF"):
                self.apply(graph,self.review(
                    "CARRY_FORWARD",action_quote=self.ACTION))

    def test_deferred_question_is_open_not_automatic_payoff(self):
        contract=dict(self.CONTRACT,due="DEFERRED",
                      id="non-immediate-question")
        with tempfile.TemporaryDirectory() as folder:
            graph=self.candidate_graph(folder)
            r=self.receipt(contract=contract)
            self.assertFalse(r["needs_review"])
            carried=self.apply(graph,self.review(),contract=contract)
            node=next(n["props"] for n in carried["nodes"].values()
                      if n["kind"]=="THREAD")
            self.assertEqual(node["status"],"OPEN")
            self.assertFalse(node["past_original_due"])

    def test_author_abandon_is_not_false_payoff_and_review_cannot_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            graph=self.candidate_graph(folder)
            rejected=self.apply(graph,self.review("ABANDON_BY_AUTHOR"))
            node=next(n["props"] for n in rejected["nodes"].values()
                      if n["kind"]=="THREAD")
            self.assertEqual(node["status"],"ABANDONED_AUTHOR_REVIEW_ONLY")
            self.assertTrue(node["not_a_payoff"])
            with self.assertRaisesRegex(
                    NarrativeCoreError,"ALREADY_CLOSED_REPLAY"):
                self.apply(rejected,self.review())


    def test_real_two_chapter_carry_then_source_anchored_settlement(self):
        from writerforge.narrative_core import (
            advance_graph,record_chapter_memory,
            propose_scene_delivery_debt,schedule,
        )
        with tempfile.TemporaryDirectory() as folder:
            first=self.apply(
                self.candidate_graph(folder),self.review("CARRY_FORWARD"))
            second_prose=(
                "沈砚把未寄出的信收起，决定当面告知唐蜃这笔旧债。"
                "唐蜃听罢没有原谅他，却答应同去矿井查证。")
            second=advance_graph(
                first,project_id=self.PROJECT,scene_id=self.STREAM,
                chapter_index=2,prose=second_prose,events=())
            file=Path(folder)/"chapter-2.md"
            file.write_text(second_prose,encoding="utf8")
            second=record_chapter_memory(
                second,project_id=self.PROJECT,scene_id=self.STREAM,
                chapter_index=2,source_path=str(file),prose=second_prose)
            report=self.receipt(prose=second_prose)
            preview=propose_scene_delivery_debt(
                first,project_id=self.PROJECT,scene_id=self.STREAM,
                chapter_index=2,prose=second_prose,
                scene_goal=self.GOAL,scene_kind="chapter",
                author_delivery_contract=self.CONTRACT,
                delivery_receipt=report)
            self.assertEqual(preview["status"],"OPEN_UNPAID")
            self.assertEqual(next(n for n in second["nodes"].values()
                                  if n["kind"]=="THREAD")["props"]["status"],
                             "OPEN")
            closed=self.apply(
                second,self.review(
                    "SETTLE_WITH_SOURCE",
                    action_quote="沈砚把未寄出的信收起，决定当面告知唐蜃这笔旧债。",
                    outcome_quote="唐蜃听罢没有原谅他，却答应同去矿井查证。"),
                prose=second_prose,receipt=report)
            thread=next(n["props"] for n in closed["nodes"].values()
                        if n["kind"]=="THREAD")
            self.assertEqual(thread["last_reviewed_chapter"],2)
            self.assertEqual(thread["opened_chapter"],1)
            self.assertEqual(thread["status"],"SETTLED_AUTHOR_REVIEW_ONLY")
            self.assertEqual(len(closed["nodes"]),len(first["nodes"]))
            self.assertEqual(closed["parent_sha256"],second["receipt_sha256"])
            self.assertEqual(closed["memory"]["last_recorded_chapter"],2)
            self.assertEqual(schedule(
                closed,project_id=self.PROJECT,scene_id=self.STREAM,
                chapter_index=3,
                beat={"kind":"decision","actor":"沈砚",
                      "goal":"沈砚准备和唐蜃继续调查"})["required_context"],"")
            self.assertEqual(closed["canon_writes"],0)

    def test_changed_contract_identity_fails_no_second_owner(self):
        from writerforge.narrative_core import propose_scene_delivery_debt
        with tempfile.TemporaryDirectory() as folder:
            opened=self.apply(self.candidate_graph(folder),self.review())
            changed=dict(self.CONTRACT,story_question="作者改写了问题但沿用同一ID")
            with self.assertRaisesRegex(
                    NarrativeCoreError,"CHANGED_CONTRACT"):
                propose_scene_delivery_debt(
                    opened,project_id=self.PROJECT,scene_id=self.STREAM,
                    chapter_index=2,
                    prose=self.PROSE,scene_goal=self.GOAL,
                    scene_kind="chapter",
                    author_delivery_contract=changed,
                    delivery_receipt=self.receipt(contract=changed))


    def test_replayed_source_cannot_be_laundered_by_resigned_receipt(self):
        source=long_original()+"\n\n"+long_original()
        audit=self.receipt(prose=source)
        self.assertTrue(audit["blocked"])
        forged=dict(audit,blocked=False)
        forged.pop("receipt_sha256")
        forged["receipt_sha256"]=hashlib.sha256(json.dumps(
            forged,sort_keys=True,ensure_ascii=False,
            separators=(",",":")).encode()).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            graph=self.candidate_graph(folder,prose=source)
            with self.assertRaisesRegex(
                    NarrativeCoreError,"PROSE_REPLAY_BLOCKED"):
                self.apply(graph,self.review(),prose=source,receipt=forged)

    def test_resigned_invalid_delivery_node_is_still_rejected(self):
        import copy
        from writerforge.narrative_core import validate
        with tempfile.TemporaryDirectory() as folder:
            carried=self.apply(self.candidate_graph(folder),self.review())
            forged=copy.deepcopy(carried)
            thread=next(x for x in forged["nodes"].values()
                        if x["kind"]=="THREAD")
            thread["props"]["status"]="SETTLED_AUTHOR_REVIEW_ONLY"
            forged.pop("receipt_sha256")
            forged["receipt_sha256"]=hashlib.sha256(json.dumps(
                forged,sort_keys=True,ensure_ascii=False,
                separators=(",",":")).encode()).hexdigest()
            with self.assertRaisesRegex(
                    NarrativeCoreError,"DELIVERY_SETTLED_ONLY_BY_AUTHOR"):
                validate(forged,project_id=self.PROJECT,scene_id=self.STREAM)


    def test_review_reloads_real_source_not_just_snapshot_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            graph=self.candidate_graph(folder)
            pointer=Path(graph["memory"]["hot"][-1]["source_path"])
            pointer.write_text(self.PROSE+"未受批准的新一句。",encoding="utf8")
            with self.assertRaisesRegex(
                    NarrativeCoreError,"ORIGINAL_MANUSCRIPT_HASH_CHANGED"):
                self.apply(graph,self.review())
            self.assertEqual(len(graph["nodes"]),0)

    def test_remote_review_requires_actual_private_reader(self):
        from writerforge.narrative_core import _signed
        with tempfile.TemporaryDirectory() as folder:
            graph=self.candidate_graph(folder)
            raw={k:v for k,v in graph.items() if k!="receipt_sha256"}
            raw["memory"]["hot"][-1]["source_path"]=(
                "r2://writerforge-private-library/verified-source")
            graph=_signed(raw)
            with self.assertRaisesRegex(
                    NarrativeCoreError,"R2_SOURCE_READER_REQUIRED"):
                self.apply(graph,self.review())
            from writerforge.narrative_core import review_scene_delivery_on_graph
            resolved=review_scene_delivery_on_graph(
                graph,project_id=self.PROJECT,scene_id=self.STREAM,
                prose=self.PROSE,scene_goal=self.GOAL,scene_kind="chapter",
                author_delivery_contract=self.CONTRACT,
                author_review=self.review(),
                source_reader=lambda path,expected:self.PROSE)
            self.assertEqual(next(v for v in resolved["nodes"].values()
                                  if v["kind"]=="THREAD")["props"]["status"],
                             "OPEN")

    def test_writing_host_surfaces_debt_but_never_commits_it(self):
        source=inspect.getsource(AutonomousWriting.run)
        self.assertIn("whole_debt_proposal=(",source)
        self.assertIn("propose_scene_delivery_debt(",source)
        self.assertIn('"unified_scene_debt_review_proposal"',source)
        self.assertIn('"unified_scene_cross_chapter_debt_status"',source)
        self.assertIn('"unified_scene_debt_auto_commits":0',source)
        self.assertNotIn("review_scene_delivery_on_graph(",source)



if __name__=="__main__":
    unittest.main()
