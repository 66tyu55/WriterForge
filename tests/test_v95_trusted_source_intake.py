"""V95 source trust: real V85/V86/V89 software on synthetic private fixtures.

The only reviewer signature in this TEST is an explicit public synthetic
HMAC. Passing a test never establishes genuine literary truth or a real
human independent judge; it verifies the refusal/approval protocol.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from test_v86_evidence_review_feedback_loop import (
    V86LiteraryLoopTests,ORIGINAL,QUOTE,h,
)
from writerforge.v95_trusted_source_intake import (
    intake_verified_experimental_candidate,V95SourceAdmissionError,
)


def quote_only():
    return {
        "status":"HYPOTHESIS","claim_id":"claim01",
        "question":"少年为何可能因为守桥人熄灯而改变渡河计划？",
        "observation":{"unit":1,"quote":QUOTE},
        "consequence":{"unit":2,"quote":"少年收起渡河的木牌"},
        "character_knowledge":{
            "actor":"少年",
            "known":"他知道守桥人出现异常，但无法了解当时的全部背景。",
            "unknown":"尚不知道守桥人熄灯的原因与今夜河面状况。"},
        "hypothesis":"守桥人熄灯可能改变了少年在当时的渡河风险判断。",
        "alternative":"钟声、夜色或自身疑虑也可能使少年选择等待。",
        "falsifier":"若后续证据证明熄灯与过河并无关系，应撤销此因果。",
        "uncertainty":"这只是两段局部原文推断，不是已经验证的文学真实因果。",
    }


class V95SealedSourceTests(unittest.TestCase):
    def setUp(self):
        fixture=V86LiteraryLoopTests(
            methodName="test_linked_review_approval_negative_revision_changes_behavior")
        fixture.setUp()
        self.fixture=fixture
        self.fixture.stage()

    def tearDown(self):
        self.fixture.tearDown()

    def call(self,answer=None,receipt=None,source=None,units=None,loop=None):
        fx=self.fixture
        return intake_verified_experimental_candidate(
            sealed=fx.sealed,
            review_loop=loop or fx.loop,
            v85_receipt=receipt or fx.receipt,
            project_id="project01",
            experience_id="lesson01",
            quote_only_model_answer=answer or quote_only(),
            visible_units=units if units is not None else ORIGINAL,
            pinned_visible_unit_sha256=[h(v) for v in ORIGINAL],
            original_source_sha256=source or fx.source_sha,
            frozen_fragment_sha256=h("".join(ORIGINAL)),
            sealed_future_unit_sha256=h("sealed future fixture"),
        )

    def test_signed_review_plus_same_session_exact_spans_admits_only_hypothesis(self):
        self.fixture.review()
        candidate=self.call()
        self.assertEqual(candidate["trust_type"],
                         "REVIEWED_HYPOTHESIS_NOT_CHARACTER_FACT")
        self.assertTrue(candidate["source_quote_positions_verified"])
        self.assertFalse(candidate["fact_journal_KNOWN_insert_allowed"])
        self.assertFalse(candidate["experimental_write_authorization_granted_here"])
        self.assertFalse(candidate["literary_skill_promotion_approved"])
        self.assertFalse(candidate["independent_literary_truth_proven"])
        self.assertEqual(candidate["model_calls"],0)
        self.assertEqual(candidate["r2_writes"],0)
        self.assertNotIn(QUOTE,str(candidate))
        self.assertNotIn("守桥人熄灯可能",str(candidate))

    def test_no_signed_review_fail_closed(self):
        with self.assertRaisesRegex(V95SourceAdmissionError,
                                    "MISSING_NEGATIVE_OR_UNRESOLVED"):
            self.call()

    def test_new_negative_after_positive_blocks_older_candidate(self):
        self.fixture.review()
        self.fixture.review(verdict="NEGATIVE",
                            reason="UNSUPPORTED_CAUSAL_CHAIN",
                            review_id="negative02")
        with self.assertRaisesRegex(V95SourceAdmissionError,
                                    "MISSING_NEGATIVE_OR_UNRESOLVED"):
            self.call()

    def test_original_model_quote_must_exist_literally_in_visible_unit(self):
        self.fixture.review()
        sample=quote_only()
        sample["observation"]["quote"]="守桥人突然打开了不曾存在的密室"
        with self.assertRaisesRegex(V95SourceAdmissionError,
                                    "HOST_LITERAL_SOURCE_ANCHOR_REJECTED"):
            self.call(answer=sample)

    def test_even_real_different_sentence_cannot_be_mixed_with_v85_claim(self):
        self.fixture.review()
        answer=quote_only()
        answer["observation"]["quote"]="少年看见守桥人悄悄熄灭了灯"
        with self.assertRaisesRegex(V95SourceAdmissionError,
                                    "EXACT_SOURCE_SPAN_MISMATCH"):
            self.call(answer=answer)

    def test_untrusted_other_book_and_changed_future_rejected(self):
        self.fixture.review()
        with self.assertRaisesRegex(V95SourceAdmissionError,
                                    "V85_AUDIT_NOT_SEALED"):
            self.call(source=h("another source"))
        with self.assertRaisesRegex(Exception,"VISIBLE_SOURCE_CHANGED"):
            self.call(units=(ORIGINAL[0]+"篡改",ORIGINAL[1]))

    def test_v85_receipt_hash_cannot_be_self_asserted_or_reused_after_change(self):
        self.fixture.review()
        bad=deepcopy(self.fixture.receipt)
        bad["audit"]["claims"][0]["actor_id"]="fabricated_hero"
        with self.assertRaisesRegex(Exception,"SESSION_NOT_VERIFIED"):
            self.call(receipt=bad)
        self.assertEqual(self.call()["review_state"],
                         "SUPPORTED_FOR_EXPERIMENT")

    def test_claim_id_must_match_signed_v86_link(self):
        self.fixture.review()
        q=quote_only()
        q["claim_id"]="other_claim_id"
        with self.assertRaisesRegex(V95SourceAdmissionError,
                                    "MODEL_CLAIM_ID_NOT_V85"):
            self.call(answer=q)

    def test_review_signature_validator_does_not_accept_manipulated_sql(self):
        self.fixture.review()
        self.fixture.db.conn.execute(
            "UPDATE experience_literary_reviews SET signature=? "
            "WHERE review_id='semantic01'",("0"*64,))
        self.fixture.db.conn.commit()
        with self.assertRaises(Exception):
            self.call()

    def test_duplicate_or_future_quote_is_not_accepted(self):
        self.fixture.review()
        q=quote_only()
        q["observation"]["unit"]=3
        with self.assertRaisesRegex(V95SourceAdmissionError,
                                    "HOST_LITERAL_SOURCE_ANCHOR_REJECTED"):
            self.call(answer=q)
        q=quote_only()
        q["consequence"]=deepcopy(q["observation"])
        with self.assertRaisesRegex(V95SourceAdmissionError,
                                    "HOST_LITERAL_SOURCE_ANCHOR_REJECTED"):
            self.call(answer=q)

if __name__=="__main__":
    unittest.main()
