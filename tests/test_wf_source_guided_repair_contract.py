"""WF must HELP repair; not just show an error, and not rewrite for the AI.

Deterministic structural tests on existing V119 source-only guardrails:
- before model, prepare source-proven repair objective, actual V96 parent,
  earlier risks and what any revision invalidates downstream;
- after model, distinguish resolved/old/new hard and unverified findings;
- HOLD new source uncertainty, do not assume it is confirmed fiction;
- reject revisiting the same manuscript bytes in one edit task;
- on a false action/effect trace, give source-specific next work without
  having software write any missing prose or stealth-edit the model trace.
All model decisions in this test are simulated, no real provider access.
"""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json

from writerforge.v119_revision_transaction import (
    prepare_source_repair_contract,compare_source_repair_impact,
    preview_revision,RevisionTransactionError,_digest_json,
)
from writerforge.writing_assist import _self_edit_one_turn
from writerforge.verified_flow import GroundedDraftPacket
from test_wf_writer_self_revision_loop import advice
from test_v96_causal_turns import ACTION1,EFFECT1,prose1,response,plan


def hashed(s):
    return sha256(s.encode("utf8")).hexdigest()


class GuardrailRequirements(TestCase):
    def setUp(self):
        self.source=prose1()
        self.beat=plan()[0]
        self.trace={"action_quote":ACTION1,"effect_quote":EFFECT1,
                    "parent_effect_quote":None}
        self.selected="黄昏最后一点天光落到桥头时，"
        self.attention={
            "reason":"人物明明怕桥断裂却突然莽撞上前，动作不符合刚才的谨慎。",
            "risk":"直接切入撞击让人物没有采取任何可见的保护动作。",
            "desired_effect":"读者应看到试探和受到阻力的真实连续后果。",
            "source_quote":self.selected,
            "focus":"sentence",
        }
        self.contract=lambda **kwargs:prepare_source_repair_contract(
            source=self.source,source_sha256=hashed(self.source),
            beat=self.beat,accepted=(),original_trace=self.trace,
            writer_attention=self.attention,**kwargs)

    def test_guide_is_source_frozen_and_prepares_options_not_new_fiction(self):
        doc=self.contract(previous_candidate_state={},cast=())
        self.assertEqual(doc["source_sha256"],hashed(self.source))
        self.assertEqual(doc["author_model_selected_focus_quote"],self.selected)
        self.assertEqual(doc["author_model_selected_focus_offset"],
                         self.source.index(self.selected))
        self.assertEqual(doc["author_intent_not_a_verified_fact"]["reason"],
                         self.attention["reason"])
        self.assertIsNone(doc["previous_causal_parent_id"])
        self.assertIsNone(doc["actual_previous_effect_quote"])
        self.assertTrue(doc["source_action_effect_required"])
        self.assertEqual(doc["baseline_state_coverage"],"V116_SOURCE_ONLY_NARROW")
        self.assertEqual(doc["downstream_after_change"],
                         "MUST_REGENERATE_FROM_REVISED_SOURCE")
        self.assertTrue(doc["no_literary_grade_or_host_authored_text"])
        self.assertTrue(doc["any_author_intent_fulfillment_still_unproven"])
        self.assertEqual(doc["new_model_calls"],0)
        self.assertEqual(doc["canon_writes"],0)
        self.assertEqual(doc["receipt_sha256"],_digest_json({
            k:v for k,v in doc.items() if k!="receipt_sha256"}))

    def test_wrong_original_sha_or_missing_parent_is_rejected_before_llm(self):
        with self.assertRaisesRegex(
                RevisionTransactionError,"WF119_REPAIR_ORIGINAL_SOURCE_INVALID"):
            prepare_source_repair_contract(
                source=self.source,source_sha256="0"*64,
                beat=self.beat,accepted=(),original_trace=self.trace)
        parent={**self.beat,"causal_parent":"unwritten_t0"}
        with self.assertRaisesRegex(
                RevisionTransactionError,"WF119_REPAIR_PARENT_SOURCE_MISSING"):
            prepare_source_repair_contract(
                source=self.source,source_sha256=hashed(self.source),
                beat=parent,accepted=(),original_trace=self.trace)
        self.assertNotIn("同一模型自动按我的想法生成",repr(self.contract()))

    def test_before_after_risk_delta_is_structural_not_literary_grade(self):
        first=self.selected
        replacement="山间落起骤雨的时候，"
        preview=preview_revision(
            project_id="source-guided",scene_id="river",
            source=self.source,source_sha256=hashed(self.source),
            start=self.source.index(first),
            end=self.source.index(first)+len(first),
            expected_original=first,replacement=replacement,
            previous_candidate_state={},cast=())
        self.assertEqual(preview["status"],"PROVISIONAL_REVIEW")
        comparison=compare_source_repair_impact(
            preview_receipt=preview["receipt"])
        self.assertEqual(comparison["status"],
                         "NO_NEW_DETECTED_STRUCTURAL_RISK_ONLY")
        self.assertFalse(comparison["new_unverified_review_findings"])
        self.assertEqual(comparison["author_literary_goal_satisfied"],
                         "UNVERIFIED")
        self.assertTrue(comparison["subsequent_turns_require_new_source_prose"])
        self.assertTrue(comparison[
            "never_automatically_repair_or_promote_to_canon"])
        old=dict(preview["receipt"])
        old["source_sha256"]="f"*64
        with self.assertRaisesRegex(
                RevisionTransactionError,"WF119_REPAIR_IMPACT_RECEIPT_TAMPERED"):
            compare_source_repair_impact(preview_receipt=old)

    def test_new_uncertain_risk_must_be_held_even_when_no_new_hard_error(self):
        first=self.selected
        preview=preview_revision(
            project_id="source-guided",scene_id="river",
            source=self.source,source_sha256=hashed(self.source),
            start=self.source.index(first),
            end=self.source.index(first)+len(first),
            expected_original=first,
            replacement="黄昏下雨的时候，",previous_candidate_state={},cast=())
        hacked={**preview["receipt"]}
        hacked["new_preflight_review_flags"]=["SOURCE_SUBJECT_UNCONFIRMED"]
        hacked["revision_review_findings"]=["SOURCE_SUBJECT_UNCONFIRMED"]
        hacked["receipt_sha256"]=_digest_json({
            k:v for k,v in hacked.items() if k!="receipt_sha256"})
        delta=compare_source_repair_impact(preview_receipt=hacked)
        self.assertEqual(delta["status"],"HELD_NEW_UNVERIFIED_SOURCE_RISK")
        self.assertEqual(delta["new_unverified_review_findings"],
                         ["SOURCE_SUBJECT_UNCONFIRMED"])
        self.assertTrue(delta["one_fix_may_create_another_error"])


