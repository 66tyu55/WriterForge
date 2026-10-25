"""0.AL: source-only replay of one confirmed real model formatting defect.

Never regenerate 0.AJ romance or scifi prose and never ask a writer model
to return a "corrected" story. Four existing SHA-locked author provider
wires must be confirmed before exactly four possible blind-rater calls.
"""
from __future__ import annotations
import inspect
import unittest

from experiments import wf_0al_replay_scifi_fullwidth_source_and_two_grades_20261025 as replay
from experiments import wf_0aj_diverse_micro_paired_20261025 as third
from writerforge.deepseek_flash_model import (
    recover_single_fullwidth_author_field_separator,
)


class SourceOnly0AJRecoveryProtocol(unittest.TestCase):
    def test_only_original_two_genres_and_zero_new_author_requests(self):
        self.assertEqual(replay.PRIOR_RUN,40205342567)
        self.assertEqual(replay.BATCH,("romance_photos","scifi_airlock"))
        self.assertEqual(len(replay.ORIGINAL_SOURCE_SHA),2)
        self.assertEqual(replay.MAX_NEW_CALLS,4)
        self.assertEqual(replay.MAX_NEW_RATER_TOKENS,6400)
        self.assertEqual(replay.REAL_SCIFI_ORIGINAL_RAW_WIRE_SHA,
                         "61b61ec1c651735e07a01df91b2836d859d98d6dcc397879ef3118afd8755548")
        self.assertEqual(replay.ORIGINAL_SOURCE_SHA["scifi_airlock"]["WF"],
                         "713534247a7071accb8852ee5e72133d3420ceeaabecf92cf1a542d5626edf35")
        self.assertIs(replay.recover_single_fullwidth_author_field_separator,
                      recover_single_fullwidth_author_field_separator)

    def test_original_sha_validation_before_paid_rater_and_no_prose_rewriting(self):
        old=inspect.getsource(replay.replay_four_original_authors)
        main=inspect.getsource(replay.main)
        caller=inspect.getsource(replay.SourceOnlyTwoOrderRater)
        self.assertIn("WF0AL_ORIGINAL_FROZEN_PROMPT_DRIFT",old)
        self.assertIn("WF0AL_ORIGINAL_AUTHOR_PROSE_SHA_MISMATCH",old)
        self.assertIn("WF0AL_ONLY_ONE_REAL_UNDECODED_AUTHOR_WIRE_EXPECTED",
                      inspect.getsource(replay.read_original_provider))
        self.assertLess(main.index("replay_four_original_authors()"),
                        main.index("require_external_runtime()"))
        self.assertIn("copytree(PRIOR/",main)
        self.assertIn('"new_author_calls":0',main)
        self.assertIn('"R2_reads":0',main)
        self.assertIn('"Canon_writes":0',main)
        self.assertIn("max_calls=MAX_NEW_CALLS",caller)
        self.assertIn('role=="craft_analysis"',caller)
        self.assertIn("WF0AL_NO_WRITER_OR_UNREGISTERED_JUDGE_CALL_ALLOWED",
                      caller)
        self.assertIn("on_response_wire=self.save_original_wire",caller)
        self.assertNotIn("retry(",caller.lower()+main.lower())

    def test_pair_length_flags_never_manipulate_original_writing(self):
        romance=replay.ORIGINAL_SOURCE_SHA["romance_photos"]
        self.assertNotEqual(romance["bare"],romance["WF"])
        self.assertEqual(third.AUTHOR_OUTPUT_TOKENS,1400)
        self.assertEqual(third.BATCH,replay.BATCH)
        self.assertIn("NOT_COMPARABLE_PROSE_LENGTH_OUT_OF_200_350",
                      inspect.getsource(replay.main))
        self.assertIn("NOT_COMPARABLE_LENGTH_MISMATCH",
                      inspect.getsource(replay.main))
        self.assertIn("literary_improvement_not_proven",
                      inspect.getsource(replay.main))


if __name__=="__main__":
    unittest.main()
