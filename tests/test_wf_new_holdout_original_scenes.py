"""Pure offline literary holdout pre-registration checks; no model requests."""
import inspect
import unittest

from experiments import wf_holdout_three_fresh_literary_genres as holdout
from writerforge.narrative_core import new_graph,advance_graph
from experiments.wf_real_self_scene_diagnostics import source_event


class UnseenLiteraryHoldout(unittest.TestCase):
    def test_three_unseen_genres_and_new_cast(self):
        self.assertTrue(holdout.check_cases())
        self.assertEqual(
            set(holdout.GENRES),{"plot","climax","horror"})
        old={"沈砚","唐蜃","叶青梧"}
        for genre,case in holdout.CASES.items():
            self.assertIsInstance(case["seed"],str)
            self.assertIsInstance(case["goal"],str)
            self.assertFalse(set(case["cast"]) & old)
            self.assertGreaterEqual(len(case["seed"]),130)
            self.assertGreaterEqual(len(case["goal"]),12)
            self.assertGreaterEqual(len(case["outline"]),35)

    def test_event_seeds_use_existing_unified_character_and_thread(self):
        for genre,case in holdout.CASES.items():
            with self.subTest(genre=genre):
                g=new_graph(project_id="holdout-check",scene_id=genre)
                source=case["seed"]
                events=[
                    source_event(source,i,event)
                    for i,event in enumerate(case.get("event_quotes",()),1)]
                graph=advance_graph(
                    g,project_id="holdout-check",scene_id=genre,
                    chapter_index=1,prose=source,events=events)
                self.assertEqual(graph["model_calls"],0)
                self.assertEqual(graph["canon_writes"],0)
                self.assertEqual(graph["last_event_count"],len(events))
                self.assertNotIn("v123_open_character_arc",graph)

    def test_exact_limit_same_frozen_plans_both_arms_and_no_automatic_retry(self):
        self.assertEqual(holdout.MAX_PROVIDER_CALLS,6)
        self.assertEqual(holdout.MAX_RESERVED_OUTPUT,7900)
        self.assertEqual(holdout.MODELS,("baseline","source_progression"))
        code=inspect.getsource(holdout.run_one)
        self.assertIn("for blind_id,mode in zip",code)
        self.assertIn("plans=plans",code)
        self.assertIn("actual_provider_calls",code)
        self.assertNotIn("retry",inspect.getsource(
            holdout.frozen_new_plans).lower())


if __name__=="__main__":
    unittest.main()
