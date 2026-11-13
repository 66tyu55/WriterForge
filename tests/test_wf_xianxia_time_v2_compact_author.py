"""Frozen 2-arm compact time-author interface, no model/provider call."""
import unittest
from experiments.wf_xianxia_time_v2_compact_author_once import (
    preflight,request,frozen,ARMS
)

class CompactTimeAuthorTests(unittest.TestCase):
    def test_only_two_real_attempts_and_one_parameter(self):
        data=frozen()
        doc=preflight()
        self.assertEqual(doc["calls_planned"],2)
        self.assertTrue(doc["changed_only_time_rate"])
        self.assertEqual(ARMS,("rate1","rate3"))
        self.assertEqual(doc["prompts"][0]["time_window"]["world_hour_now"],1006)
        self.assertEqual(doc["prompts"][1]["time_window"]["world_hour_now"],1006)
        self.assertFalse(doc["prompts"][0]["time_window"]["could_succeed_if_attempted_now"])
        self.assertTrue(doc["prompts"][1]["time_window"]["could_succeed_if_attempted_now"])
    def test_writer_receives_time_not_raw_parameter_json(self):
        data=frozen()
        for arm in ARMS:
            prompt=request(data,arm)
            self.assertIn("截止事件时限是第1008小时",prompt)
            self.assertIn("灵田佃户",prompt)
            self.assertNotIn('"time_frames"',prompt)
            self.assertNotIn('"advancement"',prompt)
            self.assertNotIn('"world_clock"',prompt)
            self.assertIn("不预设突破成功",prompt)
    def test_only_allowed_difference_is_eligibility_effect(self):
        data=frozen()
        p,q=request(data,"rate1"),request(data,"rate3")
        self.assertIn("未满足成功突破",p)
        self.assertIn("已满足突破尝试",q)
        self.assertIn("已有实修12",p)
        self.assertIn("已有实修24",q)
if __name__=="__main__":unittest.main()
