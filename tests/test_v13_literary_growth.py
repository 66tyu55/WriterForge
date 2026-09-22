import unittest

from writerforge import (
    EndingBacktraceInput, EndingBacktraceAnalyzer,
    StoryElementProfile, OrthogonalOriginality,
    ObservedScene, ObservedStoryAuditor,
    CraftEngine, CraftRequest,
)


class V13LiteraryGrowthTests(unittest.TestCase):
    def test_ending_backtrace_flags_missing_setup_and_unearned_resolution(self):
        result = EndingBacktraceAnalyzer().analyze(EndingBacktraceInput(
            central_question_resolved=True,
            protagonist_choice_drives_resolution=False,
            payoff_elements=("old_key", "secret_tunnel"),
            established_setups=("old_key",),
        ))
        self.assertFalse(result.traceable)
        self.assertEqual(result.missing_setups, ("secret_tunnel",))
        self.assertIn("PAYOFF_WITHOUT_SETUP", result.issues)
        self.assertIn("UNEARNED_RESOLUTION", result.issues)

    def test_ending_can_be_traceable_and_surprising_without_overexplaining(self):
        result = EndingBacktraceAnalyzer().analyze(EndingBacktraceInput(
            central_question_resolved=True,
            protagonist_choice_drives_resolution=True,
            payoff_elements=("promise", "scar"),
            established_setups=("promise", "scar", "letter"),
            route_subverts_surface_expectation=True,
            final_image_echo=True,
            irreversible_cost_or_change=True,
        ))
        self.assertTrue(result.traceable)
        self.assertTrue(result.surprising)
        self.assertTrue(result.resonant)
        self.assertEqual(result.issues, ())

    def test_orthogonal_originality_detects_default_cluster(self):
        default = StoryElementProfile("wise_mentor", "knows_plot", "help_hero", "guide", ("teach",))
        d = OrthogonalOriginality().diagnose(candidate=default, default=default, required_functions=("teach",))
        self.assertIn("DEFAULT_CLUSTER", d.issues)
        self.assertEqual(d.missing_functions, ())

    def test_orthogonal_originality_detects_cosmetic_swap(self):
        default = StoryElementProfile("fbi", "knows_plot", "stop_hero", "antagonist", ("pressure",))
        candidate = StoryElementProfile("corporate_security", "knows_plot", "stop_hero", "antagonist", ("pressure",))
        d = OrthogonalOriginality().diagnose(candidate=candidate, default=default, required_functions=("pressure",))
        self.assertEqual(d.changed_axes, ("form",))
        self.assertIn("COSMETIC_SWAP", d.issues)

    def test_originality_must_preserve_required_function(self):
        default = StoryElementProfile("mentor", "plot_aware", "train_hero", "guide", ("teach", "pressure"))
        candidate = StoryElementProfile("rival", "unaware", "win_status", "independent_actor", ("pressure",))
        d = OrthogonalOriginality().diagnose(candidate=candidate, default=default, required_functions=("teach", "pressure"))
        self.assertIn("FUNCTION_LOSS", d.issues)
        self.assertEqual(d.missing_functions, ("teach",))

    def test_reverse_outline_detects_observed_story_drift(self):
        report = ObservedStoryAuditor().analyze([
            ObservedScene("s1", "introduce_mystery", "relationship_fracture", "leave", ("relationship",), ("dread",)),
            ObservedScene("s2", "collect_clue", "relationship_fracture", "hide_truth", ("belief",), ("attachment",)),
            ObservedScene("s3", "travel", "", "", (), ()),
        ])
        self.assertEqual(len(report.drifts), 2)
        self.assertEqual(report.functionless_scene_ids, ("s3",))
        self.assertEqual(report.persistent_unplanned_functions, ("relationship_fracture",))

    def test_reverse_outline_does_not_call_quiet_scene_functionless_when_reader_effect_exists(self):
        report = ObservedStoryAuditor().analyze([
            ObservedScene("quiet", "recovery", "", "", (), ("warmth",)),
        ])
        self.assertEqual(report.functionless_scene_ids, ())

    def test_temporal_reordering_is_internal_craft_card_not_new_group(self):
        plan = CraftEngine().plan(CraftRequest(needs=("nonlinear", "recontextualization")))
        self.assertEqual(len(plan.groups), 1)
        self.assertEqual(plan.techniques[0].id, "temporal_reordering")


if __name__ == "__main__":
    unittest.main()
