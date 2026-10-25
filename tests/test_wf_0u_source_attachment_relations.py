"""0.U physical attachment review uses existing V122/V114/V117/V119 source only.

The first sample is a verbatim sentence from the sealed REAL 0.T B-stage
DeepSeek author response #40163959949, not a fabricated model result. All
other strings are deliberately synthetic adversarial software tests.
No LLM, R2, Canon, extra memory, or subjective literary judge is involved.
"""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import json

from writerforge.v122_item_provenance import audit_physical_relation_sources
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import preflight_continuation, make_resume, read_resume
from writerforge.v119_revision_transaction import (
    preview_revision, prepare_source_repair_contract,compare_source_repair_impact)
from writerforge.writing_assist import _self_edit_one_turn
from writerforge.verified_flow import GroundedDraftPacket
from writerforge.v96_causal_turns import check_turn

# Only original model-authored source. The original full B T2 is still saved
# under Actions; this substring is uniquely source-located in that document.
REAL_B_SENTENCE=(
    "天亮前林栖已经到了堤上，手里攥着那截麻绳，绳结还系在木桩上，"
    "只是绳子被人从桩头解下来，绕在旁边一块石头上，石头下面压着片碎瓦。"
    "他蹲着看了很久，把瓦片翻过来，底面用炭画了个歪斜的叉。"
)
CAST=("林栖","程满")
BEAT={"id":"t01","kind":"action","actor":"林栖",
      "goal":"观察堤坝出现的痕迹并作出有后果的选择",
      "causal_parent":None,"craft_focus":[]}


def h(value):
    return sha256(value.encode("utf8")).hexdigest()


class PhysicalRelationshipSourceAudit(TestCase):
    def test_real_B_detected_as_source_question_not_proven_plot_error(self):
        report=audit_physical_relation_sources(prose=REAL_B_SENTENCE)
        self.assertEqual(report["review_status"],"NEEDS_SOURCE_RELATION_REVIEW")
        self.assertEqual(report["source_sha256"],h(REAL_B_SENTENCE))
        self.assertEqual(len(report["review_pairs"]),1)
        pair=report["review_pairs"][0]
        self.assertEqual(pair["first_source_quote"],"绳结还系在木桩上")
        self.assertEqual(pair["second_source_quote"],
                         "只是绳子被人从桩头解下来")
        self.assertEqual(pair["item_identity_evidence"],
                         "POSSIBLE_PART_OR_REFERENT_ALIAS")
        self.assertEqual(pair["contact_identity_evidence"],
                         "POSSIBLE_CONTACT_AREA_ALIAS")
        for suffix in ("first","second"):
            quote=pair[suffix+"_source_quote"]
            start=pair[suffix+"_source_start"]
            self.assertEqual(REAL_B_SENTENCE[start:start+len(quote)],quote)
            self.assertEqual(pair[suffix+"_source_quote_sha256"],h(quote))
        self.assertFalse(report["claims"][0]["candidate_not_item_holder_or_canon"] is False)
        self.assertTrue(report["source_coverage_is_partial_not_universal"])
        self.assertEqual(report["canon_writes"],0)
        self.assertEqual(report["model_calls"],0)

    def test_exact_same_item_same_post_is_review_not_literary_verdict(self):
        p="红绳还系在铁钩上，只是红绳已经被人从铁钩上解下来。"
        report=audit_physical_relation_sources(prose=p)
        self.assertEqual(report["review_pairs"][0]["item_identity_evidence"],
                         "EXACT_LITERAL")
        self.assertEqual(report["review_pairs"][0]["contact_identity_evidence"],
                         "EXACT_LITERAL")
        self.assertTrue(report["actor_unknown_is_not_literary_error"])

    def test_sequential_attach_then_detach_is_allowed(self):
        p="林栖先把麻绳系在木桩上，然后将麻绳从木桩上解下。"
        r=audit_physical_relation_sources(prose=p)
        self.assertFalse(r["current_source_needs_review"],r)

    def test_delayed_unbinding_after_still_bound_is_allowed(self):
        p="麻绳仍系在木桩上，后来麻绳被人从木桩上解下来。"
        r=audit_physical_relation_sources(prose=p)
        self.assertFalse(r["current_source_needs_review"],r)

    def test_two_differently_identified_objects_are_not_merged(self):
        p="红绳还系在木桩上，只是蓝绳被人从木桩上解下来。"
        r=audit_physical_relation_sources(prose=p)
        self.assertFalse(r["current_source_needs_review"],r)

    def test_tether_free_end_is_not_the_whole_rope(self):
        p="绳结还系在木桩上，只是绳子的自由端被人从桩头解下来。"
        r=audit_physical_relation_sources(prose=p)
        self.assertFalse(r["current_source_needs_review"],r)

    def test_unknown_actor_or_reader_guess_not_world_state(self):
        for prose in (
            "林栖猜绳结还系在木桩上，只是绳子被人从桩头解下来。",
            "不知道谁动了绳子，堤坝上没有任何明显痕迹。",
            "“绳结还系在木桩上，只是绳子被人从桩头解下来。”他说。",
            "绳子可能还系在木桩上，只是有人想象它被解开了。",
        ):
            with self.subTest(prose=prose):
                self.assertFalse(
                    audit_physical_relation_sources(
                        prose=prose)["current_source_needs_review"])

    def test_relation_parser_not_hardcoded_to_rope_nouns(self):
        text="铜牌还挂在门钩上，只是铜牌被人从门钩上摘下来。"
        receipt=audit_physical_relation_sources(prose=text)
        self.assertEqual(receipt["review_status"],"NEEDS_SOURCE_RELATION_REVIEW")
        self.assertEqual(receipt["review_pairs"][0]["first_item_literal"],"铜牌")
        self.assertEqual(receipt["review_pairs"][0]["second_item_literal"],"铜牌")

    def test_forged_previous_review_receipt_rejected(self):
        earlier=audit_physical_relation_sources(prose=REAL_B_SENTENCE)
        fake={**earlier,"source_sha256":"f"*64}
        with self.assertRaisesRegex(
                ValueError,"WF122_PREVIOUS_RELATION_RECEIPT_UNTRUSTED"):
            audit_physical_relation_sources(
                prose="他站在堤坝上。",previous_relation_receipt=fake)


