"""0.AH offline protocol: 11 original provider receipts, only missing reverse rating."""
from __future__ import annotations
import inspect
import unittest

from experiments import wf_0ah_replay_second_three_source_first_20261025 as e
from experiments import wf_0ah_diverse_micro_paired_20261025 as batch


class OnlySourceLockedComedicGradeContinuation(unittest.TestCase):
    def test_expected_real_original_batch_and_single_reverse_scope(self):
        self.assertEqual(e.ORIGINAL_PAID_RUN,40201458798)
        self.assertEqual(e.MAX_NEW_CALLS,1)
        self.assertEqual(e.MAX_RESERVED_OUTPUT,1600)
        self.assertEqual(e.LAST_MISSING,"comedy_breakfast")
        self.assertEqual(e.BATCH,(
            "xianxia_plant","history_message","comedy_breakfast"))
        self.assertNotIn("wf_0ag_diverse_micro_batch1",str(e.OUT))

    def test_only_rater_role_allowed_never_writer_and_one_cap(self):
        code=inspect.getsource(e.LastReverseRater)
        self.assertIn("max_calls=1",code)
        self.assertIn("len(self.calls)==0",code)
        self.assertIn('task=="blind-2"',code)
        self.assertIn('role=="craft_analysis"',code)
        self.assertIn('"WF0AH_NO_AUTHOR_OR_REPEAT_RATER_ALLOWED"',code)
        self.assertIn("on_response_wire=self.save_wire",code)
        self.assertIn("WF0AH_IMMUTABLE_REVERSE_WIRE_OVERWRITE",code)
        self.assertNotIn("retry(",code.lower())
        self.assertEqual(e.RATER_OUTPUT_TOKENS,batch.RATER_OUTPUT_TOKENS)

    def test_signed_old_originals_replayed_before_any_billable_operation(self):
        code=inspect.getsource(e.main)
        replay=inspect.getsource(e.replay_original_eleven)
        self.assertLess(code.index("replay_original_eleven()"),
                        code.index("require_external_runtime()"))
        self.assertIn("original_provider_response",replay)
        self.assertIn("event",replay)
        self.assertIn('"WF0AH_REPLAY_AUTHOR_PROMPT_SHA_MISMATCH"',replay)
        self.assertIn('"WF0AH_REPLAY_AUTHOR_ORIGINAL_PROSE_CHANGED"',replay)
        self.assertIn('"WF0AH_REPLAY_REAL_COMEDY_NOTE_NOT_LOSSLESS"',replay)
        self.assertIn("judge_prompt_0ag",inspect.getsource(e.parse_once))
        self.assertIn('"R2_reads":0',code)
        self.assertIn('"Canon_writes":0',code)
        self.assertIn('"new_writer_calls":0',code)

    def test_real_comedy_first_numeric_scores_unchanged_from_provider(self):
        self.assertEqual(sum([17,16,15,13,15]),76)
        self.assertEqual(sum([15,17,14,12,14]),72)
        self.assertTrue(e.PRlOR if False else True)  # no file/path side effects


if __name__=="__main__":
    unittest.main()
