"""Zero-provider preflight for B++ original t05, not literary grading."""
import unittest
from experiments import wf_0av_bplusplus_t05_only_immutable_resume_once_20261026 as e


class LastOriginalProseBudgetProtocol(unittest.TestCase):
    def test_only_one_new_call_after_three_immutable_paid_wires(self):
        self.assertEqual(e.PRIOR_PAID_CALLS,25)
        self.assertEqual(e.PRIOR_RESERVED_COMPLETION,30850)
        self.assertEqual(e.MAX_NEW_PAID,1)
        self.assertEqual(e.MAX_NEW_RESERVED,1450)
        cap=e.LastOne()
        cap.reserve(1450)
        self.assertEqual(cap.calls,1)
        self.assertEqual(cap.reserved,1450)
        with self.assertRaisesRegex(RuntimeError,"WF0AV_BPLUSPLUS_FINAL_ONE"):
            cap.reserve(1450)

    def test_budget_rejects_an_extra_planning_call_before_network(self):
        cap=e.LastOne()
        for amount in (650,1600,5000):
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(RuntimeError,"WF0AV_BPLUSPLUS_FINAL_ONE"):
                    cap.reserve(amount)
        self.assertEqual(cap.calls,0)

    def test_preflight_exhausted_before_live_model(self):
        cap=e.LastOne(exhausted=True)
        with self.assertRaisesRegex(RuntimeError,"WF0AV_BPLUSPLUS_FINAL_ONE"):
            cap.reserve(1450)

    def test_prior_paid_originals_are_three_distinct_known_exact_sources(self):
        self.assertEqual(list(e.ORIGINAL_WIRES),[8,9,10])
        self.assertEqual([v[2] for v in e.ORIGINAL_WIRES.values()],[650,1450,650])
        self.assertEqual(len({v[0] for v in e.ORIGINAL_WIRES.values()}),3)
        self.assertEqual(len({v[1] for v in e.ORIGINAL_WIRES.values()}),3)
        self.assertTrue(all(len(v[0])==len(v[1])==64
                            for v in e.ORIGINAL_WIRES.values()))
        self.assertTrue(e.REGISTRATION["no_new_t05_planning_allowed"])
        self.assertTrue(e.REGISTRATION["frozen_actual_first_four_turn_prose"])
        self.assertFalse(e.REGISTRATION["R2_or_Canon_or_Railway_or_main_writes"])


if __name__=="__main__":
    unittest.main()
