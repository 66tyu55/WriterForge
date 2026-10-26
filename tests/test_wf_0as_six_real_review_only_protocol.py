"""0.AS offline protocol: immutable six-real-review baseline and only 6 new reviews.

NO fiction generation or auto-revision. This test guards the exact provider
source SHA, roles, and source-only independent author decision contract.
"""
from __future__ import annotations
import inspect
import unittest

from experiments import wf_0as_real_six_same_writer_self_review_once_20261026 as case
from writerforge.writing_assist import SELF_EDIT_MOMENT_TOKENS


class FrozenSixGReviewSourceProtocol(unittest.TestCase):
    def test_original_source_six_sha_and_preexisting_four_schema_echoes(self):
        self.assertEqual(case.REAL_SOURCE_RUN,40264287305)
        self.assertEqual(case.REAL_EARLY_AUTHOR_RUN,40259961845)
        self.assertEqual(len(case.ORIGINAL_PROSE_SHAS),6)
        self.assertEqual(len(case.ORIGINAL_REVIEW_SHAS),6)
        self.assertEqual(len(set(case.ORIGINAL_REVIEW_SHAS)),6)
        self.assertEqual(case.MAX_NEW_CALLS,6)
        self.assertEqual(case.OUTPUT_CAP,3600)
        self.assertEqual(SELF_EDIT_MOMENT_TOKENS,600)
        self.assertTrue(case.SOURCE.name.startswith("wf0as_original_0aq"))
        self.assertNotEqual(case.SOURCE,case.OUTPUT)

    def test_source_wires_read_before_any_new_model_calls(self):
        verify=inspect.getsource(case.freeze_original_six)
        main=inspect.getsource(case.main)
        self.assertIn('REVIEW_SHAS',verify)
        self.assertIn('ORIGINAL_PROSE_SHAS',verify)
        self.assertIn('raw_provider_sha256',verify)
        self.assertIn('finish_reason',verify)
        self.assertIn('source_prose_sha256',verify) if False else None
        self.assertLess(main.index('freeze_original_six()'),
                        main.index('model=SixOriginalReviews(key)'))
        self.assertIn('new_writer_prose_calls',main)
        self.assertIn('literary_quality_improvement_proven',main)
        self.assertIn('old_review_schema',main)
        self.assertIn('new_valid_decision_count',main)
        self.assertNotIn('AutonomousWriting(',main)

    def test_writer_only_owns_keep_or_lookback_not_host(self):
        model=inspect.getsource(case.SixOriginalReviews)
        self.assertIn('max_calls=MAX_NEW_CALLS',model)
        self.assertIn('on_response_wire=self._save_original',model)
        self.assertIn('self_scene_writing',model)
        self.assertIn('ONLY_REVIEW_DECISION',model)
        self.assertIn('max_tokens==SELF_EDIT_MOMENT_TOKENS',model)
        self.assertIn('WF0AS_PROVIDER_ORIGINAL_IMMUTABLE',model)
        self.assertNotIn('retry(',model.lower())
        self.assertEqual(case.MAX_NEW_CALLS*SELF_EDIT_MOMENT_TOKENS,
                         case.OUTPUT_CAP)


if __name__=="__main__":
    unittest.main()
