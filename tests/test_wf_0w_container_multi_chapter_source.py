"""0.W: existing V122/V114/V117 physical source boundary across boxes/items/chapters.

Only synthetic adversarial inputs. No model calls, no training, no R2 writes,
no new memory owner. A source-signed unresolved relation cannot vanish during
two intervening quiet chapters nor become a downstream story-world fact.
"""
import copy
import json
import unittest

from writerforge.v122_item_provenance import audit_physical_relation_sources
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v114_external_story_state import external_temporal_step
from writerforge.v117_continuity_trace import (
    preflight_continuation, make_resume, read_resume,
)


CONFLICT=("铜牌还在木匣里，只是铜牌已经被人从木匣里取出来。")
QUIET_2="守夜人望着远处的山峰，记录一夜的雨量，决定天亮再检查桥墩。"
QUIET_3="第二天雨还在下，他继续登记街道上的交易，没有碰那座山里的旧物件。"
DEPENDENT="铜牌还在木匣里。林栖按这条没有被澄清的消息决定避开旧仓库。"


class ContainerSourceRelations(unittest.TestCase):
    def test_container_presence_and_removal_are_unresolved_same_time_claims(self):
        view=audit_physical_relation_sources(prose=CONFLICT)
        self.assertEqual(view["review_status"],"NEEDS_SOURCE_RELATION_REVIEW")
        self.assertEqual(len(view["review_pairs"]),1)
        pair=view["review_pairs"][0]
        self.assertEqual(pair["relation_family"],"CONTAINMENT")
        self.assertEqual(pair["item_identity_evidence"],"EXACT_LITERAL")
        self.assertEqual(pair["contact_identity_evidence"],"EXACT_LITERAL")
        self.assertEqual([x["relation"] for x in view["claims"]],
                         ["CONTAINED","REMOVED"])
        self.assertEqual(len(view["open_relation_reviews"]),1)
        self.assertTrue(view["open_relation_debts_are_source_only_not_state_cells"])
        self.assertEqual(view["model_calls"],0)

    def test_distinct_objects_and_containers_never_merge(self):
        cases=(
            "红铜牌还在木匣里，只是蓝铜牌被人从木匣里取出来。",
            "铜牌还在木匣里，只是铜牌被人从铁箱里取出来。",
            "铜牌还在木匣里，只是令牌已经被人从木匣里取出来。",
            "铜牌仍在左边木匣里，只是铜牌被人从右边木匣里取出来。",
            "铜牌还在木匣里，只是银牌已经被人从铁箱里取出来。"
        )
        for p in cases:
            with self.subTest(p=p):
                result=audit_physical_relation_sources(prose=p)
                self.assertEqual(result["review_pairs"],[],result)

    def test_honest_temporal_sequence_and_unwritten_actor_remain_valid(self):
        cases=(
            "铜牌还在木匣里，后来铜牌被人从木匣里取出来。",
            "铜牌还在木匣里，随后铜牌被人从木匣里取出来。",
            "铜牌放在木匣里，然后林栖把铜牌从木匣里取出来。",
            "不知道是谁拿走了铜牌。堤上的人暂时没有发现新的线索。",
            "林栖猜铜牌还在木匣里，但说不清谁进入过库房。",
            "“铜牌还在木匣里，只是铜牌被人从木匣里取出来。”",
        )
        for p in cases:
            with self.subTest(p=p):
                self.assertEqual(audit_physical_relation_sources(
                    prose=p)["review_pairs"],[])

    def test_container_alias_not_assumed_to_be_identical_owner(self):
        p="铜牌还在旧木匣里，只是铜牌已经被人从木匣中取出来。"
        out=audit_physical_relation_sources(prose=p)
        self.assertEqual(out["review_pairs"][0]["contact_identity_evidence"],
                         "POSSIBLE_CONTACT_AREA_ALIAS")
        self.assertTrue(out["identified_referents_are_hypotheses_not_state_cells"])

    def test_multiple_items_are_covered_independently(self):
        p=(CONFLICT+"银牌仍在铁箱中，只是银牌已经被人从铁箱里拿出来。")
        x=audit_physical_relation_sources(prose=p)
        self.assertEqual(len(x["review_pairs"]),2,x)
        ids={r["first_item_literal"] for r in x["review_pairs"]}
        self.assertEqual(ids,{"铜牌","银牌"})
        self.assertEqual(len(x["open_relation_reviews"]),2)

    def test_item_holder_reducer_must_not_treat_location_as_ownership(self):
        cp=external_temporal_step(CONFLICT,cast=("林栖","程满"))
        details=cp["v122_physical_relation_source_receipt"]
        self.assertEqual(len(details["open_relation_reviews"]),1)
        self.assertFalse(any(
            '"contains"' in key or '"inside"' in key or '"attached"' in key
            for key in cp["reducer_result"]["candidate_state"]))
        self.assertEqual(cp["canon_writes"],0)


