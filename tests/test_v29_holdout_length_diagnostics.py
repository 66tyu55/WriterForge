"""Length mismatch diagnostics capture only numeric data, never full text."""
import unittest
from hashlib import sha256
from test_v29_old_new_holdout import SOURCE,Planner,Critic
from writerforge.v29_old_new_trial import compare_old_vs_semantic,LengthUnscorable
from writerforge.v29_fresh_holdout import task

class UnequalWriter:
    provider="synthetic"
    name="synthetic-writer"
    def __init__(self):self.calls=[]
    def ask(self,system,user,*,num_predict):
        self.calls.append((system,user,num_predict))
        n=len(self.calls)
        unit="迷失的少年在冬夜的树林里听见铃声，他想回家却不得不停下确认方向。"
        return {"scene":unit*([18,40,17,39][n-1])}

class LengthDiagnosticsTests(unittest.TestCase):
    def test_failure_is_numeric_only_never_contains_source_or_drafts(self):
        w=UnequalWriter()
        c=Critic()
        with self.assertRaises(LengthUnscorable) as caught:
            compare_old_vs_semantic(
                planner=Planner(),writer=w,critic=c,
                first=SOURCE,second="合成后文"*80,source_sha="a"*64,
                source_window_sha=sha256(SOURCE.encode()).hexdigest(),
                writing_task=task(0))
        nums=caught.exception.safe_lengths
        self.assertEqual(len(w.calls),4)
        self.assertEqual(len(c.calls),0)
        self.assertGreater(nums["relative_final_difference"],.15)
        self.assertTrue(nums["no_literary_score"])
        self.assertEqual(set(nums["after_symmetric_revision"]),{"legacy","semantic"})
        self.assertNotIn("少年",str(nums))
        self.assertNotIn("铃声",str(nums))
    def test_legacy_positive_control_remains_separately_scored(self):
        self.assertTrue(issubclass(LengthUnscorable,Exception))

if __name__=="__main__":
    unittest.main()
