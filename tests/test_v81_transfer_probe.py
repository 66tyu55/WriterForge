"""V81 synthetic blind different-book transfer probe; no model, source, or R2.

Ensures the same two contiguous unseen source units and deterministic arm
order; a change between baseline and experience-conditioned model answers
must NEVER be scored as independently verified literary mastery.
"""
from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path
from hashlib import sha256
import unittest

from writerforge.v81_transfer_probe import (
    prepare_heldout,validate_model_proposal,
    compare_arms,WFTransferExamError,
)

class TransferComparabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.source=Path(self.temp.name)/"holdout.txt"
        novel=("第一章 远行\n"+
               "江边的人听见钟声却没有看见敲钟的人，一阵风吹过石桥。\n"*80+
               "第二章 小路\n"+
               "另一位旅人走进树林，他仍不明白夜里传来的声音。\n"*70)
        self.source.write_bytes(novel.encode("utf-8"))
        self.source_sha=sha256(self.source.read_bytes()).hexdigest()
        self.key_sha="a"*64
        self.exp_sha="b"*64
    def tearDown(self):
        self.temp.cleanup()
    def make(self):
        return prepare_heldout(
            self.source,original_sha=self.source_sha,
            source_key_sha=self.key_sha,
            encoding="utf-8",trained_experience_sha=self.exp_sha)

    def test_precommitted_holdout_is_exactly_same_for_both_arms(self):
        units,proof=self.make()
        second,again=self.make()
        self.assertEqual(units,second)
        self.assertEqual(proof,again)
        self.assertEqual(len(units),2)
        self.assertEqual(set(proof["arm_order"]),{"baseline","experience"})
        self.assertEqual(len(proof["source_first_two_unit_sha256"]),2)
        self.assertFalse(proof["independent_literary_quality_verified"])
        self.assertTrue(proof["unseen_other_work"])
        self.assertNotIn("江边的人",str(proof))

    def test_requires_frozen_sha_not_reinterpreted_text(self):
        with self.assertRaisesRegex(WFTransferExamError,
                                    "CONTENT_CHANGED"):
            prepare_heldout(
                self.source,original_sha="0"*64,
                source_key_sha=self.key_sha,
                encoding="utf-8",trained_experience_sha=self.exp_sha)

    def test_structured_question_grounding_and_self_limits_only(self):
        units,_=self.make()
        proposal={
            "question":"为什么河边钟声始终无法解释来人的身份？",
            "hypothesis":"读者可能先注意声音，再等待事件的直接说明。",
            "uncertainty":"仅有开头两段，不能断定后面发生的真实情节。",
            "focus":"注意信息出现的先后顺序及人物视角。",
            "evidence_units":[1,2],
        }
        reviewed=validate_model_proposal(
            proposal,source_units=units)
        self.assertTrue(reviewed["mechanical_evidence_indices_valid"])
        self.assertTrue(reviewed["difference_does_not_prove_transfer"])
        self.assertEqual(reviewed["source_units_referenced"],[1,2])

    def test_unread_source_number_is_rejected(self):
        units,_=self.make()
        bad={
            "question":"发生了什么事情是还没有确定的？",
            "hypothesis":"先提到声音再说到人物身份。",
            "uncertainty":"目前无法知道之后章节。",
            "focus":"检查同一来源证据是否连贯。",
            "evidence_units":[3],
        }
        with self.assertRaisesRegex(WFTransferExamError,
                                    "EVIDENCE_UNIT_NOT_GROUNDED"):
            validate_model_proposal(bad,source_units=units)

    def test_long_private_original_copy_refused(self):
        units,_=self.make()
        result={
          "question":"我为什么会感到困惑，接下来是什么？",
          "hypothesis":units[0][:100],
          "uncertainty":"前两段不能证明真正的后续情节。",
          "focus":"是否存在叙事信息的刻意遗漏。",
          "evidence_units":[1],
        }
        with self.assertRaisesRegex(WFTransferExamError,
                                    "UNAUTHORIZED_LONG_SOURCE_COPY"):
            validate_model_proposal(result,source_units=units)

    def test_response_change_is_not_an_independent_literary_grade(self):
        a={
          "question":"什么时间传来那阵钟声？",
          "hypothesis":"声音可能先于人物事件。",
          "uncertainty":"尚无法说明钟声的具体来源。",
          "focus":"声音与人物行动的先后。",
          "evidence_units":[1],
        }
        b={**a,"focus":"观察读者期待是否随声响改变。"}
        same=compare_arms(a,a)
        diff=compare_arms(a,b)
        self.assertFalse(same["answer_sha_differs"])
        self.assertTrue(diff["answer_sha_differs"])
        self.assertTrue(diff["learned_skill_improvement_unproven"])
        self.assertTrue(diff["prompt_conditioning_alone_can_explain_difference"])

if __name__=="__main__":
    unittest.main()