class SignedUncertaintyAcrossChapters(unittest.TestCase):
    def make_sequence(self):
        first=external_temporal_step(CONFLICT,cast=("林栖",))
        second=external_temporal_step(QUIET_2,cast=("林栖",),prior=first)
        third=external_temporal_step(QUIET_3,cast=("林栖",),prior=second)
        return first,second,third

    def test_old_source_obligation_survives_two_unrelated_chapters(self):
        first,second,third=self.make_sequence()
        for old,new in ((first,second),(second,third)):
            r=new["v122_physical_relation_source_receipt"]
            self.assertEqual(r["open_relations_forwarded_from_signed_prior"],1)
            self.assertEqual(len(r["open_relation_reviews"]),1)
            self.assertEqual(r["open_relation_reviews"][0]["origin_source_sha256"],
                             first["source_sha256"])
            self.assertEqual(r["review_pairs"],[])
            self.assertEqual(r["dependent_on_unresolved_previous_relation"],[])
            self.assertEqual(new["canon_writes"],0)
            self.assertEqual(old["receipt_sha256"],
                             new["previous_checkpoint_sha256"])

        signed=make_resume(project_id="wf-0w",scene_id="container-story",
                           chapter_index=3,checkpoint=third)
        self.assertEqual(read_resume(
            signed,project_id="wf-0w",scene_id="container-story"),
            third)
        self.assertEqual(signed["canon_writes"],0)

    def test_only_actual_dependent_continuation_is_held(self):
        first,second,third=self.make_sequence()
        for cp,text in ((first,QUIET_2),(second,QUIET_3)):
            result=preflight_continuation(
                text,cp,project_id="wf-0w",chapter_index=3,cast=("林栖",))
            self.assertFalse(
                result["physical_relation_must_not_be_fact_or_downstream_parent"],
                result)
            self.assertEqual(result["physical_relation_dependent_on_unresolved_source"],[])
        future=preflight_continuation(
            DEPENDENT,third,project_id="wf-0w",chapter_index=4,
            cast=("林栖",))
        self.assertTrue(future["needs_review"])
        self.assertTrue(future["physical_relation_must_not_be_fact_or_downstream_parent"])
        dependencies=future["physical_relation_dependent_on_unresolved_source"]
        self.assertEqual(len(dependencies),1)
        self.assertEqual(dependencies[0]["prior_relation_source_sha256"],
                         first["source_sha256"])
        self.assertEqual(dependencies[0]["current_source_quote"],
                         "铜牌还在木匣里")

    def test_old_receipt_tamper_fails_before_v114_state_update(self):
        first,second,_=self.make_sequence()
        unsafe=copy.deepcopy(second)
        unsafe["v122_physical_relation_source_receipt"]["open_relation_reviews"][0][
            "first_source_quote_sha256"]="0"*64
        with self.assertRaises(ValueError):
            audit_physical_relation_sources(
                prose=QUIET_3,
                previous_relation_receipt=unsafe[
                    "v122_physical_relation_source_receipt"])

    def test_fresh_origins_accumulate_without_evicting_old_evidence(self):
        old=None
        for index in range(3):
            name=("铜牌","银牌","金牌")[index]
            site=("木匣","铁箱","石盒")[index]
            p=f"{name}还在{site}里，只是{name}被人从{site}里取出来。"
            old=audit_physical_relation_sources(
                prose=p,previous_relation_receipt=old)
            self.assertEqual(len(old["open_relation_reviews"]),index+1,old)
            self.assertEqual(old["canon_writes"],0)
        self.assertEqual(len({x["origin_source_sha256"]
                              for x in old["open_relation_reviews"]}),3)

    def test_budget_overflow_is_refusal_not_silent_discard(self):
        old=None
        items=("铜牌","银牌","金牌","玉牌","木牌","铁牌","青牌","白牌")
        for name in items:
            p=f"{name}还在木匣里，只是{name}被人从木匣里取出来。"
            old=audit_physical_relation_sources(
                prose=p,previous_relation_receipt=old)
        self.assertEqual(len(old["open_relation_reviews"]),8)
        with self.assertRaisesRegex(ValueError,
                                    "WF122_OPEN_RELATION_DEBT_BUDGET_EXCEEDED"):
            audit_physical_relation_sources(
                prose="红牌还在木匣里，只是红牌被人从木匣里取出来。",
                previous_relation_receipt=old)

    def test_one_chapter_cannot_drop_ninth_relation_review(self):
        names=("铜牌","银牌","金牌","玉牌","木牌","铁牌","青牌","白牌","红牌")
        p="".join(f"{name}还在木匣里，只是{name}被人从木匣里取出来。"
                  for name in names)
        with self.assertRaisesRegex(
            ValueError, "WF122_PHYSICAL_CONFLICT_SOURCE_BUDGET_EXCEEDED"):
            audit_physical_relation_sources(prose=p)


if __name__=="__main__":
    unittest.main()
