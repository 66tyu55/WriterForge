"""Falsifiable source-disjoint sealed-inverse preflight, NOT literary accuracy."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "experiments/wf_non_time_source_inverse_frozen_20261113.json"
SCRIPT = ROOT / "experiments/wf_non_time_source_inverse_local_model_once.py"
spec = importlib.util.spec_from_file_location("wf_source_inverse_v3", SCRIPT)
experiment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(experiment)


class SourceDisjointInversePreflightTests(unittest.TestCase):
    def setUp(self):
        self.case = experiment.load_case()

    def test_model_input_not_private_prose_or_novel_ids(self):
        s = FROZEN.read_text(encoding="utf8")
        self.assertTrue(self.case["original_prose_embedded"] is False)
        self.assertTrue(self.case["one_to_one_complete"] is False)
        for t in ("韩立", "秦羽", "林动", "武动乾坤", "凡人修仙传", "星辰变"):
            self.assertNotIn(t, s)

    def test_source_disjoint_learning_and_holdout(self):
        self.assertEqual(self.case["learned_from"], ["A: chapters 1-4", "B: chapters 1-4"])
        self.assertEqual([x[0] for x in self.case["test_world"]["observations"]],
                         [f"C{i:03}" for i in range(1,31)])
        self.assertTrue(all(x["ids"] and all(p.startswith(("A", "B")) for p in x["ids"])
                            for x in self.case["calibration"]))

    def test_no_future_answer_or_gold_leakage(self):
        s = FROZEN.read_text(encoding="utf8").lower()
        for word in ("hidden_future_gold", "exact_holdout_answer", "later_source_text"):
            self.assertNotIn(word, s)
        self.assertFalse(any(row[0].startswith("C03") for row in
                             self.case["test_world"]["observations"] if len(row[0])>4))

    def test_baseline_and_learned_are_same_test_world(self):
        p0 = json.loads(experiment.prompt(self.case, "baseline"))
        p1 = json.loads(experiment.prompt(self.case, "trained_on_source_A_B"))
        self.assertEqual(p0["test"], p1["test"])
        self.assertIsNone(p0["learning_from_two_other_originals"])
        self.assertGreaterEqual(len(p1["learning_from_two_other_originals"]),6)

    def test_character_belief_and_reported_judgement_remain_distinct(self):
        observations={x[0]:x for x in self.case["test_world"]["observations"]}
        self.assertEqual(observations["C026"][2],"CHARACTER_BELIEF")
        self.assertEqual(observations["C009"][2],"REPORTED")
        self.assertEqual(observations["C015"][2],"CHARACTER_SECRET")
        self.assertEqual(observations["C023"][2],"CHARACTER_KNOWLEDGE_LIMIT")

    def test_preflight_before_any_model_call(self):
        p=experiment.preflight(self.case)
        self.assertEqual(p["paid_api_calls"],0)
        self.assertFalse(p["weights_finetuned"])
        self.assertFalse(p["independent_review"])
        self.assertFalse(p["full_original_training_complete"])
        self.assertFalse(p["source_gold_passed_to_model"])
        self.assertEqual(len(p["prompt_preflight"]),2)
        self.assertNotEqual(p["prompt_preflight"][0]["prompt_sha256"],
                            p["prompt_preflight"][1]["prompt_sha256"])

    def test_mutation_prohibits_original_plot_inevitability(self):
        instructions = " ".join(self.case["test_world"]["questions"]).lower()
        self.assertIn("no longer wants parental praise",instructions)
        self.assertIn("cannot be derived",instructions)


if __name__=="__main__":
    unittest.main()
