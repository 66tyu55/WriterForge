"""V100 offline tests only: no provider/R2 access and no literary score claims."""
import unittest

from writerforge.v100_blind_fair_protocol import (
    HISTORICAL_ACTUAL, HISTORICAL_TARGET, BLIND_IDS, MODES,
    OUTPUT_RESERVATION, NEW_TARGET, MAX_CALLS,
    MAX_OUTPUT_RESERVED, MAX_CONSERVATIVE_INPUT_OUTPUT,
    xianxia_precommit, historical_blind_packets, xianxia_fairness,
)
from writerforge.v99_longform_quality_evidence import (
    freeze_manuscript, V99EvidenceError,
)


class V100BlindFairTest(unittest.TestCase):
    def test_history_uses_genuine_1500_not_fictional_1600_target(self):
        f=freeze_manuscript(prose="旧桥下的水还在上涨。"*160,
            arm="single",case_id="v97_historical_ferry",requested_chars=1500)
        self.assertEqual(f["requested_characters_including_punctuation"],
                         HISTORICAL_TARGET)
        self.assertEqual(f["actual_characters_including_punctuation"],
                         len("旧桥下的水还在上涨。"*160))

    def test_v97_candidate_lengths_force_uncomparable(self):
        bodies={a:str(i)*size for i,(a,size) in
                enumerate(HISTORICAL_ACTUAL.items(),1)}
        order=("causal_guard","single","split_only")
        packets,mapping,fairness=historical_blind_packets(bodies,order)
        self.assertEqual([x["blind_id"] for x in packets],list(BLIND_IDS))
        self.assertEqual([x["arm"] for x in mapping],list(order))
        self.assertEqual(len(packets),3)
        self.assertFalse(fairness["lengths_comparable"])
        self.assertEqual(fairness["literary_winner"],"UNDETERMINED")
        self.assertEqual(round(fairness["relative_length_gap"],3),0.183)
        self.assertTrue(all("arm" not in x for x in packets))
        self.assertTrue(all("raw_model_answer" not in x for x in packets))
        self.assertTrue(all(x["independent_review_status"]=="UNREVIEWED"
                            for x in packets))

    def test_no_forged_cold_restore_bodies_or_repeated_arm(self):
        bodies={a:str(i)*size for i,(a,size) in
                enumerate(HISTORICAL_ACTUAL.items(),1)}
        bodies["causal_guard"]="不存在的正文"
        with self.assertRaisesRegex(ValueError,"ACTUAL_PROSE"):
            historical_blind_packets(bodies,tuple(HISTORICAL_ACTUAL))
        bodies["causal_guard"]="丙"*1554
        with self.assertRaisesRegex(ValueError,"PERMUTATION"):
            historical_blind_packets(
                bodies,("single","single","causal_guard"))

    def test_xianxia_precommit_budget_and_no_paid_trigger(self):
        doc=xianxia_precommit()
        self.assertEqual(doc["max_calls"],MAX_CALLS)
        self.assertEqual(doc["max_reserved_completion_tokens"],
                         MAX_OUTPUT_RESERVED)
        self.assertLessEqual(MAX_CONSERVATIVE_INPUT_OUTPUT,150000)
        self.assertEqual({sum(v) for v in OUTPUT_RESERVATION.values()},
                         {4800})
        self.assertEqual(sum(len(v) for v in OUTPUT_RESERVATION.values()),
                         12)
        self.assertEqual(doc["blind_independent_human_review"],
                         "NOT_PERFORMED")
        self.assertEqual(doc["literary_outcome"],"UNDETERMINED")
        self.assertTrue(doc["no_auto_retry_on_timeout_or_schema_failure"])

    def card(self,arm,size):
        return freeze_manuscript(prose="仙"*size,arm=arm,
                  case_id="v100_xianxia_critical_watergate",
                  requested_chars=NEW_TARGET)

    def test_four_arms_length_and_target_gate(self):
        cards=[self.card(arm,1600) for arm in MODES]
        card=xianxia_fairness(cards)
        self.assertTrue(card["eligible_for_equal_length_blind_comparison"])
        self.assertFalse(card["narrative_or_literary_advantage_verified"])
        cards[-1]=self.card("rolling_causal",1390)
        card=xianxia_fairness(cards)
        self.assertFalse(card["eligible_for_equal_length_blind_comparison"])
        self.assertEqual(card["literary_winner"],"UNDETERMINED")

    def test_wrong_arm_set_rejected(self):
        with self.assertRaisesRegex(ValueError,"FOUR_ARMS_REQUIRED"):
            xianxia_fairness([self.card(a,1600) for a in MODES[:3]])


if __name__=="__main__":
    unittest.main()
