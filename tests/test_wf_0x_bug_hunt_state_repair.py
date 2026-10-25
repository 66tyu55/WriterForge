"""Failure-first WF defects: same warning code hides new errors; old debt cannot retire.

These tests are intentionally about WF engineering, NOT about coaxing the
novelist into LOOK_BACK or endorsing model prose. Every sample is synthetic.
"""
import unittest

from writerforge.v119_revision_transaction import (
    preview_revision, compare_source_repair_impact,
)
from writerforge.v122_item_provenance import audit_physical_relation_sources
from writerforge.v114_external_story_state import (
    external_temporal_step, replay_revised_source_checkpoint,
)
from writerforge.v117_continuity_trace import preflight_continuation

OLD="铜牌还在木匣里，只是铜牌已经被人从木匣里取出来。"
OTHER="银牌还在铁箱里，只是银牌已经被人从铁箱里拿出来。"
CALM="姜岚逐字誊下残损的账册，尚不知是谁触碰了它。她没有将传闻称作已证事实。"
GOOD="铜牌仍在木匣里。姜岚小心将所见写入自己的账册，等待白天再核对这件事。"

def sha(text):
    import hashlib
    return hashlib.sha256(text.encode("utf8")).hexdigest()

def edit(src,target,replacement):
    first=src.index(target)
    return preview_revision(
        project_id="wf-bug-hunt",scene_id="source-locked-repair",
        source=src,source_sha256=sha(src),
        start=first,end=first+len(target),
        expected_original=target,replacement=replacement,
        previous_candidate_state={},cast=())

class FalseGreenRiskCodeCollision(unittest.TestCase):
    def test_old_relation_replaced_by_different_new_relation_is_new_risk(self):
        # TODAY V119 reports only the SAME symbolic warning code for both.
        src=OLD+CALM
        patch=edit(src,OLD,OTHER)
        result=compare_source_repair_impact(preview_receipt=patch["receipt"])
        self.assertEqual(result["status"],"HELD_NEW_UNVERIFIED_SOURCE_RISK",result)
        self.assertEqual(len(result["new_source_relation_issue_keys"]),1,result)
        self.assertEqual(len(result["retired_source_relation_issue_keys"]),1,result)
        self.assertNotEqual(
            result["new_source_relation_issue_keys"],
            result["retired_source_relation_issue_keys"])

    def test_additional_different_relation_cannot_hide_under_existing_code(self):
        src=OLD+CALM
        patch=edit(src,CALM,CALM+OTHER)
        result=compare_source_repair_impact(preview_receipt=patch["receipt"])
        self.assertEqual(result["status"],"HELD_NEW_UNVERIFIED_SOURCE_RISK",result)
        self.assertEqual(len(result["new_source_relation_issue_keys"]),1,result)
        self.assertEqual(len(result["still_open_source_relation_issue_keys"]),1,result)

    def test_same_old_relation_without_source_fix_stays_old_risk(self):
        src=OLD+CALM
        patch=edit(src,"逐字誊下","仔细誊下")
        result=compare_source_repair_impact(preview_receipt=patch["receipt"])
        self.assertEqual(result["status"],"HELD_EXISTING_SOURCE_RELATION_RISK",result)
        self.assertEqual(result["new_source_relation_issue_keys"],[])
        self.assertEqual(len(result["still_open_source_relation_issue_keys"]),1,result)


class RepeatedSourceQuoteMustNotBeSkipped(unittest.TestCase):
    def test_two_same_state_quotes_plus_detach_must_still_be_checked(self):
        # Today's V122 silently DROPS the duplicated quoted state because
        # prose.count(quote) != 1, even when exact source offsets exist.
        p=("铜牌还在木匣里，铜牌还在木匣里，"
           "只是铜牌已经被人从木匣里取出来。")
        report=audit_physical_relation_sources(prose=p)
        self.assertTrue(report["current_source_needs_review"],report)
        self.assertEqual(len(report["claims"]),3,report)
        self.assertEqual(len(report["review_pairs"]),2,report)
        self.assertNotEqual(
            report["review_pairs"][0]["first_source_start"],
            report["review_pairs"][1]["first_source_start"])
        from writerforge.v116_state_delta import preflight_next_prose
        from writerforge.writing_assist import _physical_relation_source_hold
        gate=preflight_next_prose(
            p,previous_candidate_state={},cast=())
        self.assertTrue(gate["needs_review"])
        hold=_physical_relation_source_hold(prose=p,preflight=gate)
        self.assertIsNotNone(hold)
        self.assertEqual(hold["status"],"HELD_NEEDS_SOURCE_RELATION_REVIEW")

    def test_duplicate_same_state_alone_is_not_a_world_contradiction(self):
        p="铜牌还在木匣里，铜牌还在木匣里。"
        report=audit_physical_relation_sources(prose=p)
        self.assertEqual(report["review_pairs"],[])
        self.assertEqual(len(report["claims"]),2)

