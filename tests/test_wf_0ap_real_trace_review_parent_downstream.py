"""0.AP RED: a real 0.AO prose source is retained as TRACE_REJECTED review-only.

Original DeepSeek Flash writer run 40259961845, artifact 12624461773:
T03 parent quote was not the signed T02 effect, so G rightly retained T03
as an unverified literary DRAFT rather than writing a false causal fact.
T04 later authored ordinary source text but the prior review-only receipt
raised WF96_NONCAUSAL_PARENT_SOURCE_INVALID and stopped the whole job.

This test uses SYNTHETIC shortened prose to exercise the identical failure
class. Separate artifact replay checks real original wires and hashes. No
new author, semantic judge, R2, Canon, or model calls.
"""
from __future__ import annotations

from hashlib import sha256
import json
import unittest

from writerforge.v96_causal_turns import (
    V96CausalDraftError,check_turn,review_only_model_turn,
    trace_failure_reviewable,assemble_prose,
)
from writerforge.v119_revision_transaction import (
    prepare_source_repair_contract,RevisionTransactionError,
)


def beat(id,kind,parent=None):
    return {"id":id,"kind":kind,"actor":"秦渊",
            "goal":"依据前文真正看见的情况做下一小步选择，不将未知当已知",
            "causal_parent":parent,"craft_focus":[]}


def response(prose,action=None,effect=None,parent=None):
    return json.dumps({"prose":prose,"trace":{
        "action_quote":action,"effect_quote":effect,
        "parent_effect_quote":parent,
    }},ensure_ascii=False,separators=(",",":"))


def digest(prose):
    return sha256(prose.encode("utf8")).hexdigest()


PARENT=(
    "夜已深，秦渊不知门外那骑从哪里来，也不知道主帅收到密信没有。"
    "秦渊把这句原话记在纸边，写下来源未明，不作确报。"
    "他查验驿道换马的时辰，觉得还要把北路的缺报单列。"
    "灯影落在封套上，他并未说自己知道马匹后来去了哪里。"
)
ACTION="秦渊把这句原话记在纸边，写下来源未明，不作确报"
CHILD=(
    "案头余烬快熄了，秦渊把北面的空缺重新写进附呈里。"
    "他又取过三封斥候回报，把不同时辰的印记一一对齐。"
    "门外有人轻叩木门，却没说究竟是哪一路的信使。"
    "秦渊把薄纸折成两页，不敢提前宣称远处已有新命令。"
    "他不催人快马，也不凭一句模糊的传闻出兵。"
)
CHILD_ACTION="秦渊把薄纸折成两页，不敢提前宣称远处已有新命令"
CHILD_EFFECT="他不催人快马，也不凭一句模糊的传闻出兵"


def old_signed_review():
    # Exactly what G's existing optional model-trace recovery signs:
    # a real prose body, not a certified event or a semantic truth claim.
    return review_only_model_turn(
        response(PARENT,ACTION,"这段不存在的效果"),
        beat("t03","decision"),
        failure_code="WF96_PARENT_CAUSE_NOT_ANCHORED_IN_PREVIOUS_PROSE",
        max_prose_chars=1024,
    )


class ReviewOnlyParentDownstreamDebt(unittest.TestCase):
    def test_source_verified_but_trace_rejected_parent_is_not_a_causal_fact(self):
        old=old_signed_review()
        self.assertEqual(old["receipt"]["causal_check"],
                         "TRACE_REJECTED_SOURCE_PROSE_REVIEW_ONLY")
        self.assertIsNone(old["effect_quote"])
        self.assertTrue(old["receipt"]["source_causal_review_required"])
        self.assertFalse(old["receipt"]["eligible_for_factjournal_KNOWN"])
        self.assertFalse(old["receipt"]["causal_relation_verified"])
        raw=response(CHILD,CHILD_ACTION,CHILD_EFFECT,ACTION)
        with self.assertRaisesRegex(
            V96CausalDraftError,
            "WF96_PARENT_REVIEW_ONLY_TRACE_REQUIRES_REVIEW",
        ):
            check_turn(raw,beat("t04","action",parent="t03"),
                       accepted=(old,),mode="causal_guard")
        self.assertTrue(trace_failure_reviewable(
            "WF96_PARENT_REVIEW_ONLY_TRACE_REQUIRES_REVIEW"))
        child=review_only_model_turn(
            raw,beat("t04","action",parent="t03"),
            failure_code="WF96_PARENT_REVIEW_ONLY_TRACE_REQUIRES_REVIEW",
            accepted=(old,),max_prose_chars=1024,
        )
        self.assertEqual(child["prose"],CHILD)
        self.assertIsNone(child["effect_quote"])
        self.assertEqual(child["receipt"]["parent_review_only_source_sha256"],
                         digest(PARENT))
        self.assertTrue(child["receipt"]["parent_review_only_unresolved"])
        self.assertFalse(child["receipt"]["eligible_for_factjournal_KNOWN"])
        self.assertFalse(child["receipt"]["eligible_for_experience_promotion"])
        self.assertEqual(assemble_prose((old,child)),PARENT+"\n\n"+CHILD)

    def test_no_spoofed_parent_receipt_or_modified_prose_can_be_accepted(self):
        old=old_signed_review()
        raw=response(CHILD,CHILD_ACTION,CHILD_EFFECT,ACTION)
        for forged in (
            {**old,"prose":old["prose"]+"凭空加一段后文"},
            {**old,"receipt":{**old["receipt"],"receipt_sha256":"0"*64}},
            {**old,"receipt":{**old["receipt"],"eligible_for_factjournal_KNOWN":True}},
        ):
            with self.subTest(kind=str(forged.keys())):
                with self.assertRaises(V96CausalDraftError):
                    check_turn(raw,beat("t04","action",parent="t03"),
                               accepted=(forged,),mode="causal_guard")
                with self.assertRaises(V96CausalDraftError):
                    review_only_model_turn(
                        raw,beat("t04","action",parent="t03"),
                        failure_code="WF96_PARENT_REVIEW_ONLY_TRACE_REQUIRES_REVIEW",
                        accepted=(forged,),max_prose_chars=1024)

    def test_source_repair_guide_preserves_unresolved_parent_not_fake_effect(self):
        old=old_signed_review()
        guide=prepare_source_repair_contract(
            source=CHILD,source_sha256=digest(CHILD),
            beat=beat("t04","action",parent="t03"),
            accepted=(old,),original_trace={
                "action_quote":CHILD_ACTION,"effect_quote":CHILD_EFFECT,
                "parent_effect_quote":ACTION})
        self.assertTrue(guide["previous_parent_trace_review_only"])
        self.assertEqual(guide["actual_previous_review_only_source_sha256"],
                         digest(PARENT))
        self.assertIsNone(guide["actual_previous_effect_quote"])
        self.assertTrue(guide["no_literary_grade_or_host_authored_text"])
        self.assertEqual(guide["canon_writes"],0)


if __name__=="__main__":
    unittest.main()