class SourceGuideIntegratedIntoOriginalWriter(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=prose1()
        self.raw=response(self.source,ACTION1,EFFECT1)
        self.beat=plan()[0]
        basic="【已经实际发生的源约束】旧桥有损伤，人物不能凭空脱困。"
        self.packet=GroundedDraftPacket(
            scene_id="test-repair-guidance-one-turn",
            project_id="test-repair-guidance-project",
            snapshot_id=0,evidence=(),craft_ids=(),
            prompt=basic,prompt_sha256=hashed(basic))
        self.focus="黄昏最后一点天光落到桥头时，"
        self.intention={
            "reason":"情节动作节奏太快，想让人物慎重选择下一步。",
            "source_quote":self.focus,
            "focus":"sentence",
        }

    def execute(self,replies,*,rounds=1,previous_candidate_state=None,
                patch_preview=None):
        replies=list(replies)
        observed=[]
        def same_writer(packet,*,model,api_base,max_tokens):
            self.assertIsNone(model)
            self.assertIsNone(api_base)
            self.assertIn('"wf_source_repair_contract"',packet.prompt)
            self.assertIn(self.intention["reason"],packet.prompt)
            self.assertIn("MUST_REGENERATE_FROM_REVISED_SOURCE",packet.prompt)
            self.assertEqual(max_tokens,1800)
            observed.append(packet.prompt)
            return replies[len(observed)-1]
        with patch("writerforge.writing_assist.preview_surgical_revision",
                   side_effect=patch_preview) if patch_preview else patch(
                       "writerforge.writing_assist.preview_surgical_revision",
                       wraps=preview_revision):
            final,receipt=_self_edit_one_turn(
                raw=self.raw,beat=self.beat,accepted=(),
                project_id=self.packet.project_id,scene_id=self.packet.scene_id,
                turn_packet=self.packet,ask_model=same_writer,
                round_limit=rounds,call_allowance=rounds,
                directory=self.root/"test-edit",
                previous_candidate_state=previous_candidate_state,
                writer_attention=self.intention)
        self.assertEqual(receipt["model_calls"],len(observed))
        return final,receipt,observed

    def test_original_ai_can_keep_and_receives_factual_guidance_without_autorewrite(self):
        final,receipt,calls=self.execute([advice(self.source)])
        self.assertEqual(final,self.raw)
        self.assertEqual(receipt["rounds"][0]["status"],"KEEP_BY_WRITER")
        guide=json.loads((self.root/"test-edit"/
                          "round-01-source-repair-guide.json").read_text("utf8"))
        self.assertEqual(guide["author_model_selected_focus_quote"],self.focus)
        self.assertEqual(receipt["rounds"][0][
            "source_repair_contract_sha256"],guide["receipt_sha256"])
        self.assertEqual(len(calls),1)
        self.assertFalse(list((self.root/"test-edit").glob("*selected-draft*")))

    def test_after_invalid_v96_trace_gives_actual_next_step_without_editing_for_ai(self):
        anchor=self.focus
        start=self.source.index(anchor)
        replacement="雨下到桥头，少年调整步伐，准备谨慎渡桥时，"
        proposal=advice(
            self.source,decision="REVISE",scope="sentence",
            start=start,end=start+len(anchor),
            replacement=replacement,
            trace={
                "action_quote":ACTION1,
                "effect_quote":ACTION1,
                "parent_effect_quote":None})
        final,receipt,_=self.execute([proposal],previous_candidate_state={})
        self.assertEqual(final,self.raw)
        row=receipt["rounds"][0]
        self.assertEqual(row["status"],"REJECTED_AND_ROLLED_BACK")
        self.assertEqual(row["reason_code"],
                         "WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED")
        self.assertEqual(row["writer_next_safe_action"],
                         "ORIGINAL_WRITER_MUST_QUOTE_TWO_DISTINCT_ORDERED_SOURCE_SPANS")
        action=json.loads((self.root/"test-edit"/
                           "round-01-actionable-failure.json").read_text("utf8"))
        self.assertTrue(action["no_unbounded_repair_retries"])
        self.assertEqual(action["exact_validation_failure"],
                         "WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED")
        self.assertTrue((self.root/"test-edit"/
                         "round-01-before-after-impact.json").is_file())
        self.assertFalse((self.root/"test-edit"/
                          "round-01-selected-draft.md").exists())

    def test_two_model_revisions_cannot_oscillate_back_to_old_source(self):
        original=self.focus
        interim="黄昏先落起了急雨，"
        first_start=self.source.index(original)
        first=advice(
            self.source,decision="REVISE",scope="sentence",
            start=first_start,end=first_start+len(original),
            replacement=interim,
            trace={"action_quote":ACTION1,"effect_quote":EFFECT1,
                   "parent_effect_quote":None})
        next_prose=self.source.replace(original,interim,1)
        second=advice(
            next_prose,decision="REVISE",scope="sentence",
            start=first_start,end=first_start+len(interim),
            replacement=original,
            trace={"action_quote":ACTION1,"effect_quote":EFFECT1,
                   "parent_effect_quote":None})
        final,receipt,calls=self.execute([first,second],rounds=2)
        self.assertEqual(json.loads(final)["prose"],next_prose)
        self.assertEqual(receipt["model_calls"],2)
        self.assertEqual([x["status"] for x in receipt["rounds"]],
                         ["PROVISIONALLY_REVISED",
                          "REJECTED_REVISION_OSCILLATION"])
        self.assertEqual(receipt["rounds"][1][
            "previously_seen_source_sha256"],hashed(self.source))
        self.assertTrue(receipt["rounds"][1][
            "author_cannot_loop_back_to_same_draft_automatically"])
        self.assertTrue((self.root/"test-edit"/
                         "round-01-selected-draft.md").is_file())
        self.assertFalse((self.root/"test-edit"/
                          "round-02-selected-draft.md").exists())

    def test_source_locked_new_prose_gets_one_same_writer_trace_only_rescue(self):
        selected=self.focus
        replacement="山风先吹到桥头，少年收住脚步试探石阶时，"
        start=self.source.index(selected)
        first=advice(
            self.source,decision="REVISE",scope="sentence",
            start=start,end=start+len(selected),
            replacement=replacement,
            trace={"action_quote":ACTION1,"effect_quote":ACTION1,
                   "parent_effect_quote":None})
        # Model's SECOND allowed call only supplies exact references in
        # the frozen first model-authored candidate. No prose at all.
        meta=json.dumps({
            "trace":{"action_quote":ACTION1,"effect_quote":EFFECT1,
                     "parent_effect_quote":None},
        },ensure_ascii=False)
        seen=[]
        def same_original_writer(packet,*,model,api_base,max_tokens):
            self.assertIsNone(model)
            self.assertIsNone(api_base)
            self.assertEqual(max_tokens,1800)
            seen.append(packet.prompt)
            if len(seen)==1:
                self.assertIn('"wf_source_repair_contract"',packet.prompt)
                return first
            if len(seen)==2:
                self.assertIn("本次只允许更正引用元数据",packet.prompt)
                self.assertIn("原作者已经写出的冻结候选",packet.prompt)
                self.assertIn(replacement,packet.prompt)
                self.assertIn("WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED",
                              packet.prompt)
                return meta
            self.fail("Never allow a third automatic literary retry")
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            result,receipt=_self_edit_one_turn(
                raw=self.raw,beat=self.beat,accepted=(),
                project_id=self.packet.project_id,scene_id=self.packet.scene_id,
                turn_packet=self.packet,ask_model=same_original_writer,
                round_limit=2,call_allowance=2,
                directory=root/"author-help",
                writer_attention=self.intention)
            self.assertEqual(receipt["model_calls"],2)
            self.assertEqual(len(seen),2)
            self.assertEqual(receipt["rounds"][0]["status"],
                             "PROVISIONALLY_REVISED")
            round=receipt["rounds"][0]
            self.assertTrue(round["source_trace_reattributed_by_same_author_model"])
            self.assertEqual(round["initial_model_V96_trace_failure"],
                             "WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED")
            self.assertEqual(round["additional_trace_only_model_call"],1)
            self.assertTrue(round["novelist_prose_never_changed_by_trace_repair"])
            fiction=json.loads(result)
            self.assertEqual(fiction["prose"],
                             self.source.replace(selected,replacement,1))
            self.assertEqual(fiction["trace"],json.loads(meta)["trace"])
            self.assertTrue((root/"author-help"/
                             "round-01-invalid-model-trace.json").is_file())
            self.assertEqual((root/"author-help"/
                "same-writer-source-trace-only-original.json").read_text("utf8"),
                meta)
            self.assertFalse((root/"author-help"/
                              "round-02-model-proposal.json").exists())

    def test_second_trace_attempt_that_still_fails_never_changes_original(self):
        anchor=self.focus
        start=self.source.index(anchor)
        first=advice(
            self.source,decision="REVISE",scope="sentence",
            start=start,end=start+len(anchor),
            replacement="黄昏时桥边又起风了，",
            trace={"action_quote":ACTION1,"effect_quote":ACTION1,
                   "parent_effect_quote":None})
        broken=json.dumps({
            "trace":{"action_quote":ACTION1,"effect_quote":ACTION1,
                     "parent_effect_quote":None}},ensure_ascii=False)
        outputs=[first,broken]
        with TemporaryDirectory() as temp:
            path=Path(temp)/"failed-repair"
            def fake_model(packet,*,model,api_base,max_tokens):
                self.assertEqual(max_tokens,1800)
                return outputs.pop(0)
            actual,r=_self_edit_one_turn(
                raw=self.raw,beat=self.beat,accepted=(),
                project_id=self.packet.project_id,scene_id=self.packet.scene_id,
                turn_packet=self.packet,ask_model=fake_model,
                round_limit=2,call_allowance=2,directory=path)
            self.assertEqual(actual,self.raw)
            self.assertEqual(r["model_calls"],2)
            self.assertEqual(outputs,[])
            self.assertEqual(r["rounds"][0]["status"],
                             "REJECTED_AND_ROLLED_BACK")
            self.assertEqual(r["rounds"][0]["reason_code"],
                             "WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED")
            self.assertTrue(r["rounds"][0]["metadata_only_trace_attempted"])
            self.assertTrue((path/
                             "same-writer-source-trace-only-original.json").exists())
            self.assertFalse((path/"round-01-selected-draft.md").exists())

    def test_malformed_trace_only_model_response_consumes_second_budget_and_rolls_back(self):
        anchor=self.focus
        start=self.source.index(anchor)
        first=advice(
            self.source,decision="REVISE",scope="sentence",
            start=start,end=start+len(anchor),
            replacement="夜色下桥头的风更紧了，",
            trace={"action_quote":ACTION1,"effect_quote":ACTION1,
                   "parent_effect_quote":None})
        responses=[first,'{"prose":"偷偷代写整个新故事"}']
        with TemporaryDirectory() as temp:
            path=Path(temp)/"malformed"
            final,receipt=_self_edit_one_turn(
                raw=self.raw,beat=self.beat,accepted=(),
                project_id=self.packet.project_id,scene_id=self.packet.scene_id,
                turn_packet=self.packet,
                ask_model=lambda *a,**kw:responses.pop(0),
                round_limit=2,call_allowance=2,directory=path)
            self.assertEqual(final,self.raw)
            self.assertEqual(receipt["model_calls"],2)
            self.assertEqual(receipt["rounds"][0]["reason_code"],
                             "WF_TRACE_ONLY_REPLY_SCHEMA_INVALID")
            self.assertTrue(receipt["rounds"][0]["metadata_only_trace_attempted"])
            self.assertFalse(responses)
            self.assertTrue((path/"same-writer-source-trace-only-original.json"
                             ).is_file())

    def test_user_cancel_is_not_swallowed_by_reattribution_recovery(self):
        from writerforge.writing_assist import WriterDraftCancelled
        anchor=self.focus
        start=self.source.index(anchor)
        first=advice(
            self.source,decision="REVISE",scope="sentence",
            start=start,end=start+len(anchor),
            replacement="山雨落在桥头时，",
            trace={"action_quote":ACTION1,"effect_quote":ACTION1,
                   "parent_effect_quote":None})
        count=0
        def same_writer(packet,*,model,api_base,max_tokens):
            nonlocal count
            count+=1
            return first
        def cancel_check():
            if count==1:
                raise WriterDraftCancelled("WF_STUDIO_DRAFT_CANCELLED")
        with TemporaryDirectory() as temp:
            with self.assertRaises(WriterDraftCancelled):
                _self_edit_one_turn(
                    raw=self.raw,beat=self.beat,accepted=(),
                    project_id=self.packet.project_id,
                    scene_id=self.packet.scene_id,
                    turn_packet=self.packet,ask_model=same_writer,
                    round_limit=2,call_allowance=2,
                    directory=Path(temp)/"canceled",
                    cancel_check=cancel_check)
            self.assertEqual(count,1)
            self.assertFalse((Path(temp)/"canceled"/
                              "same-writer-source-trace-only-original.json").exists())

    def test_new_unproven_state_flag_stays_private_and_does_not_cause_new_turn(self):
        anchor=self.focus
        start=self.source.index(anchor)
        reply=advice(
            self.source,decision="REVISE",scope="sentence",
            start=start,end=start+len(anchor),
            replacement="风吹桥头，行人试探前行时，",
            trace={"action_quote":ACTION1,"effect_quote":EFFECT1,
                   "parent_effect_quote":None})
        def emulated_source_warning(**kw):
            valid=preview_revision(**kw)
            receipt={**valid["receipt"],
                     "new_preflight_review_flags":[
                         "UNPROVEN_NEW_PROP_LOCATION"],
                     "revision_review_findings":[
                         "UNPROVEN_NEW_PROP_LOCATION"]}
            receipt["receipt_sha256"]=_digest_json({
                k:v for k,v in receipt.items()
                if k!="receipt_sha256"})
            return {**valid,"receipt":receipt}
        final,receipt,calls=self.execute(
            [reply],previous_candidate_state={},
            patch_preview=emulated_source_warning)
        self.assertEqual(final,self.raw)
        self.assertEqual(receipt["rounds"][0]["status"],
                         "HELD_NEW_UNVERIFIED_SOURCE_RISK")
        self.assertTrue((self.root/"test-edit"/
                         "round-01-held-unverified-draft.md").is_file())
        self.assertFalse((self.root/"test-edit"/
                          "round-01-selected-draft.md").exists())
        self.assertEqual(len(calls),1)

if __name__=="__main__":
    import unittest
    unittest.main()
