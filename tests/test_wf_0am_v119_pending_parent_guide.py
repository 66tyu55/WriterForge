"""0.AM RED: V119 repair guide still demands an OBSERVED effect for decisions.

0.AI source-verified DeepSeek historical original already has a legal
decision/action quote with effect_quote=null, and V96/V98 propagate it.
V119 must not force the same author to invent immediate consequences when
repairing that decision or a child of it. Exact source SHA, no new model,
no book, R2, Canon, or inferred literary verdict.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import unittest

from writerforge.v119_revision_transaction import (
    prepare_source_repair_contract,RevisionTransactionError,
)
from test_wf_0ai_decision_effect_pending import (
    HISTORY_REAL,HISTORY_REAL_SHA,HISTORY_ACTION,beat,pending_history,
)

CHILD=(
    "驿站门前的薄雪被踩出几个模糊脚印，秦渊知道并非所有经过的人"
    "都是给主帅送信的驿卒。他把灯下的纸重新铺平，记住了昨天的时辰。"
    "亲兵想催他下令，他却选择先等等，愿意承受这一夜消息未明的焦灼。"
    "屋外马蹄声渐渐远去，谁能证明那匹马已经走上去主帅营的旧路？"
)


def digest(s):return sha256(s.encode("utf8")).hexdigest()


class RepairGuideDoesNotInventObservedOutcomes(unittest.TestCase):
    def test_real_decision_can_preserve_action_with_effect_yet_unobserved(self):
        self.assertEqual(digest(HISTORY_REAL),HISTORY_REAL_SHA)
        self.assertEqual(pending_history()["receipt"][
            "source_causal_review_reason"],"DECISION_EFFECT_UNOBSERVED")
        doc=prepare_source_repair_contract(
            source=HISTORY_REAL,source_sha256=HISTORY_REAL_SHA,
            beat=beat(),accepted=(),
            original_trace={
                "action_quote":HISTORY_ACTION,
                "effect_quote":None,"parent_effect_quote":None})
        self.assertFalse(doc["source_action_effect_required"])
        self.assertTrue(doc["source_action_quote_required"])
        self.assertTrue(doc["decision_effect_unobserved_source_only"])
        self.assertIsNone(doc["actual_previous_effect_quote"])
        self.assertEqual(doc["new_model_calls"],0)
        self.assertEqual(doc["canon_writes"],0)
        self.assertTrue(doc["no_literary_grade_or_host_authored_text"])

    def test_child_repair_guidance_uses_signed_actual_parent_action_not_fake_effect(self):
        previous=pending_history()
        doc=prepare_source_repair_contract(
            source=CHILD,source_sha256=digest(CHILD),
            beat=beat(kind="quiet",actor="秦渊",parent="t01",id="t02"),
            accepted=(previous,),
            original_trace={
                "action_quote":None,"effect_quote":None,
                "parent_effect_quote":None})
        self.assertEqual(doc["previous_causal_parent_id"],"t01")
        self.assertIsNone(doc["actual_previous_effect_quote"])
        self.assertEqual(doc["actual_previous_pending_action_quote"],
                         HISTORY_ACTION)
        self.assertTrue(doc["previous_parent_effect_unobserved"])
        self.assertTrue(doc["unverified_relation_cannot_become_downstream_fact"])
        self.assertEqual(doc["downstream_after_change"],
                         "MUST_REGENERATE_FROM_REVISED_SOURCE")

    def test_tampered_parent_receipt_and_prose_are_rejected_before_writer(self):
        source=pending_history()
        for value in (
            {**source,"receipt":{**source["receipt"],
                                  "receipt_sha256":"0"*64}},
            {**source,"prose":source["prose"]+"后面凭空加上的情节"},
        ):
            with self.subTest(case=list(value)):
                with self.assertRaises(RevisionTransactionError):
                    prepare_source_repair_contract(
                        source=CHILD,source_sha256=digest(CHILD),
                        beat=beat(kind="quiet",actor="秦渊",
                                  parent="t01",id="t02"),
                        accepted=(value,))
        self.assertEqual(digest(HISTORY_REAL),HISTORY_REAL_SHA)


if __name__=="__main__":
    unittest.main()
