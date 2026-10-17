"""Synthetic protocol version isolation and no duplicated finished chapters."""
import unittest
from writerforge.reverse_discovery_models import ROLE_MODELS,DiscoveryError
from scripts import run_wudong_random3_v9_length_ch17 as v9
from scripts import run_wudong_random3_v8_low_effort_ch17 as v8
from scripts import run_wudong_random3_v7 as v7

class LengthRecoveryV9Tests(unittest.TestCase):
    def test_same_source_task_and_models_but_versioned_protocol(self):
        self.assertEqual(v9.SOURCE_SHA,v8.SOURCE_SHA)
        self.assertEqual(v9.TRANSFER_TASK,v8.TRANSFER_TASK)
        self.assertEqual(v9.TRANSFER_TASK,v7.TRANSFER_TASK)
        self.assertNotEqual(v9.PREFIX,v8.PREFIX)
        self.assertNotEqual(v9.TRIAL,v8.TRIAL)
        self.assertEqual(v9.COMMON_AB_CHARS,1100)
        self.assertEqual(v9.BUDGET_PROFILE,(5500,8500,7000))
        self.assertEqual(ROLE_MODELS["writer"],"glm-5.3")
        self.assertEqual(ROLE_MODELS["critic"],"deepseek-v4-flash-0731")
    def test_only_chapter17_may_trigger_a_paid_model(self):
        for slot in (0,1,-1,3):
            with self.subTest(slot=slot):
                with self.assertRaisesRegex(DiscoveryError,"SLOT17_ONLY"):
                    v9.run(slot=slot)

if __name__=="__main__":
    unittest.main()