class RelationExistingTransactionalPath(TestCase):
    def test_v116_reveals_actual_source_quotes_no_automatic_state(self):
        report=preflight_next_prose(
            REAL_B_SENTENCE,previous_candidate_state={},cast=CAST)
        self.assertFalse(report["blocked"])
        self.assertTrue(report["needs_review"])
        self.assertIn("NEEDS_SOURCE_RELATION_REVIEW",report["review_findings"])
        self.assertTrue(report["physical_relation_current_review_needed"])
        self.assertEqual(len(report["physical_relation_review_pairs"]),1)
        self.assertTrue(report["physical_relation_cannot_promote_to_holder_or_canon"])
        self.assertEqual(report["new_model_retries"],0)

    def test_v114_signed_checkpoint_and_v117_cannot_promote_relation(self):
        cp=external_temporal_step(REAL_B_SENTENCE,cast=CAST)
        self.assertEqual(cp["v122_physical_relation_source_receipt"]
                             ["source_sha256"],h(REAL_B_SENTENCE))
        self.assertEqual(cp["source_sha256"],h(REAL_B_SENTENCE))
        self.assertTrue(cp["v122_relation_review_not_a_reducer_cell"])
        self.assertFalse(any("attached_to" in key or "bound_to" in key
                             for key in cp["reducer_result"]["candidate_state"]))
        next_prose=("林栖仍觉得线索不足。他把所有痕迹誊在潮簿上，"
                    "没有声称绳子是谁解下的，也没有凭空宣布物件在别处。")
        second=preflight_continuation(
            next_prose,cp,project_id="wf-0u-source",
            chapter_index=2,cast=CAST)
        self.assertFalse(second["blocked"])
        self.assertGreater(second["physical_relation_previous_unresolved"],0)
        # Purely unrelated continuation may proceed without assigning a
        # fictional rope location; old uncertainty stays in signed source.
        self.assertFalse(second["physical_relation_must_not_be_fact_or_downstream_parent"])
        self.assertEqual(second["physical_relation_dependent_on_unresolved_source"],[])
        dependent=preflight_continuation(
            "绳结还系在木桩上。林栖继续观察堤坝，不肯把昨日没有写明的动作当作眼前已证的事实。",
            cp,project_id="wf-0u-source",chapter_index=2,cast=CAST)
        self.assertTrue(dependent["needs_review"])
        self.assertTrue(dependent[
            "physical_relation_must_not_be_fact_or_downstream_parent"])
        self.assertEqual(len(dependent[
            "physical_relation_dependent_on_unresolved_source"]),1)
        signed=make_resume(project_id="wf-0u-source",scene_id="river",
                           chapter_index=1,checkpoint=cp)
        reread=read_resume(signed,project_id="wf-0u-source",scene_id="river")
        self.assertEqual(reread["receipt_sha256"],cp["receipt_sha256"])

    def test_source_relation_hold_is_not_a_model_literary_rewrite(self):
        from writerforge.writing_assist import _physical_relation_source_hold
        preflight=preflight_next_prose(
            REAL_B_SENTENCE,previous_candidate_state={},cast=CAST)
        hold=_physical_relation_source_hold(
            prose=REAL_B_SENTENCE,preflight=preflight)
        self.assertEqual(hold["status"],"HELD_NEEDS_SOURCE_RELATION_REVIEW")
        self.assertEqual(hold["prose_sha256"],h(REAL_B_SENTENCE))
        self.assertEqual(len(hold["current_conflicting_source_quote_pairs"]),1)
        self.assertTrue(hold["actor_unknown_may_remain_literary_mystery"])
        self.assertTrue(hold["writer_owns_edit_and_literary_choice"])
        self.assertEqual(hold["new_model_calls"],0)
        self.assertEqual(hold["canon_writes"],0)
        self.assertFalse(hold["automatic_author_decision_or_fiction_generation"])
        self.assertTrue(hold["downstream_relation_dependent_scene_must_not_reuse_old_state"])
        self.assertIsNone(_physical_relation_source_hold(
            prose="林栖走到桥上，仍谨慎记下每个潮位标记。",
            preflight=preflight_next_prose(
                "林栖走到桥上，仍谨慎记下每个潮位标记。",
                previous_candidate_state={},cast=CAST)))
        with self.assertRaisesRegex(
                Exception,"WF122_RELATION_HOLD_WRONG_SOURCE_SHA"):
            _physical_relation_source_hold(
                prose=REAL_B_SENTENCE+"伪",preflight=preflight)

    def test_v119_contract_contains_actual_two_source_quotes(self):
        guide=prepare_source_repair_contract(
            source=REAL_B_SENTENCE,source_sha256=h(REAL_B_SENTENCE),
            beat=BEAT,accepted=(),
            writer_attention={"source_quote":"绳结还系在木桩上",
                               "reason":"这一处绳索状态衔接似乎需要仔细阅读"},
            original_trace={"action_quote":None,"effect_quote":None,
                            "parent_effect_quote":None},
            previous_candidate_state={},cast=CAST)
        detail=guide["physical_relation_source_evidence"]
        self.assertEqual(detail["source_sha256"],h(REAL_B_SENTENCE))
        self.assertEqual(len(detail["source_quote_pairs"]),1)
        self.assertTrue(detail["writer_chooses_keep_delete_local_edit_or_scene_rewrite"])
        self.assertTrue(detail["writer_may_keep_unrevealed_actor_and_meaning"])
        self.assertEqual(detail["source_quote_pairs"][0]["first_source_quote"],
                         "绳结还系在木桩上")

    def test_unrelated_edit_cannot_clear_existing_relation_review(self):
        first="天亮前林栖已经到了堤上"
        replacement="天色刚亮，林栖到了堤上"
        preview=preview_revision(
            source=REAL_B_SENTENCE,source_sha256=h(REAL_B_SENTENCE),
            project_id="wf0u",scene_id="river",start=0,end=len(first),
            expected_original=first,replacement=replacement,
            previous_candidate_state={},cast=CAST)
        self.assertEqual(preview["status"],"PROVISIONAL_REVIEW")
        report=compare_source_repair_impact(preview_receipt=preview["receipt"])
        self.assertEqual(report["status"],"HELD_EXISTING_SOURCE_RELATION_RISK")
        self.assertTrue(report["existing_physical_relation_review_remaining"])
        self.assertTrue(report["source_relation_risk_cannot_be_cleared_by_prose_without_evidence"])

    def test_only_author_generated_mock_revision_can_remove_dilemma(self):
        # Synthetic test patch: NEVER an actual model literary result.
        old="只是绳子被人从桩头解下来"
        revised="只是木桩旁多了几道新鲜泥痕"
        start=REAL_B_SENTENCE.index(old)
        preview=preview_revision(
            source=REAL_B_SENTENCE,source_sha256=h(REAL_B_SENTENCE),
            project_id="wf0u",scene_id="river",
            start=start,end=start+len(old),
            expected_original=old,replacement=revised,
            previous_candidate_state={},cast=CAST)
        report=compare_source_repair_impact(preview_receipt=preview["receipt"])
        self.assertEqual(report["status"],"NO_NEW_DETECTED_STRUCTURAL_RISK_ONLY")
        self.assertFalse(report["existing_physical_relation_review_remaining"])
        self.assertEqual(report["author_literary_goal_satisfied"],"UNVERIFIED")

