"""Recovery permits only V29 failed slots 1/2, no old successful slot."""
import unittest
from writerforge.reverse_discovery_models import DiscoveryError
from scripts import run_v29_old_new_length_recovery as v2
from scripts import run_v29_old_new_holdout as v1
from writerforge.v29_fresh_holdout import chosen_ids,task

class TechnicalRecoveryTests(unittest.TestCase):
    def test_genuine_holdout_prompts_and_roles_unchanged(self):
        self.assertEqual(len(chosen_ids()),3)
        self.assertEqual(v2.SOURCE_SHA,v1.SOURCE_SHA)
        self.assertEqual(v2.SOURCE_UNIT_SHA,v1.SOURCE_UNIT_SHA)
        self.assertEqual(v2.TRIAL,"v29-sourceblind-old-vs-semantic-two-arm-length-feedback-recovery")
        for slot in (1,2):
            self.assertNotEqual(v2.root_for_slot(slot),v1.root_for_slot(slot))
            self.assertEqual(task(slot),task(slot))
    def test_successful_first_slot_not_rerun(self):
        for slot in (0,3,-1,None,"1"):
            with self.subTest(slot=slot):
                with self.assertRaisesRegex(DiscoveryError,"ONLY_FAILED_V29_HOLDOUT"):
                    v2.run(slot=slot)
if __name__=="__main__":
    unittest.main()