class SourceLockedV114RebaseAfterV119(unittest.TestCase):
    def test_true_author_source_edit_rebuilds_checkpoint_not_poisoned_forever(self):
        old=OLD+CALM
        prior_checkpoint=external_temporal_step(old,cast=("姜岚",))
        self.assertEqual(len(prior_checkpoint[
            "v122_physical_relation_source_receipt"]["open_relation_reviews"]),1)
        patch=edit(old,OLD,GOOD)
        transaction=replay_revised_source_checkpoint(
            source_before=old,
            checkpoint_before=prior_checkpoint,
            v119_preview_receipt=patch["receipt"],
            corrected_source=patch["candidate_prose"],
            parent_checkpoint=None,cast=("姜岚",))
        self.assertEqual(transaction["status"],
                         "SOURCE_CHANGED_REQUIRES_DOWNSTREAM_REPLAY",transaction)
        self.assertEqual(transaction["retired_old_source_relation_count"],1)
        self.assertEqual(transaction["new_source_relation_count"],0)
        self.assertTrue(transaction["all_old_derived_downstream_invalidated"])
        self.assertFalse(transaction["author_accepted"])
        self.assertFalse(transaction["literary_improvement_verified"])
        revised=transaction["recomputed_unaccepted_v114_checkpoint"]
        self.assertNotEqual(revised["receipt_sha256"],
                            prior_checkpoint["receipt_sha256"])
        self.assertEqual(revised["source_sha256"],sha(patch["candidate_prose"]))
        self.assertEqual(
            revised["v122_physical_relation_source_receipt"]["open_relation_reviews"],[])
        quiet=external_temporal_step(
            "她第二天继续整理账簿，只把确实看见的水位刻在原始表格上。",
            prior=revised,cast=("姜岚",))
        self.assertEqual(
            quiet["v122_physical_relation_source_receipt"]["open_relation_reviews"],[])
        # It would be WRONG to use quiet's old pre-revision parent chain.
        self.assertEqual(quiet["previous_checkpoint_sha256"],
                         revised["receipt_sha256"])

    def test_replaying_one_revised_chapter_preserves_older_unresolved_debt(self):
        prior_source=OTHER+CALM
        parent=external_temporal_step(prior_source,cast=("姜岚",))
        second_source=OLD+CALM
        old_second=external_temporal_step(
            second_source,cast=("姜岚",),prior=parent)
        self.assertEqual(len(old_second[
            "v122_physical_relation_source_receipt"]["open_relation_reviews"]),2)
        patch=edit(second_source,OLD,GOOD)
        rewritten=replay_revised_source_checkpoint(
            source_before=second_source,
            checkpoint_before=old_second,
            v119_preview_receipt=patch["receipt"],
            corrected_source=patch["candidate_prose"],
            parent_checkpoint=parent,cast=("姜岚",))
        self.assertEqual(rewritten["retired_old_source_relation_count"],1)
        self.assertEqual(rewritten["new_source_relation_count"],1)
        fresh=rewritten["recomputed_unaccepted_v114_checkpoint"]
        self.assertEqual(fresh["previous_checkpoint_sha256"],
                         parent["receipt_sha256"])
        entry=fresh["v122_physical_relation_source_receipt"]["open_relation_reviews"][0]
        self.assertEqual(entry["origin_source_sha256"],parent["source_sha256"])
        self.assertEqual(entry["first_item_literal"],"银牌")
        with self.assertRaisesRegex(Exception,"WF114_REVISION_MISSING_OR_WRONG_PARENT"):
            replay_revised_source_checkpoint(
                source_before=second_source,
                checkpoint_before=old_second,
                v119_preview_receipt=patch["receipt"],
                corrected_source=patch["candidate_prose"],
                parent_checkpoint=None,cast=("姜岚",))

    def test_edit_outside_source_risk_does_not_retire_it(self):
        old=OLD+CALM
        cp=external_temporal_step(old,cast=("姜岚",))
        patch=edit(old,"逐字誊下","仔细誊下")
        revised=replay_revised_source_checkpoint(
            source_before=old,checkpoint_before=cp,
            v119_preview_receipt=patch["receipt"],
            corrected_source=patch["candidate_prose"],
            parent_checkpoint=None,cast=("姜岚",))
        self.assertEqual(revised["retired_old_source_relation_count"],0)
        self.assertEqual(revised["new_source_relation_count"],1)
        self.assertEqual(len(revised[
            "recomputed_unaccepted_v114_checkpoint"][
                "v122_physical_relation_source_receipt"]["open_relation_reviews"]),1)

    def test_stale_sha_or_unrelated_new_source_must_fail_closed(self):
        old=OLD+CALM
        cp=external_temporal_step(old,cast=("姜岚",))
        patch=edit(old,OLD,GOOD)
        args=dict(source_before=old,checkpoint_before=cp,
                  v119_preview_receipt=patch["receipt"],
                  corrected_source=patch["candidate_prose"],
                  parent_checkpoint=None,cast=("姜岚",))
        for changed in (
            dict(source_before=old+"伪"),
            dict(corrected_source=patch["candidate_prose"]+"伪"),
            dict(v119_preview_receipt={
                **patch["receipt"],"candidate_sha256":"0"*64}),
        ):
            with self.subTest(changed=changed.keys()):
                with self.assertRaises(Exception):
                    replay_revised_source_checkpoint(**(args|changed))

if __name__=="__main__":
    unittest.main()
