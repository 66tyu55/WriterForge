"""0.AR RED: actual 0.AQ G document custody crosses signed V114 turns.

Real DeepSeek source Actions 40264287305, provider artifact 12625547786:
T02 sends a particular booklet away with 周卒; T04 then has 秦渊 handle
possibly the same geography booklet WITHOUT visible return. This is
a source question, NOT proved literary contradiction, and legitimate
ellipsis/another copy must not be hard-rejected. The real source hashes:
T02 e5ed869a300904e63a43e063a5d9e71e6d79d21a6ecf939d991e9612dd4fb473
T04 b867d7903bd94e4cbaaba8d59889a1ffabbb8e725b317affe1f271d7873b5c33.
No new literary scorer, independent memory, model, R2 or Canon.
"""
from __future__ import annotations

import unittest
from hashlib import sha256

from writerforge.v122_item_provenance import (
    audit_physical_relation_sources, ItemProvenanceError, _digest,
)
from writerforge.v116_state_delta import preflight_next_prose
from writerforge.v114_external_story_state import (
    external_temporal_step,temporal_prompt,
)

OUTGOING=(
    "周卒把册子揣进贴身的油布囊里，应声出去。"
    "门外马蹄又响了一回，秦渊没有起身，只照原来的墨迹核对时辰。"
)
REAPPEARING=(
    "秦渊把纸折好，与地形册子一并纳入封套，用火漆点了，"
    "又取过换马单子核第三处驿站的记号。"
    "他忽然想起方才那骑，仍不知来自哪里。"
)
RETURNED="周卒回来把册子交还秦渊，又去马厩照看旧道上的马。"
DIFFERENT=(
    "秦渊把纸折好，与另一本册子一并纳入封套，用火漆点了。"
    "那是刚写成的副本，不是周卒已经带走的旧册。"
)
QUIET="一夜过去，营外下起细雨，秦渊并不急于认定主帅已经读过文书。"
RETROSPECTIVE="秦渊回忆中把纸折好，与地形册子一并纳入封套，那是昨日白天的事情。"


def checksum(s): return sha256(s.encode("utf8")).hexdigest()


