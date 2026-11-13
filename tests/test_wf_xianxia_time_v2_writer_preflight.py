"""No-credit dry-run checks for real writer V2 trial before model download."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import unittest

from experiments.wf_xianxia_time_v2_real_writer_once import (
    ARMS,FROZEN,SEED,LIMIT,read_frozen,request_for,preflight
)

class TimeV2WriterPreflightTests(unittest.TestCase):
    def test_freeze_exact_character_and_three_arms(self):
        data=read_frozen()
        self.assertEqual(data["character"]["role"],"灵田佃户")
        self.assertEqual(data["character"]["temperament"],"谨慎却倔强")
        self.assertEqual(data["random_character_seed"],SEED)
        self.assertEqual(ARMS,("baseline","rate1","rate3"))
        self.assertEqual(LIMIT,1536)
        self.assertEqual(preflight()["planned_calls"],3)

    def test_exact_one_parameter_changed_and_no_baked_in_outcome(self):
        data=read_frozen()
        a,b=deepcopy(data["rate1"]),deepcopy(data["rate3"])
        a["time_frames"]["cave"]["numerator"]=b["time_frames"]["cave"]["numerator"]
        self.assertEqual(a,b)
        for name in ARMS:
            prompt=request_for(data,name)
            self.assertIn("灵田佃户",prompt)
            self.assertIn("N001",prompt)
            self.assertIn("六个外界小时",prompt)
            self.assertNotIn("主角必然突破",prompt)
        self.assertNotEqual(request_for(data,"rate1"),
                            request_for(data,"rate3"))

    def test_time_units_present_only_when_rules_attached(self):
        data=read_frozen()
        baseline=request_for(data,"baseline")
        self.assertNotIn("subjective_hour",baseline)
        for arm in ("rate1","rate3"):
            q=request_for(data,arm)
            self.assertIn("subjective_hour",q)
            self.assertIn("世界",q)
            self.assertIn("世界时钟1008小时",q)

if __name__=="__main__":unittest.main()
