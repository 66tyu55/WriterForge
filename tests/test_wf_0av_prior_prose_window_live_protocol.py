"""WF 0.AV B++ RED regression, no model.

The author's t04 might gain a valid trace after seeing original t01 prose.
Then t05 legitimately replans from signed valid source, NOT review-only source.
A source-first literary experiment must not mislabel that literary progress as a
failure merely because t05 no longer needs the REVIEW-only fallback.
"""
import unittest
from experiments.wf_0av_prior_prose_window_last_four_calls_once_20261026 import (
    later_author_replan_receipts,
)


def receipt(beat, *, review=False, canon=0, causal=False):
    return {
        "beat_id": beat,
        "review_only_or_quiet_prose_writer_plan": review,
        "source_parent_causal_relation_verified": causal,
        "canon_or_factjournal_writes": canon,
    }


class BPlusPlusRealAuthorAutonomyRegression(unittest.TestCase):
    def test_new_t05_valid_trace_after_t04_real_prose_is_not_a_false_failure(self):
        earlier = [receipt("t02"), receipt("t03")]
        t04 = receipt("t04", review=True)
        t05 = receipt("t05", review=False)
        latest, review_only = later_author_replan_receipts(earlier + [t04, t05])
        self.assertEqual([r["beat_id"] for r in latest], ["t04", "t05"])
        self.assertEqual([r["beat_id"] for r in review_only], ["t04"])

    def test_t05_review_only_still_works(self):
        latest, review_only = later_author_replan_receipts(
            [receipt("t02"), receipt("t03"),
             receipt("t04", review=True), receipt("t05", review=True)])
        self.assertEqual(len(latest), 2)
        self.assertEqual(len(review_only), 2)

    def test_missing_new_author_replan_is_not_silent_success(self):
        with self.assertRaisesRegex(RuntimeError, "WF0AV_BPLUSPLUS"):
            later_author_replan_receipts([
                receipt("t02"), receipt("t03"), receipt("t04", review=True)])

    def test_unsigned_truth_promotion_or_canon_raises(self):
        for unsafe in (receipt("t05", causal=True),receipt("t05", canon=1)):
            with self.subTest(unsafe=unsafe):
                with self.assertRaisesRegex(RuntimeError, "WF0AV_BPLUSPLUS"):
                    later_author_replan_receipts([
                        receipt("t02"),receipt("t03"),
                        receipt("t04", review=True),unsafe])


if __name__ == "__main__":
    unittest.main()
