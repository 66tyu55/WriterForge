"""No-network regressions for requested baseline-30 display and new task isolation."""
import unittest

from writerforge.reverse_score_scale import baseline_30_display,ScaleError
from writerforge.reverse_cloud_ab import CloudABTrial,BASE_TASK
from scripts.run_wudong_transfer_baseline30_v5 import TRANSFER_TASK


def arm(scores):
    names=("perception","causality","information","continuity","language")
    return {"dimension_review":{
        name:{"score":value,"reason":"synthetic"}
        for name,value in zip(names,scores)
    }}


class TestBaselineThirty(unittest.TestCase):
    def test_true_raw_score_retained_in_display_transform(self):
        raw={"baseline":arm([88,82,85,90,86]),"skill":arm([92,89,87,91,90])}
        result=baseline_30_display(raw)
        self.assertEqual(result["unadjusted_model_mean"]["baseline"],86.2)
        self.assertEqual(result["unadjusted_model_mean"]["skill"],89.8)
        self.assertEqual(result["baseline_display_score"],30)
        self.assertEqual(result["skill_display_score_unclipped"],33.6)
        self.assertEqual(result["unadjusted_signed_delta"],3.6)
        self.assertFalse(result["usable_for_mastery_or_human_evaluation"])
        self.assertFalse(result["second_window_unlocked"])
    def test_negative_delta_remains_negative(self):
        raw={"baseline":arm([88,82,85,90,86]),"skill":arm([73,73,73,73,73])}
        result=baseline_30_display(raw)
        self.assertLess(result["skill_display_score_unclipped"],30)
    def test_forged_raw_scores_fail_closed(self):
        raw={"baseline":arm([88,82,85,90,86]),"skill":arm([92,89,87,91,90])}
        raw["skill"]["dimension_review"]["language"]["score"]=False
        with self.assertRaises(ScaleError):baseline_30_display(raw)
    def test_new_transfer_prompt_differs_without_original_names(self):
        self.assertNotEqual(TRANSFER_TASK,BASE_TASK)
        self.assertGreaterEqual(len(TRANSFER_TASK),40)
        self.assertLessEqual(len(TRANSFER_TASK),800)
        for name in ["林动","林啸","柳妍","武动乾坤"]:
            self.assertNotIn(name,TRANSFER_TASK)
        self.assertIn("索道",TRANSFER_TASK)


if __name__=="__main__":
    unittest.main()
