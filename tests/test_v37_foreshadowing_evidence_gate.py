"""V37 future learned-L2 application must have verifiable textual proof."""
import unittest
from writerforge.v37_foreshadowing_evidence_gate import (
    validate_transfer_claim,ForeshadowingEvidenceError,
)

EARLY="她在摊角看见一条染红的细绳，却没有想清楚它为何系在药包上。"
LATE="她再看药包，才发现系绳的颜色与老人此前描述的一模一样。"
STORY="寒冷的清晨，药市人声喧闹，年轻药童想替病人寻找药草。"+EARLY+(
    "路上她几次犹豫，商人催促她赶快结账，她又怕让师父失望。"*15)+LATE
PLAN={"decisions":[{"angle":"foreshadowing","learned_lesson_id":"L2"}]}
LESSONS={"lessons":[{"id":"L2"}]}
REASON={
    "character_knowledge_at_setup":"药童看见了染红的细绳，但不掌握它与老人口述线索之间的真实联系。",
    "setup_to_payoff_connection":"前文细绳的颜色最终帮助她修正判断，产生一次可以向前文追溯的认知变化。",
    "uncertainty_or_abstention":"目前只是具体文本证据是否存在的核查，仍然需要独立审稿人判断文学效果。",
}
def claimed(**extra):
    return dict(lesson_id="L2",angle="foreshadowing",
                application_status="CLAIMED_APPLIED",
                setup_quote=EARLY,payoff_quote=LATE,**REASON,**extra)

class StrictL2EvidenceTests(unittest.TestCase):
    def test_exact_time_anchored_evidence_still_not_a_pass(self):
        data=validate_transfer_claim(response=claimed(),story=STORY,
                                     plan=PLAN,lessons=LESSONS)
        self.assertTrue(data["exact_characters_grounded_by_host"])
        self.assertTrue(data["actual_text_positions"]["setup_in_first_half"])
        self.assertTrue(data["actual_text_positions"]["payoff_after_two_thirds"])
        self.assertTrue(data["semantics_correct_not_proven"])
        self.assertFalse(data["automatic_skill_promotion_allowed"])
        self.assertNotIn(EARLY,str(data))
        self.assertNotIn(LATE,str(data))

    def test_forged_payoff_and_wrong_order_rejected(self):
        d=claimed();d["payoff_quote"]="一段完全不在原本作文中的伪造线索说明"
        with self.assertRaisesRegex(ForeshadowingEvidenceError,"FABRICATED_DRAFT"):
            validate_transfer_claim(response=d,story=STORY,plan=PLAN,lessons=LESSONS)
        d=claimed();d["setup_quote"]=LATE;d["payoff_quote"]=EARLY
        with self.assertRaisesRegex(ForeshadowingEvidenceError,"NOT_AFTER_SETUP"):
            validate_transfer_claim(response=d,story=STORY,plan=PLAN,lessons=LESSONS)

    def test_no_learned_lesson_link_no_promotion(self):
        d=claimed()
        with self.assertRaisesRegex(ForeshadowingEvidenceError,"NOT_BOUND_IN_PREWRITE"):
            validate_transfer_claim(response=d,story=STORY,
                  plan={"decisions":[{"angle":"goal","learned_lesson_id":"L2"}]},
                  lessons=LESSONS)

    def test_not_applied_must_state_uncertainty_not_fabricate_clue(self):
        d=claimed()
        d.update(application_status="NOT_APPLIED",setup_quote=None,payoff_quote=None)
        data=validate_transfer_claim(response=d,story=STORY,plan=PLAN,lessons=LESSONS)
        self.assertFalse(data["exact_characters_grounded_by_host"])
        self.assertIsNone(data["actual_text_positions"])
        d["setup_quote"]=EARLY
        with self.assertRaisesRegex(ForeshadowingEvidenceError,"ABSTENTION_MUST_NOT"):
            validate_transfer_claim(response=d,story=STORY,plan=PLAN,lessons=LESSONS)

    def test_duplicate_anchor_cannot_prove_single_precise_event(self):
        duplicated=STORY+EARLY
        with self.assertRaisesRegex(ForeshadowingEvidenceError,"AMBIGUOUS_DUPLICATED"):
            validate_transfer_claim(response=claimed(),story=duplicated,
                                    plan=PLAN,lessons=LESSONS)

if __name__=="__main__":
    unittest.main()