class SourceFirstPortableDocumentReview(unittest.TestCase):
    def test_genuine_booklet_out_then_unreturned_same_book_possible_alias_is_review_only(self):
        a=audit_physical_relation_sources(prose=OUTGOING)
        self.assertEqual(len(a["document_custody_open_sources"]),1)
        original=a["document_custody_open_sources"][0]
        self.assertEqual(original["item_literal"],"册子")
        self.assertEqual(original["holder_literal"],"周卒")
        self.assertEqual(original["source_quote_sha256"],checksum("周卒把册子揣进贴身的油布囊里，应声出去"))
        b=audit_physical_relation_sources(
            prose=REAPPEARING,previous_relation_receipt=a)
        self.assertTrue(b["document_custody_current_needs_review"])
        self.assertEqual(len(b["document_custody_current_review_pairs"]),1)
        q=b["document_custody_current_review_pairs"][0]
        self.assertEqual(q["item_identity_scope"],"POSSIBLE_DOCUMENT_ALIAS")
        self.assertEqual(q["earlier_holder_literal"],"周卒")
        self.assertEqual(q["later_holder_literal"],"秦渊")
        self.assertEqual(q["earlier_source_sha256"],checksum(OUTGOING))
        self.assertEqual(q["later_source_sha256"],checksum(REAPPEARING))
        self.assertFalse(q["literary_error_proven"])
        self.assertTrue(q["omitted_return_or_distinct_copy_may_explain"])
        self.assertFalse(b["document_custody_authoritative_holder_written"])
        self.assertEqual(b["canon_writes"],0)
        pre=preflight_next_prose(
            REAPPEARING,previous_candidate_state={},
            previous_relation_receipt=a,cast=("秦渊","周卒"))
        self.assertFalse(pre["blocked"])
        self.assertTrue(pre["needs_review"])
        self.assertIn("WF122_DOCUMENT_CUSTODY_SOURCE_REVIEW",pre["review_findings"])

    def test_explicit_narrated_return_prevents_false_red_and_clears_stale_holder(self):
        outgoing=audit_physical_relation_sources(prose=OUTGOING)
        returned=audit_physical_relation_sources(
            prose=RETURNED,previous_relation_receipt=outgoing)
        self.assertFalse(returned["document_custody_current_needs_review"])
        self.assertEqual(returned["document_custody_open_sources"][0]["holder_literal"],"秦渊")
        after=audit_physical_relation_sources(
            prose=REAPPEARING,previous_relation_receipt=returned)
        self.assertFalse(after["document_custody_current_needs_review"])

    def test_another_copy_ellipsis_and_recollection_are_not_proved_contradictions(self):
        outgoing=audit_physical_relation_sources(prose=OUTGOING)
        for story in (DIFFERENT,RETROSPECTIVE):
            with self.subTest(story=story[:9]):
                result=audit_physical_relation_sources(
                    prose=story,previous_relation_receipt=outgoing)
                self.assertFalse(result["document_custody_current_needs_review"])
                self.assertEqual(result["canon_writes"],0)

    def test_quiet_intervening_turn_carries_source_without_claiming_new_transfer(self):
        outgoing=audit_physical_relation_sources(prose=OUTGOING)
        next_state=audit_physical_relation_sources(
            prose=QUIET,previous_relation_receipt=outgoing)
        self.assertFalse(next_state["document_custody_current_needs_review"])
        self.assertEqual(next_state["document_custody_open_sources"][0]["source_quote_sha256"],
                         outgoing["document_custody_open_sources"][0]["source_quote_sha256"])
        after=audit_physical_relation_sources(
            prose=REAPPEARING,previous_relation_receipt=next_state)
        self.assertTrue(after["document_custody_current_needs_review"])
        self.assertEqual(len(after["document_custody_open_source_reviews"]),1)
        later=audit_physical_relation_sources(
            prose=QUIET,previous_relation_receipt=after)
        self.assertFalse(later["document_custody_current_needs_review"])
        self.assertEqual(len(later["document_custody_open_source_reviews"]),1)
        self.assertEqual(
            later["document_custody_open_source_reviews"][0]["later_source_sha256"],
            checksum(REAPPEARING))

    def test_real_v114_reducer_keeps_same_signed_debt_and_delivers_optional_writer_context(self):
        actors=("秦渊","周卒")
        first=external_temporal_step(OUTGOING,cast=actors)
        second=external_temporal_step(QUIET,cast=actors,prior=first)
        third=external_temporal_step(REAPPEARING,cast=actors,prior=second)
        self.assertEqual(third["source_sha256"],checksum(REAPPEARING))
        self.assertEqual(third["canon_writes"],0)
        evidence=third["v122_physical_relation_source_receipt"]
        self.assertTrue(evidence["document_custody_current_needs_review"])
        self.assertEqual(len(evidence["document_custody_open_source_reviews"]),1)
        hint=temporal_prompt(third)
        self.assertIn("周卒把册子揣进",hint)
        self.assertIn("与地形册子一并纳入",hint)
        self.assertIn("保留未知",hint)
        self.assertIn("非已判文学错误",hint)
        self.assertNotIn("必须删除",hint)
        fourth=external_temporal_step(QUIET,cast=actors,prior=third)
        carry=fourth["v122_physical_relation_source_receipt"]
        self.assertEqual(len(carry["document_custody_open_source_reviews"]),1)
        self.assertFalse(carry["document_custody_current_needs_review"])
        self.assertIn("保留未知",temporal_prompt(fourth))

    def test_tampered_custody_source_receipt_never_turns_into_certified_item_state(self):
        previous=audit_physical_relation_sources(prose=OUTGOING)
        forged={**previous,"source_sha256":"0"*64}
        with self.assertRaises(ItemProvenanceError):
            audit_physical_relation_sources(
                prose=REAPPEARING,previous_relation_receipt=forged)
        # Even if an attacker recomputes a raw, unkeyed SHA, the claimed
        # actor is absent from the source quote and cannot be accepted.
        import copy
        forged=copy.deepcopy(previous)
        forged["document_custody_open_sources"][0]["holder_literal"]="陌生人"
        forged["receipt_sha256"]=_digest({
            k:v for k,v in forged.items() if k!="receipt_sha256"})
        with self.assertRaises(ItemProvenanceError):
            audit_physical_relation_sources(
                prose=REAPPEARING,previous_relation_receipt=forged)


if __name__=="__main__":
    unittest.main()
