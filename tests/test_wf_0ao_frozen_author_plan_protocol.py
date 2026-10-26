"""0.AO offline: real 0.AM DeepSeek plans replayed, new model ONLY for prose.

Structural test only; original 0.AM provider wire SHA is checked in live
preflight with downloaded GitHub artifact. No paid calls, R2, Canon or books.
"""
from __future__ import annotations
import inspect
import unittest

from experiments import wf_0ao_frozen_real_deepseek_plan_prose_once_20261026 as trial
from experiments import wf_0am_real_history_same_model_g_once_20261026 as old
from test_wf_0an_actual_dialogue_quiet_source_links import (
    ORIGINAL_OUTLINE,REAL_DECODED_SHA,
)
from writerforge.v96_causal_turns import parse_turn_outline
from writerforge.writing_assist import _normalize_optional_model_craft_labels


class FrozenOriginalWriterPlanProtocol(unittest.TestCase):
    def test_actual_six_original_model_beat_parent_links_unchanged(self):
        self.assertEqual(trial.TURN_REPLY_SHA,REAL_DECODED_SHA)
        self.assertEqual(trial.h(ORIGINAL_OUTLINE),REAL_DECODED_SHA)
        cleaned,receipt=_normalize_optional_model_craft_labels(ORIGINAL_OUTLINE)
        beats=parse_turn_outline(cleaned)
        self.assertEqual(len(beats),6)
        self.assertEqual(beats[2]["causal_parent"],"t02")
        self.assertEqual(beats[5]["causal_parent"],"t05")
        self.assertTrue(receipt["only_model_optional_craft_fields_adjusted"])
        self.assertEqual(receipt["original_model_plan_sha256"],REAL_DECODED_SHA)

    def test_one_prior_model_plan_replayed_at_zero_new_model_cost(self):
        self.assertEqual(trial.ORIGINAL_MODEL_RUN,40257489862)
        self.assertEqual(trial.MAX_NEW_CALLS,16)
        self.assertEqual(trial.MAX_RESERVED_OUTPUT_TOKENS,40000)
        self.assertNotEqual(trial.OUT,old.OUTPUT)
        caller=inspect.getsource(trial.OriginalPlanThenSameWriter)
        self.assertIn("self.replayed_first=True",caller)
        self.assertIn("return self.first",caller)
        self.assertIn("WF0AO_OLD_REAL_CHAPTER_PLAN_PROMPT_CHANGED",caller)
        self.assertIn("on_response_wire=self.on_original",caller)
        self.assertIn("WF0AO_REAL_AUTHOR_WIRE_IMMUTABLE_NO_RETRY",caller)
        self.assertEqual(caller.lower().count("retry("),0)

    def test_single_existing_g_core_not_duplicate_literary_memory(self):
        body=inspect.getsource(trial.main)
        freeze=inspect.getsource(trial.freeze_original_model_decisions)
        self.assertIn("freeze_original_model_decisions()",body)
        self.assertLess(body.index("freeze_original_model_decisions()"),
                        body.index("OriginalPlanThenSameWriter("))
        self.assertIn('frozen_turn_outlines=(turns,)',body)
        self.assertIn('draft_mode="continuity_guard"',body)
        self.assertIn('self_edit_timing="ai_decides"',body)
        self.assertIn("resume_story_checkpoint=root",body)
        self.assertIn("read_core_from_resume",body)
        self.assertIn("new_graph",body)
        self.assertIn("R2_reads",body)
        self.assertIn("Canon_writes",body)
        self.assertIn('source_sha256',freeze)
        self.assertIn('wire_sha256',freeze)
        self.assertIn('prompt_sha256',freeze)
        self.assertIn('original_model_plan_sha256',freeze)
        self.assertNotIn("model.generate(",body)


if __name__=="__main__":
    unittest.main()
