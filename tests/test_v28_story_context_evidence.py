"""No network tests for topic-specific positive and negative model observations."""
import unittest
from hashlib import sha256
from test_v28_three_random_openings_audit import FakeR2
from scripts.audit_wf_three_random_openings_v10 import collect
from writerforge.r2_storage import _canonical
from writerforge.reverse_story_context_evidence import (
    derive_story_context_candidates,StoryContextEvidenceError,
)

class StoryContextCandidatesTests(unittest.TestCase):
    def report(self):
        r=collect(FakeR2(),persist=False)
        # Deliberately synthesize one fully negative genre context while
        # preserving two positives using the exact same HOST technique pair.
        row=r["results"][1]
        differences={"perception":-8,"causality":-7,"information":-7,
                     "continuity":-8,"language":-7}
        row["dimension_deltas"]=differences
        row["raw_effect"]=-7.4
        row["writerforge_raw_mean"]=row["baseline_raw_mean"]-7.4
        row["all_five_negative"]=True
        row["writerforge_30_display"]=22.6
        return r

    def test_one_genre_negative_must_not_erase_two_positive_genres(self):
        report=self.report()
        sha=sha256(_canonical(report)).hexdigest()
        out=derive_story_context_candidates(report,report_sha256=sha)
        self.assertTrue(out["same_mechanism_pair_all_three"])
        self.assertTrue(out["positive_and_negative_same_pair"])
        self.assertFalse(out["disable_global_mechanisms"])
        self.assertFalse(out["automatic_skill_promotion"])
        self.assertEqual(out["second_window"],"LOCKED")
        rows=out["model_only_contextual_observations"]
        self.assertEqual(rows[1]["story_id"],"cedar_night")
        self.assertEqual(rows[1]["model_effect"],-7.4)
        self.assertEqual(rows[1]["candidate_status"],
            "NEGATIVE_ALL_FIVE_NEEDS_INDEPENDENT_REVIEW")
        self.assertEqual(rows[0]["candidate_status"],"MODEL_POSITIVE_UNVERIFIED")
        self.assertEqual(rows[2]["candidate_status"],"MODEL_POSITIVE_UNVERIFIED")
        self.assertTrue(all(not r["auto_apply_as_skill"] for r in rows))

    def test_forged_digest_and_changed_mechanism_fail_closed(self):
        report=self.report()
        with self.assertRaises(StoryContextEvidenceError):
            derive_story_context_candidates(report,report_sha256="f"*64)
        report["results"][1]["mechanisms_unreviewed"]=["UNKNOWN_COPY_FROM_NOVEL"]
        h=sha256(_canonical(report)).hexdigest()
        with self.assertRaisesRegex(StoryContextEvidenceError,"MECHANISM_OUTSIDE"):
            derive_story_context_candidates(report,report_sha256=h)

    def test_wrong_means_are_detected_even_if_digest_is_correct(self):
        report=self.report()
        report["results"][1]["writerforge_raw_mean"]=98
        h=sha256(_canonical(report)).hexdigest()
        with self.assertRaisesRegex(StoryContextEvidenceError,"AB_GROUP_MEANS"):
            derive_story_context_candidates(report,report_sha256=h)

if __name__=="__main__":
    unittest.main()
