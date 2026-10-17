"""Three independently premised original first chapters; no real calls in tests."""
from hashlib import sha256
import unittest
from writerforge.random_original_openings import (
    POOL,SEED,selected_ids,task_for_slot,sample_manifest,sample_sha256,
)
from writerforge.reverse_discovery_models import ROLE_MODELS,DiscoveryError
from scripts import run_wf_three_random_openings_v10 as runner

class ThreeOriginalOpeningsTests(unittest.TestCase):
    def test_sample_before_inference_is_deterministic_and_distinct(self):
        self.assertEqual(selected_ids(),("copper_valley","cedar_night","black_tide"))
        self.assertEqual(len(POOL),6)
        self.assertEqual(len(sample_sha256()),64)
        doc=sample_manifest()
        self.assertEqual(doc["selected_ids"],list(selected_ids()))
        self.assertEqual(len(set(doc["selected_task_sha256"])),3)
        self.assertTrue(doc["sample_precommitted"])

    def test_independent_first_chapter_outlines_not_keyword_salad(self):
        tasks=[task_for_slot(i) for i in range(3)]
        self.assertEqual(len(set(tasks)),3)
        for t in tasks:
            self.assertTrue(60<=len(t)<=800)
            self.assertIn("小说第一章正文",t)
            self.assertIn("意外阻断归途",t)
            self.assertIn("意外",t)
            self.assertIn("可回查线索",t)
            self.assertNotIn("林动",t)
            self.assertNotIn("武动乾坤",t)
        for i in range(3):
            self.assertEqual(sha256(tasks[i].encode()).hexdigest(),
                             sample_manifest()["selected_task_sha256"][i])

    def test_fixed_one_learning_source_for_three_random_stories(self):
        self.assertEqual(runner.SOURCE_CHAPTER,3)
        self.assertEqual(runner.SOURCE_FIRST_SHA,
                         "96b6363d40be7b99d5635af1346da0c04e44556fc06e32d1aab04e419e4942fa")
        self.assertEqual(runner.COMMON_AB_CHARS,1070)
        self.assertEqual(runner.BUDGET_PROFILE,(5500,7500,7000))
        self.assertLessEqual(5500+4*7500+7000,50000)
        self.assertEqual(ROLE_MODELS["writer"],"glm-5.3")
        self.assertEqual(ROLE_MODELS["planner"],"deepseek-v4-flash-0731")
        self.assertEqual(ROLE_MODELS["critic"],"deepseek-v4-flash-0731")

    def test_invalid_slot_rejected_before_charge(self):
        for slot in (None,"1",-1,3,9):
            with self.subTest(slot=slot):
                with self.assertRaisesRegex(DiscoveryError,"ORIGINAL_PROMPT_SLOT_INVALID"):
                    runner.run(slot=slot)

if __name__=="__main__":
    unittest.main()
