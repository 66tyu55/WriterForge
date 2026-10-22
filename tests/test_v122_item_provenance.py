"""V122 multi-actor and multi-resource physical state and source-only tests.

No model calls, no R2, no DB, no canon promotion; preserve uncertain pronouns.
"""
from __future__ import annotations

import hashlib
import json
import unittest

from writerforge.v122_item_provenance import (
    audit_item_provenance, ItemProvenanceError, FORMAT,
)
from writerforge.v116_state_delta import preflight_next_prose

CAST=("沈砚","唐蜃","叶青梧")


def old_item(item,holder):
    return {json.dumps(["item",item,"holder","author_plan",None],
                       ensure_ascii=False,separators=(",",":")):holder}


def audit(text,state=None,cast=CAST):
    return audit_item_provenance(
        prose=text,
        previous_candidate_state=state or old_item("火髓果","沈砚左手心"),
        cast=cast)


def before(text,state=None,cast=CAST):
    return preflight_next_prose(
        text,previous_candidate_state=state or old_item("火髓果","沈砚左手心"),
        cast=cast)


class MultiActorItemSourceAudit(unittest.TestCase):
    def test_generic_not_one_special_enemy_name(self):
        prev=old_item("青木令","叶青梧手中")
        report=audit("沈砚握着青木令，慢慢朝门口退去。",prev)
        self.assertIn("WF122_ITEM_OWNER_CHANGE_WITHOUT_TRANSFER",
                      report["hard_findings"])
        self.assertEqual(report["candidate_source_events"],[])
        self.assertEqual(report["remaining_holders_candidate_only"]["青木令"],
                         "叶青梧手中")

    def test_named_antagonist_already_holder_not_false_teleport(self):
        prev=old_item("火髓果","唐蜃左手心")
        result=before("唐蜃握着火髓果，沿石壁小心后退。",prev)
        self.assertFalse(result["blocked"],result)
        self.assertEqual(result["findings"],[])

    def test_other_character_claims_protagonist_fruit_without_action(self):
        report=before("唐蜃握着火髓果，冷笑不语。")
        self.assertTrue(report["blocked"])
        self.assertIn("WF116_FRUIT_TELEPORT_TO_OTHER_ACTOR",report["findings"])
        self.assertEqual(report["v122_source_events_count"],0)

    def test_explicit_handoff_updates_candidate_with_source_and_no_teleport(self):
        prose="沈砚把火髓果从左手心递给唐蜃。唐蜃握着火髓果。"
        report=audit(prose)
        self.assertEqual(report["hard_findings"],[])
        self.assertEqual(report["review_findings"],[])
        self.assertEqual(report["remaining_holders_candidate_only"]["火髓果"],
                         "唐蜃手中")
        self.assertEqual(len(report["candidate_source_events"]),1)
        event=report["candidate_source_events"][0]
        self.assertEqual(event["kind"],"HANDOFF")
        self.assertEqual(event["before_holder"],"沈砚左手心")
        self.assertEqual(event["after_holder"],"唐蜃手中")
        self.assertEqual(event["source_quote_sha256"],
                         hashlib.sha256((prose.split("。")[0]+"。").encode()).hexdigest())
        self.assertFalse(before(prose)["blocked"])
        self.assertTrue(report["candidate_state_not_promoted_to_reducer"])

    def test_three_people_two_handoffs_temporally_ordered(self):
        prose=("沈砚把火髓果从左手心递给唐蜃。"
               "唐蜃把火髓果从手中递给叶青梧。"
               "叶青梧握着火髓果，没有再争辩。")
        report=audit(prose)
        self.assertEqual(report["hard_findings"],[])
        self.assertEqual(report["remaining_holders_candidate_only"]["火髓果"],
                         "叶青梧手中")
        self.assertEqual(len(report["candidate_source_events"]),2,report)
        self.assertEqual([x["after_holder"] for x in
                          report["candidate_source_events"]],
                         ["唐蜃手中","叶青梧手中"])
        self.assertFalse(before(prose)["blocked"])

    def test_bad_source_palm_rejects_claimed_handoff(self):
        text="沈砚把火髓果从右手心递给唐蜃。"
        result=before(text)
        self.assertTrue(result["blocked"])
        self.assertIn("WF122_HANDOFF_SOURCE_PRECONDITION_FAILED",
                      result["findings"])
        self.assertEqual(audit(text)["candidate_source_events"],[])

    def test_handoff_cannot_resurrect_consumed_item(self):
        prev=old_item("火髓果","已消耗（沈砚吞服）")
        text="沈砚把火髓果从左手心递给唐蜃。"
        r=before(text,prev)
        self.assertTrue(r["blocked"])
        self.assertIn("WF122_HANDOFF_SOURCE_PRECONDITION_FAILED",r["findings"])

    def test_two_named_fruits_never_collapse_into_first(self):
        prev={**old_item("火髓果","沈砚左手心"),
              **old_item("风髓果","唐蜃左手心")}
        prose="唐蜃握着风髓果，沈砚守着山门。"
        result=before(prose,prev)
        self.assertFalse(result["blocked"],result)
        self.assertEqual(audit(prose,prev)["checked_item_count"],2)
        self.assertEqual(audit(prose,prev)["remaining_holders_candidate_only"],
                         {"火髓果":"沈砚左手心","风髓果":"唐蜃左手心"})

    def test_multi_fruit_unqualified_fruit_alias_never_guessed(self):
        prev={**old_item("火髓果","沈砚左手心"),
              **old_item("风髓果","唐蜃左手心")}
        text="唐蜃把那枚果子从左手心递给沈砚。"
        result=before(text,prev)
        self.assertFalse(result["blocked"],result)
        self.assertTrue(result["needs_review"],result)
        self.assertIn("WF122_AMBIGUOUS_FRUIT_ALIAS",
                      result["review_findings"])

    def test_unique_fruit_alias_tracks_real_transfer(self):
        prose="沈砚把那枚果子从左手心递给唐蜃。唐蜃握着火髓果。"
        report=audit(prose)
        self.assertEqual(report["hard_findings"],[])
        self.assertEqual(report["candidate_source_events"][0]["kind"],
                         "HANDOFF")

    def test_pronoun_is_not_upgraded_to_known_giver(self):
        prose="他把果子从左手心递给唐蜃。唐蜃握着火髓果。"
        report=audit(prose)
        self.assertEqual(report["hard_findings"],[],report)
        self.assertIn("WF122_TRANSFER_ACTION_NOT_SOURCE_VERIFIED",
                      report["review_findings"])
        self.assertEqual(report["candidate_source_events"],[])
        self.assertEqual(report["remaining_holders_candidate_only"]["火髓果"],
                         "沈砚左手心")

    def test_unsourced_jump_after_a_real_transfer_is_still_blocked(self):
        prose=("沈砚把火髓果从左手心递给唐蜃。"
               "火髓果又在沈砚左手心。")
        result=before(prose)
        self.assertTrue(result["blocked"])
        self.assertIn("WF116_FRUIT_TELEPORT_TO_OTHER_ACTOR",
                      result["findings"])

    def test_legacy_teeth_without_handoff_remains_hard(self):
        report=before("火髓果还在齿间。")
        self.assertTrue(report["blocked"])
        self.assertIn("WF116_FRUIT_TEETH_WITHOUT_REHANDOFF",
                      report["findings"])

    def test_consumed_fruit_claimed_present_remains_hard(self):
        previous=old_item("火髓果","已消耗（沈砚吞服）")
        result=before("火髓果还在齿间。",previous)
        self.assertTrue(result["blocked"])
        self.assertIn("WF116_CONSUMED_FRUIT_RESURRECTED",result["findings"])

    def test_narrator_hypothetical_not_actual_handover(self):
        text="如果沈砚把火髓果从左手心递给唐蜃，后果不可想象。"
        a=audit(text)
        self.assertEqual(a["candidate_source_events"],[])
        self.assertEqual(a["hard_findings"],[])
        self.assertEqual(a["remaining_holders_candidate_only"]["火髓果"],
                         "沈砚左手心")

    def test_dialogue_quote_is_not_a_real_item_action(self):
        text="唐蜃喝道：“沈砚把火髓果从左手心递给唐蜃。”"
        a=audit(text)
        self.assertEqual(a["candidate_source_events"],[])
        self.assertEqual(a["hard_findings"],[])

    def test_item_not_in_prior_is_not_implicitly_persisted(self):
        prev=old_item("火髓果","沈砚左手心")
        text="唐蜃握着赤霞丹，向沈砚伸出手。"
        a=audit(text,prev)
        self.assertEqual(a["remaining_holders_candidate_only"],
                         {"火髓果":"沈砚左手心"})
        self.assertEqual(a["hard_findings"],[])

    def test_no_canon_or_model_and_signed_report(self):
        a=audit("沈砚把火髓果从左手心递给唐蜃。")
        self.assertEqual(a["format"],FORMAT)
        self.assertEqual(a["new_model_calls"],0)
        self.assertEqual(a["R2_writes"],0)
        self.assertEqual(a["canon_writes"],0)
        self.assertTrue(a["source_item_coverage_not_universal"])
        self.assertFalse(a["contains_raw_prose"])
        rec=dict(a);signature=rec.pop("receipt_sha256")
        expect=hashlib.sha256(
            json.dumps(rec,sort_keys=True,ensure_ascii=False,
                       separators=(",",":")).encode("utf8")).hexdigest()
        self.assertEqual(signature,expect)

    def test_surgical_edit_third_actor_cannot_teleport_fruit(self):
        from writerforge.v119_revision_transaction import preview_revision
        manuscript="唐蜃退开两步。沈砚稳住身形。"
        target="唐蜃退开两步"
        out=preview_revision(
            project_id="novel",scene_id="scene-2",
            source=manuscript,
            source_sha256=hashlib.sha256(manuscript.encode()).hexdigest(),
            start=0,end=len(target),expected_original=target,
            replacement="叶青梧握着火髓果",
            previous_candidate_state=old_item("火髓果","沈砚左手心"),
            cast=CAST)
        self.assertEqual(out["status"],"BLOCKED_NEW_STATE_WARNING")
        self.assertIsNone(out["candidate_prose"])
        self.assertIn("WF116_FRUIT_TELEPORT_TO_OTHER_ACTOR",
                      out["receipt"]["new_preflight_warnings"])

    def test_out_of_budget_source_gets_uncertain_receipt_not_silent_pass(self):
        previous=old_item("火髓果","沈砚左手心")
        long="沈砚站在山门口。"*257
        report=audit(long,previous)
        self.assertIn("WF122_CLAUSE_BUDGET_EXCEEDED",
                      report["review_findings"])

    def test_real_novel_studio_reducer_carries_two_handoffs_to_next_chapter(self):
        from writerforge.v114_external_story_state import external_temporal_step
        from writerforge.v117_continuity_trace import audit_continuity
        first=external_temporal_step(
            "沈砚把火髓果往齿间一咬。"
            "沈砚把果子从齿间吐到左手心。",
            cast=CAST)
        old=first["reducer_result"]["candidate_state"]
        self.assertEqual(
            next(v for k,v in old.items()
                 if '"item"' in k and '"火髓果"' in k and
                    '"holder"' in k),
            "沈砚左手心")
        two=external_temporal_step(
            "沈砚把火髓果从左手心递给唐蜃。"
            "唐蜃把火髓果从手中递给叶青梧。",
            cast=CAST,prior=first)
        self.assertEqual(two["v122_extra_reducer_events_count"],1)
        self.assertEqual(two["reducer_result"]["error_code"],None)
        self.assertEqual(
            next(v for k,v in two["reducer_result"]["candidate_state"].items()
                 if '"item"' in k and '"火髓果"' in k and
                    '"holder"' in k),
            "叶青梧手中")
        self.assertEqual(two["canon_writes"],0)
        self.assertFalse(two["semantic_truth_verified"])
        frame=audit_continuity(two,project_id="novel-z",chapter_index=1)
        props=[x for x in frame["prop_verdicts"] if x["entity"]=="火髓果"]
        self.assertEqual(len(props),1)
        self.assertTrue(props[0]["ok"])
        self.assertEqual(props[0]["latest_state"],"叶青梧手中")
        next_chapter=external_temporal_step(
            "叶青梧沿石壁疾奔，唐蜃在后方紧追。",
            cast=CAST,prior=two)
        self.assertEqual(
            next(v for k,v in next_chapter["reducer_result"][
                 "candidate_state"].items()
                 if '"item"' in k and '"火髓果"' in k and
                    '"holder"' in k),
            "叶青梧手中")
        false_return=preflight_next_prose(
            "沈砚握着火髓果。",cast=CAST,
            previous_candidate_state=next_chapter[
                "reducer_result"]["candidate_state"])
        self.assertTrue(false_return["blocked"])
        self.assertIn("WF116_FRUIT_TELEPORT_TO_OTHER_ACTOR",
                      false_return["findings"])

    def test_reducer_dedup_keeps_single_transfer_not_double_event(self):
        from writerforge.v114_external_story_state import external_temporal_step
        first=external_temporal_step(
            "沈砚把火髓果往齿间一咬。"
            "沈砚把果子从齿间吐到左手心.",
            cast=CAST)
        second=external_temporal_step(
            "沈砚把火髓果从左手心递给唐蜃。",
            cast=CAST,prior=first)
        self.assertEqual(second["v122_extra_reducer_events_count"],0)
        self.assertEqual(second["reducer_result"]["verified_events"],1)
        self.assertEqual(second["canon_writes"],0)

    def test_invalid_cast_and_prose_fail_closed(self):
        with self.assertRaises(ItemProvenanceError):
            audit_item_provenance(
                prose="字"*20001,
                previous_candidate_state=old_item("火髓果","沈砚左手心"),
                cast=CAST)
        with self.assertRaises(ItemProvenanceError):
            audit_item_provenance(
                prose="沈砚举起剑。",
                previous_candidate_state=old_item("火髓果","沈砚左手心"),
                cast=("沈砚","沈砚"))


if __name__=="__main__":
    unittest.main()
