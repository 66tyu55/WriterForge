"""No-network evidence-only V99 literary error review contract."""
import unittest
from writerforge.v99_longform_quality_evidence import (
 freeze_manuscript,evidence_annotation,audit_unverified_claims,
 compare_equal_length,V99EvidenceError,
)
TEXT=("少年在桥边发现通行牌已被收走，决定先照顾同行的妹妹。"
      "他将药匣藏在破布下面，告诉守夜人今晚不会强行过桥。"
      "几刻钟后，他却声称自己从未见过那块通行牌，也没有带任何药匣。"
      "妹妹一直没有出声，她还不知道桥下有人提前拆走了木桩。"
      "守夜人重新抬起灯笼，只说天亮之前仍需等待。"\n      "桥面上雨水逐渐退去，但他们仍然没有确认是谁修改了通行规则。")
A="少年在桥边发现通行牌已被收走"
B="他却声称自己从未见过那块通行牌"

class V99Tests(unittest.TestCase):
 def f(self,prose=TEXT,arm="single",requested_chars=800):
  return freeze_manuscript(prose=prose,arm=arm,
                          case_id="fixture_historical_bridge",requested_chars=requested_chars)
 def test_explicit_witnesses_are_not_semantic_verdict(self):
  f=self.f()
  a=evidence_annotation(prose=TEXT,frozen=f,category="character_knowledge",
                        established_quote=A,contradicting_quote=B)
  self.assertLess(a["earlier_witness"]["start"],a["later_witness"]["start"])
  self.assertFalse(a["semantic_conflict_proven"])
  x=audit_unverified_claims(frozen=f,annotations=[a])
  self.assertIsNone(x["verified_hard_contradictions"])
  self.assertIsNone(x["first_verified_logic_failure_character"])
  self.assertEqual(x["literary_quality_winner"],"UNDETERMINED")
  self.assertNotIn(A,str(x))
 def test_no_false_quote_or_unread_history(self):
  f=self.f()
  with self.assertRaisesRegex(V99EvidenceError,"NOT_IN_ACTUAL_PROSE"):
   evidence_annotation(prose=TEXT,frozen=f,category="causality",
    established_quote="前文已经揭示守夜人的真实目的",contradicting_quote=B)
 def test_identical_or_wrong_order_not_two_proofs(self):
  f=self.f()
  with self.assertRaisesRegex(V99EvidenceError,"NOT_ORDERED"):
   evidence_annotation(prose=TEXT,frozen=f,category="causality",
    established_quote=B,contradicting_quote=A)
 def test_changed_prose_rejected(self):
  f=self.f()
  with self.assertRaisesRegex(V99EvidenceError,"FROZEN_MANUSCRIPT_CHANGED"):
   evidence_annotation(prose=TEXT+"写了新结局",frozen=f,
    category="causality",established_quote=A,contradicting_quote=B)
 def test_no_self_reported_literary_grade(self):
  f=self.f()
  a=evidence_annotation(prose=TEXT,frozen=f,category="causality",
                         established_quote=A,contradicting_quote=B)
  a["semantic_conflict_proven"]=True
  with self.assertRaisesRegex(V99EvidenceError,"UNTRUSTED_ASSERTED_GRADE"):
   audit_unverified_claims(frozen=f,annotations=[a])
 def test_character_length_gap_not_automatically_fair(self):
  a=self.f(arm="single")
  b=self.f(prose=TEXT+"后续却没有提供新的实质事件。"*25,arm="causal_guard")
  result=compare_equal_length(samples=(a,b))
  self.assertFalse(result["lengths_comparable"])
  self.assertEqual(result["literary_winner"],"UNDETERMINED")
 def test_same_length_two_arms_are_preflight_only(self):
  a=self.f(arm="single");b=self.f(arm="rolling_causal")
  result=compare_equal_length(samples=(a,b))
  self.assertTrue(result["lengths_comparable"])
  self.assertFalse(result["independent_semantic_review_completed"])
 def test_unicode_replacement_block(self):
  with self.assertRaisesRegex(V99EvidenceError,"MANUSCRIPT_INPUT"):
   self.f(TEXT+"\ufffd")
if __name__=="__main__": unittest.main()
