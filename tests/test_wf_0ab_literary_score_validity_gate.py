"""0.AB: a truthful scorecard must not say WF beats a novel due to bad sampling.

Tests are evaluator-tool tests, not judging a novelist's worth or training WF.
"""
import unittest
from experiments.wf_0ab_score_validity_gate import audit_comparability

SOURCE_SHA="2fc1698410418bf136448807335c6359bf515b75e6f9c1e1d1f443a1c928e6cc"
EXPECTED_SHA={
    "1":{
        "A":"d731acb0c5940191bee7e929edc672a9d3459a87b4e96a422c4f05c5ab774cbc",
        "B":"15e09f04cea060e6567760aa172df8157cdfb2eeca80a5f11e6bf4ba223b449e",
        "R":"636172c9a580c1d18b3d15ec48ed4ff22e688e2e95f1b2d0d1343130128da0f1",
    },
    "2":{
        "A":"0366730b6a1cc2ba1a13b8ae99e6aecd8b1fbe3475d4b1bb8908048f3169ba9c",
        "B":"a02019ba500881ad28db87bd320f84679f0e79c77a89f5ec66aee41edf050629",
        "R":"ad3f85a17cba44bc73dbb593689d808ed382633a6e9d0249b0134233410064bb",
    },
}

def synthetic_reference_score():
    return {
        "format":"wf.0aa.frozen-first-two-stages-reference-score.v1",
        "status":"PROVISIONAL_TWO_STAGE_LOW_CONFIDENCE_MODEL_RATINGS",
        "source_reference_sha256":SOURCE_SHA,
        "sample_count":6,
        "overall_average_scores":{"R":62.0,"A":79.0,"B":76.0},
        "sample_character_counts":{
            "1":{"R":208,"A":223,"B":223},
            "2":{"R":230,"A":224,"B":183}},
        "selected_window_sha256":EXPECTED_SHA,
        "same_judge_model_family_as_original_writer":True,
        "this_is_not_human_blind_review":True,
        "cannot_attribute_change_to_WF_in_this_AB_design":True,
        "paid_rating_calls":4,
        "original_book_prose_in_public_artifacts":False,
        "r2_writes":0,"canon_writes":0,
    }

class ScoreInstrumentNotNovelistLiteraryVerdict(unittest.TestCase):
    def test_raw_scores_are_visible_but_no_claim_to_have_beaten_reference(self):
        result=audit_comparability(synthetic_reference_score())
        self.assertEqual(result["raw_local_excerpt_score_100"],
                         {"R":62.0,"A":79.0,"B":76.0})
        self.assertEqual(result["raw_B_minus_A"],-3)
        self.assertIsNone(result["comparable_literary_level_score"])
        self.assertFalse(result["proves_WF_improvement"])
        self.assertFalse(result["proves_original_literary_level_surpassed"])
        self.assertIn("DIFFERENT_NARRATIVE_FUNCTIONS",result["flags"])
        self.assertIn("NO_BARE_MODEL_CONTROL",result["flags"])
        self.assertIn("SAME_MODEL_FAMILY_RATER",result["flags"])

    def test_chapter2_score_has_length_imbalance_not_repairable_by_larger_number(self):
        result=audit_comparability(synthetic_reference_score())
        self.assertIn("STAGE_2_WINDOW_LENGTH_MISMATCH",result["flags"])
        self.assertGreater(result["stage_2_char_length_ratio"],1.20)
        self.assertEqual(result["valid_progression_signal"],False)

    def test_repaired_comparison_cannot_invent_human_blind_evidence(self):
        x=synthetic_reference_score()
        x["same_judge_model_family_as_original_writer"]=False
        x["this_is_not_human_blind_review"]=False
        # Claiming independent reviewers without receipts must be rejected.
        with self.assertRaises(RuntimeError):
            audit_comparability(x)

    def test_original_source_sha_mismatch_blocks_scorecard(self):
        x=synthetic_reference_score()
        x["selected_window_sha256"]["2"]["R"]="0"*64
        with self.assertRaisesRegex(RuntimeError,"WF0AB_REFERENCE_WINDOW_SHA_DRIFT"):
            audit_comparability(x)

    def test_score_out_of_bounds_cannot_be_used_for_conclusions(self):
        x=synthetic_reference_score()
        x["overall_average_scores"]["R"]=101
        with self.assertRaisesRegex(RuntimeError,"WF0AB_SCORE_RANGE_OR_PROVENANCE_INVALID"):
            audit_comparability(x)


if __name__=="__main__":
    unittest.main()
