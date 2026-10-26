"""0.AT real prior six source, only two new signed-source author decisions."""
from __future__ import annotations
import inspect
import unittest

from experiments import wf_0at_two_real_author_signed_source_reviews_once_20261026 as trial
from experiments import wf_0as_real_six_same_writer_self_review_once_20261026 as prior
from writerforge.writing_assist import SELF_EDIT_MOMENT_TOKENS


class TrueSourceAwareWriterDoesNotConflateLiteraryVerdicts(unittest.TestCase):
    def test_exact_two_original_paragraph_targets_and_bounded_calls(self):
        self.assertEqual(trial.TARGETS,(5,6))
        self.assertEqual(trial.MAX_NEW_CALLS,2)
        self.assertEqual(trial.MAX_OUTPUT,1200)
        self.assertEqual(SELF_EDIT_MOMENT_TOKENS,600)
        self.assertEqual(trial.ORIGINAL_HISTORY_SHA,
                         "4069722777f98ef5b9bc3b3eaea5429def9ab9b61be0a224114fae9d7ff97991")
        self.assertEqual(trial.prior.ORIGINAL_CHAPTER_SHA,prior.ORIGINAL_CHAPTER_SHA)
        self.assertNotEqual(trial.OUT,prior.OUTPUT)

    def test_v114_source_questions_verified_prior_to_asking_provider(self):
        code=inspect.getsource(trial.signed_previous_source_review_context)
        body=inspect.getsource(trial.main)
        self.assertIn('external_temporal_step(',code)
        self.assertIn('_signed_previous_author_source_question',code)
        self.assertIn('source_note_sha256',code)
        self.assertIn('prior.freeze_original_six()',code)
        self.assertIn('historical.verify_old_real_source()',code)
        self.assertLess(body.index('signed_previous_source_review_context()'),
                        body.index('caller=TwoRealSourceReviewCalls(secret)'))
        self.assertIn('author_edit_applied',body)
        self.assertIn('literary_improvement_proven',body)
        self.assertNotIn('AutonomousWriting(',body)

    def test_no_new_prose_only_same_deepseek_author_source_review(self):
        source=inspect.getsource(trial.TwoRealSourceReviewCalls)
        self.assertIn('on_response_wire=self.wire_before_decode',source)
        self.assertIn('max_calls=MAX_NEW_CALLS',source)
        self.assertIn('ONLY_REVIEW_DECISION',source)
        self.assertIn('SOURCE_REVIEW_NOT_REALLY_DELIVERED',source)
        self.assertIn('WF0AT_WRITER_PROVIDER_EVIDENCE_CANNOT_OVERWRITE',source)
        self.assertIn('self_scene_writing',source)
        self.assertNotIn('retry(',source.lower())
        self.assertEqual(trial.MAX_OUTPUT,trial.MAX_NEW_CALLS*SELF_EDIT_MOMENT_TOKENS)


if __name__=="__main__":
    unittest.main()
