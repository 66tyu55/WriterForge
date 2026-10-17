"""No-network protocol regression for the three fixed random experiments."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from writerforge.reverse_random_chapters import chosen_chapters,selection_hash
from writerforge.reverse_discovery_models import ROLE_MODELS
from scripts import run_wudong_random3_v7 as runner
from scripts.run_wudong_transfer_baseline30_v5 import TRANSFER_TASK as prior_task
from writerforge.reverse_later_window import later_chapter_diagnostic

class Random3RunnerTests(unittest.TestCase):
    def test_work_preserved_and_cap_same(self):
        self.assertEqual(chosen_chapters(),(3,15,17))
        self.assertEqual(runner.TRANSFER_TASK,prior_task)
        self.assertEqual(len(selection_hash()),64)
        self.assertEqual(ROLE_MODELS["writer"],"glm-5.3")
        self.assertEqual(ROLE_MODELS["planner"],ROLE_MODELS["critic"])
        self.assertIn("random3-v7",runner.PREFIX)
        self.assertNotIn("v6",runner.PREFIX)
    def test_invalid_slot_stops_before_api_or_r2(self):
        for invalid in (-1,3,100,None,"1"):
            with self.subTest(slot=invalid):
                with self.assertRaisesRegex(Exception,"SAMPLED_SLOT_INVALID"):
                    runner.run(slot=invalid)
