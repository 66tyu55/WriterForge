"""V119: no-model transactional edit gate; narrative claims remain unverified."""
import hashlib
import json
import unittest

from writerforge.v119_revision_transaction import (
    preview_revision, inspect_whole_rewrite, RevisionTransactionError,
)


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


SOURCE = ("【旧稿】沈砚右臂受伤，退到石墙边。唐蜃没有追击。"
          "火髓果仍在沈砚左掌，夜雨敲着屋檐。")


def kw(source=SOURCE, target="退到石墙边", replacement="借着石墙遮住右臂",
       locks=("火髓果仍在沈砚左掌",)):
    start = source.index(target)
    return dict(
        project_id="novel", scene_id="chapter-8",
        source=source, source_sha256=sha(source),
        start=start, end=start+len(target),
        expected_original=target, replacement=replacement,
        pinned_quotes=locks,
    )


def state(domain, actor, predicate, value):
    key = json.dumps([domain, actor, predicate, "author_plan", None],
                     ensure_ascii=False, separators=(",", ":"))
    return {key: value}


class RevisionGateTests(unittest.TestCase):
    def test_only_target_changes_and_receipt_hash(self):
        k = kw()
        out = preview_revision(**k)
        prose = out["candidate_prose"]
        self.assertEqual(out["status"], "PROVISIONAL_REVIEW")
        self.assertEqual(
            prose, SOURCE.replace("退到石墙边", "借着石墙遮住右臂"))
        self.assertEqual(prose[:k["start"]], SOURCE[:k["start"]])
        self.assertEqual(
            prose[k["start"]+len(k["replacement"]):], SOURCE[k["end"]:])
        receipt = out["receipt"]
        self.assertEqual(receipt["candidate_sha256"], sha(prose))
        claimed_hash = receipt.pop("receipt_sha256")
        self.assertEqual(
            claimed_hash,
            hashlib.sha256(json.dumps(
                receipt, sort_keys=True, ensure_ascii=False,
                separators=(",", ":")).encode("utf-8")).hexdigest())
        self.assertFalse(receipt["intent_fulfillment_verified"])
        self.assertFalse(receipt["literary_quality_verified"])
        self.assertEqual(receipt["model_calls"], 0)
        self.assertEqual(receipt["canon_writes"], 0)

    def test_unrelated_rewrite_rejected_even_if_plot_is_plausible(self):
        k = kw()
        bad = (SOURCE.replace("退到石墙边", "借着石墙遮住右臂")
               .replace("唐蜃没有追击", "唐蜃追了上来"))
        with self.assertRaisesRegex(
                RevisionTransactionError, "UNRELATED_TEXT_CHANGED"):
            inspect_whole_rewrite(
                proposed_whole_text=bad,
                **{n: v for n, v in k.items() if n != "replacement"})

    def test_whole_document_with_exact_patch_passes(self):
        k = kw()
        whole = SOURCE.replace("退到石墙边", "借着石墙遮住右臂")
        res = inspect_whole_rewrite(
            proposed_whole_text=whole,
            **{n: v for n, v in k.items() if n != "replacement"})
        self.assertEqual(res["candidate_prose"], whole)

    def test_stale_document_fails_closed(self):
        k = kw()
        k["source_sha256"] = sha("别的版本")
        with self.assertRaisesRegex(
                RevisionTransactionError, "STALE_SOURCE_HASH"):
            preview_revision(**k)

    def test_stale_target_fails_closed(self):
        k = kw()
        k["expected_original"] = "向前冲锋"
        with self.assertRaisesRegex(
                RevisionTransactionError, "SPAN_NO_LONGER"):
            preview_revision(**k)

    def test_pinned_fact_cannot_be_replaced(self):
        k = kw(source=SOURCE, target="火髓果仍在沈砚左掌",
               replacement="火髓果早被唐蜃吞了")
        with self.assertRaisesRegex(
                RevisionTransactionError, "OVERLAPS_EDIT"):
            preview_revision(**k)

    def test_pinned_fact_cannot_be_duplicated(self):
        k = kw(replacement="火髓果仍在沈砚左掌，然而沈砚退后。")
        with self.assertRaisesRegex(
                RevisionTransactionError, "PINNED_QUOTE_REPLICATED"):
            preview_revision(**k)

    def test_bounded_patch(self):
        k = kw(replacement="字"*1801)
        with self.assertRaisesRegex(
                RevisionTransactionError, "REPLACEMENT_SIZE"):
            preview_revision(**k)

    def test_no_automatic_acceptance_without_state_checkpoint(self):
        receipt = preview_revision(**kw())["receipt"]
        self.assertTrue(receipt["model_justification_was_not_evidence"])
        self.assertTrue(receipt["only_declared_selection_changed"])
        self.assertEqual(receipt["preflight_coverage"],
                         "NO_PRIOR_STATE_PROVIDED")
        self.assertFalse(receipt["author_accepted"])
        self.assertFalse(receipt["raw_manuscript_in_receipt"])

    def test_new_right_arm_violation_cannot_be_auto_accepted(self):
        k = kw(replacement="右手挥剑，逼退唐蜃")
        prior = state("character", "沈砚", "右臂可用性", "受限")
        out = preview_revision(**k, previous_candidate_state=prior)
        self.assertEqual(out["status"], "BLOCKED_NEW_STATE_WARNING")
        self.assertIsNone(out["candidate_prose"])
        self.assertIn("WF116_ARM_USED_WITHOUT_RECOVERY",
                      out["receipt"]["new_preflight_warnings"])

    def test_new_fruit_location_jump_cannot_be_auto_accepted(self):
        source = "沈砚背贴石墙，左手扶墙，躲开飞刃。"
        k = kw(source=source, target="左手扶墙",
               replacement="火髓果还在齿间", locks=())
        prior = state("item", "火髓果", "holder", "沈砚左手心")
        out = preview_revision(**k, previous_candidate_state=prior)
        self.assertEqual(out["status"], "BLOCKED_NEW_STATE_WARNING")
        self.assertIsNone(out["candidate_prose"])
        self.assertIn("WF116_FRUIT_TEETH_WITHOUT_REHANDOFF",
                      out["receipt"]["new_preflight_warnings"])

    def test_repair_can_clear_baseline_warning_but_not_prove_literary_quality(self):
        source = "沈砚右臂受伤后，右手挥剑，唐蜃避退。"
        k = kw(source=source, target="右手挥剑", replacement="左手撑墙",
               locks=())
        prior = state("character", "沈砚", "右臂可用性", "受限")
        out = preview_revision(**k, previous_candidate_state=prior)
        self.assertEqual(out["status"], "PROVISIONAL_REVIEW")
        self.assertIn("WF116_ARM_USED_WITHOUT_RECOVERY",
                      out["receipt"]["baseline_preflight_warnings"])
        self.assertEqual(out["receipt"]["revision_preflight_warnings"], [])
        self.assertFalse(out["receipt"]["intent_fulfillment_verified"])

    def test_real_writing_facade_offers_opt_in_no_model_revision(self):
        from writerforge.writing_assist import AutonomousWriting
        class FakeAssist:
            project_id = "novel"
            scene_id = "chapter-8"
        result = AutonomousWriting(FakeAssist()).preview_local_revision(**{
            name: value for name, value in kw().items()
            if name not in ("project_id", "scene_id")
        })
        self.assertEqual(result["status"], "PROVISIONAL_REVIEW")
        self.assertFalse(result["receipt"]["literary_quality_verified"])


if __name__ == "__main__":
    unittest.main()
