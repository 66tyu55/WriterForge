"""V46 truthfulness regression: do not certify an incomplete literary Skill."""
import unittest
from scripts.audit_v46_skill_completeness import assess, _check_links

class CompletenessGateTests(unittest.TestCase):
    def test_package_metadata_matches_stable_not_experimental(self):
        report=assess()
        self.assertEqual(report["gates"]["G01_skill_package_entry"],"PASS")
        self.assertEqual(report["observations"]["manifest_version"],"27.0.0")
        self.assertEqual(report["observations"]["packaging_version"],"27.0.0")
        self.assertEqual(report["observations"]["last_experimental_generation_examined"],"V45")

    def test_old_learning_components_are_not_relabelled_as_independent_reader(self):
        report=assess()
        self.assertTrue(report["observations"]["reader_learning_records_caller_reactions"])
        self.assertTrue(report["observations"]["scene_semantic_analysis_requires_model_callback"])
        self.assertEqual(report["gates"]["G04_reader_first_actual_semantic_learning"],"NOT_PROVEN")
        self.assertFalse(report["can_claim_literary_skill_learned"])

    def test_existing_chapter_ingest_not_reported_as_semantic_model(self):
        report=assess()
        self.assertTrue(report["observations"]["source_analysis_is_lexical_unverified"])
        self.assertEqual(report["gates"]["G03_chapter_structural_study"],
                         "IMPLEMENTED_STRUCTURAL_ONLY")

    def test_experimental_write_gate_does_not_imply_literary_transfer(self):
        report=assess()
        self.assertTrue(report["observations"]["v45_compiles_character_and_event_state"])
        self.assertEqual(report["gates"]["G07_V45_experimental_state_controls_write"],
                         "IMPLEMENTED_OPT_IN_ONLY")
        self.assertEqual(report["gates"]["G09_unseen_full_story_ablation"],"NOT_PERFORMED")
        self.assertFalse(report["skill_complete"])

    def test_repo_is_not_evidence_of_chat_skill_activation(self):
        report=assess()
        self.assertEqual(report["gates"]["G08_real_host_triggered_skill_loading"],
                         "NOT_VERIFIABLE_IN_GITHUB_CI")
        self.assertFalse(report["observations"]["v45_exposed_via_standard_cli"])

    def test_missing_internal_skill_link_is_detected(self):
        broken="[test](docs/not-a-real-writerforge-skill-file.md)"
        self.assertIn("docs/not-a-real-writerforge-skill-file.md",_check_links(broken))

if __name__=="__main__":
    unittest.main()
