"""Real B source re-evaluation: no models, cannot forge original artifacts."""
import unittest
from pathlib import Path
from experiments import wf_0v_real_B_physical_source_replay_20261025 as replay


class GenuineLockedBReplay(unittest.TestCase):
    def test_boundaries_never_obtain_model_or_original_novel(self):
        self.assertEqual(replay.PRIOR_RUN,40163959949)
        self.assertEqual(len(replay.PRIOR_WIRES),2)
        self.assertEqual(replay.OUT.name,
                         "wf_0v_real_B_physical_source_replay_20261025")
        self.assertEqual(len(replay.PRIOR_B_FIRST),64)
        self.assertEqual(len(replay.PRIOR_B_SECOND),64)

    @unittest.skipUnless(Path("wf0t_prior_paired_originals/STATUS.json").exists(),
                         "Original genuine provider zip only mounted by replay workflow")
    def test_true_original_B_source_wires_against_current_source_transactions(self):
        result=replay.run()
        self.assertEqual(result["new_provider_requests"],0)
        self.assertEqual(result["original_provider_run_id"],40163959949)
        self.assertFalse(result["real_model_original_prose_rewritten"])
        self.assertEqual(result["new_relation_review_status"],
                         "HELD_NEEDS_SOURCE_RELATION_REVIEW")
        self.assertEqual(result["new_accepted_revision"],0)
        self.assertFalse(result["literary_quality_improvement_proven"])
        self.assertEqual(len(result["review_pair_sources"]),1)
        self.assertEqual(result["Canon_writes"],0)
        self.assertEqual(result["R2_reads"],0)
        self.assertEqual(result["R2_writes"],0)


if __name__=="__main__":
    unittest.main()
