"""Synthetic, no-model proof of one-chapter low-effort recovery isolation."""
import unittest
from unittest.mock import patch
from writerforge.reverse_random_chapters import chosen_chapters
from scripts import run_wudong_random3_v8_low_effort_ch17 as recovery
from scripts import run_wudong_random3_v7 as old
from writerforge.reverse_discovery_models import DiscoveryError,ROLE_MODELS

class RecoveryTests(unittest.TestCase):
    def test_source_and_task_preserved_but_protocol_key_differs(self):
        self.assertEqual(chosen_chapters(),(3,15,17))
        self.assertEqual(recovery.TRANSFER_TASK,old.TRANSFER_TASK)
        self.assertEqual(recovery.SOURCE_SHA,old.SOURCE_SHA)
        self.assertNotEqual(recovery.PREFIX,old.PREFIX)
        self.assertNotEqual(recovery.TRIAL,old.TRIAL)
        self.assertEqual(recovery.BUDGET_PROFILE,(5500,8500,7000))
        self.assertLessEqual(5500+4*8500+7000,50000)
        self.assertEqual(ROLE_MODELS["writer"],"glm-5.3")
    def test_cannot_accidentally_recharge_prior_success_slots(self):
        for slot in (0,1,-1,3):
            with self.subTest(slot=slot):
                with self.assertRaisesRegex(DiscoveryError,"SLOT17_ONLY"):
                    recovery.run(slot=slot)
if __name__=="__main__":
    unittest.main()
