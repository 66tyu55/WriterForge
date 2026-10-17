"""V38 end-to-end learning-transfer *data-flow* regression, no model calls.

These examples are SYNTHETIC and do not constitute evidence that WF has
learned to write effective foreshadowing from Xi You Ji.
"""
import unittest
from copy import deepcopy

from writerforge.v35_observable_trace import validate_after,TraceContractError
from writerforge.v38_lesson_transfer_bridge import LearnedTransferGateError

START="她在药市角落看见一段奇特的绯红细绳，暗自疑惑却没有立即细查。"
FINISH="后来她重新拆开药包，才发现绯红细绳与失踪药匣上的结扣一致。"
FILL="老街上的药草气味随着热气散开，她听见师父叮嘱的话，仍然犹豫。"
STORY=START+FILL*15+FINISH
PLANS={"decisions":[
    {"angle":"goal","learned_lesson_id":"NONE"},
    {"angle":"knowledge","learned_lesson_id":"NONE"},
    {"angle":"causality","learned_lesson_id":"NONE"},
    {"angle":"foreshadowing","learned_lesson_id":"L2"},
]}
LESSONS={"lessons":[{"id":"L2","technique":"在角色可观察的细节与后文行动后果间建立联系。"}]}
RATIONALES={
 "character_knowledge_at_setup":
     "药童最初看见绯红细绳，只知细绳形状，尚不知药匣结扣来源。",
 "setup_to_payoff_connection":
     "故事后段再次提及结扣可以回查前文细绳，仍需独立读者判断是否形成真正伏笔。",
 "uncertainty_or_abstention":
     "目前只能保证文字证据存在与时间先后，无法保证这种安排有实际文学效果。",
}
CHECK={
 "checks":[
     {"angle":"goal","actual_draft_quote":START[:25],
      "followed_prewrite_plan":True,
      "observed_gap":"人物目标有表现，但时间压力与目标的联系仍有弱点。",
      "possible_next_revision":"未来应核对决定是否真正让人物付出可见的行动代价。"},
     {"angle":"foreshadowing","actual_draft_quote":FINISH[:26],
      "followed_prewrite_plan":True,
      "observed_gap":"读者可以找到前文的细绳，但该细节是否造成认知转折尚不确定。",
      "possible_next_revision":"需要判断前置线索是否改变读者推断，而不只是同词再次出现。"},
 ],
 "biggest_mistake":"结尾虽然引用了绯红细绳，仍需检查这是否真正与前文人物抉择产生因果关系。",
}
def claim(**updates):
    x=dict(
        lesson_id="L2",angle="foreshadowing",
        application_status="CLAIMED_APPLIED",
        setup_quote=START,payoff_quote=FINISH,**RATIONALES)
    x.update(updates)
    return x

class StrictTransferBridgeTests(unittest.TestCase):
    def do(self,*,response=None,claims=None,plan=None,lessons=None):
        return validate_after(
            deepcopy(response if response is not None else CHECK),
            STORY,deepcopy(plan if plan is not None else PLANS),
            learned_lessons=deepcopy(lessons if lessons is not None else LESSONS),
            lesson_transfer_claims=deepcopy(claims if claims is not None else [claim()]))

    def test_actual_existing_postwrite_api_requires_real_source_lesson_proof(self):
        result=self.do()
        transfer=result["learned_transfer_evidence"]
        self.assertEqual(transfer["source_linked_angle_names"],["foreshadowing"])
        self.assertTrue(transfer["postwrite_coverage_complete"])
        self.assertEqual(transfer["claimed_applied_count"],1)
        self.assertEqual(transfer["evidence_claims"][0]["application_claim"],"CLAIMED_APPLIED")
        self.assertFalse(transfer["mechanism_semantically_verified"])
        self.assertFalse(transfer["formal_core_promoted"])
        self.assertNotIn(START,str(transfer))
        self.assertNotIn(FINISH,str(transfer))

    def test_historical_four_non_lesson_angles_cannot_pass_by_missing_foreshadowing(self):
        incomplete=deepcopy(CHECK)
        incomplete["checks"]=[x for x in incomplete["checks"]
                              if x["angle"]!="foreshadowing"]
        incomplete["checks"].append({
            "angle":"knowledge","actual_draft_quote":FILL[:25],
            "followed_prewrite_plan":False,
            "observed_gap":"在人物知识限制上没有体现原先设计的必要认知边界。",
            "possible_next_revision":"需要进一步明确人物在这段情节里能够观察到的真实事实。",
        })
        with self.assertRaisesRegex(
                LearnedTransferGateError,"LEARNED_LESSON_PREWRITE_NOT_REVIEWED"):
            self.do(response=incomplete)
        # Legacy non-opt-in self review stays compatible, but does NOT
        # suddenly receive or claim a verified learned transfer record.
        old=validate_after(incomplete,STORY,PLANS)
        self.assertNotIn("learned_transfer_evidence",old)

    def test_no_lessons_or_claims_not_fabricated(self):
        with self.assertRaisesRegex(TraceContractError,
                                   "LEARNED_TRANSFER_INPUTS_INCOMPLETE"):
            validate_after(CHECK,STORY,PLANS,learned_lessons=LESSONS)
        with self.assertRaisesRegex(LearnedTransferGateError,
                                   "LEARNED_LESSON_APPLICATION_EVIDENCE_MISSING"):
            self.do(claims=[])

    def test_forged_literary_quote_and_reversed_payoff_fail(self):
        with self.assertRaisesRegex(LearnedTransferGateError,
                                   "FABRICATED_DRAFT_QUOTE"):
            self.do(claims=[claim(setup_quote="这是一句根本不存在的伪造小说引用。")])
        with self.assertRaisesRegex(LearnedTransferGateError,
                                   "PAYOFF_NOT_AFTER_SETUP"):
            self.do(claims=[claim(setup_quote=FINISH,payoff_quote=START)])

    def test_invalid_lesson_reference_and_duplicate_claims_rejected(self):
        with self.assertRaisesRegex(LearnedTransferGateError,
                                   "CLAIM_NOT_LINKED_OR_DUPLICATED"):
            self.do(claims=[claim(lesson_id="L1")])
        with self.assertRaisesRegex(LearnedTransferGateError,
                                   "APPLICATION_EVIDENCE_MISSING"):
            self.do(claims=[claim(),claim()])

    def test_honest_not_applied_status_is_observed_without_false_success(self):
        result=self.do(claims=[claim(application_status="NOT_APPLIED",
                                     setup_quote=None,payoff_quote=None)])
        transfer=result["learned_transfer_evidence"]
        self.assertEqual(transfer["claimed_applied_count"],0)
        self.assertEqual(transfer["admitted_not_applied_count"],1)
        self.assertEqual(transfer["evidence_status"],
                         "LEARNER_ADMITS_INCOMPLETE_OR_UNCERTAIN_APPLICATION")
        self.assertFalse(transfer["independent_literary_improvement_proven"])

if __name__=="__main__":
    unittest.main()
