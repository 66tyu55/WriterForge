"""WF unified-core prose replay gate: source-only, no model, no R2, no canon.

The external Atria psychology failure was an entire ~964-nonwhitespace
character span duplicated 2x. The real provider manuscript is NOT copied
into this public regression fixture. Construct a distinct synthetic case
and separately verify the sealed original locally by SHA.
"""
from __future__ import annotations

import hashlib
import inspect
import re
import unittest

from writerforge.narrative_core import (
    detect_long_prose_replay,NarrativeCoreError,
)
from writerforge.writing_assist import AutonomousWriting


def nonperiodic_body():
    return "".join(
        f"第{index:02d}步，沈砚听见门外的水声，核对桌上留下的线索。"
        f"唐蜃没有转身，他尚不知道铜钱已经落在叶青梧手里。"
        for index in range(20)
    )


class SourceBasedReplayGateTests(unittest.TestCase):
    def test_two_complete_long_copies_are_rejected(self):
        body=nonperiodic_body()
        self.assertGreater(len(body),650)
        raw=("\n\n"+body+"\n\n"+body+"\n")
        result=detect_long_prose_replay(raw)
        self.assertTrue(result["blocked"])
        self.assertFalse(result["needs_review"])
        self.assertEqual(result["finding"],
                         "WFCORE_ENTIRE_LONG_PROSE_REPEATED")
        self.assertEqual(result["exact_repeat_count"],2)
        self.assertEqual(result["minimal_repeated_span"],len(body))
        self.assertEqual(result["non_whitespace_characters"],len(body)*2)
        self.assertEqual(result["source_prose_sha256"],
                         hashlib.sha256(raw.encode()).hexdigest())
        self.assertTrue(result["original_prose_is_never_rewritten"])
        self.assertEqual(result["model_calls"],0)
        self.assertEqual(result["canon_writes"],0)

    def test_real_case_shape_psychological_epilogue_duplicate(self):
        body=(
            "沈砚把旧信重新折好，放回桌上的抽屉。"
            "他一直担心自己仇恨的方向错了，夜色越深越想先查证真相。"
        )+nonperiodic_body()
        self.assertGreater(len(body),900)
        report=detect_long_prose_replay(
            body+" \n\n"+body)
        self.assertTrue(report["blocked"])
        self.assertEqual(report["exact_repeat_count"],2)

    def test_nonduplicated_long_prose_is_not_blocked(self):
        body=nonperiodic_body()
        report=detect_long_prose_replay(
            body+"\n然而叶青梧推开院门，说这一切还需要重新验证。")
        self.assertFalse(report["blocked"])
        self.assertFalse(report["needs_review"])
        self.assertIsNone(report["finding"])

    def test_short_refrain_and_punctuation_are_not_misclassified(self):
        chorus="雨仍在下。"
        body=(chorus+"沈砚凝望空院，久久没有说话。" )*11
        report=detect_long_prose_replay(body)
        # A short refrain may be intentional lyric texture.
        self.assertFalse(report["blocked"])
        self.assertNotEqual(report["finding"],
                            "WFCORE_ENTIRE_LONG_PROSE_REPEATED")

    def test_long_bookending_echo_review_not_hard_rejection(self):
        body=nonperiodic_body()
        scene=body+"唐蜃推开门，意外的消息改写了旧事。"+body[:len(body)-60]
        report=detect_long_prose_replay(scene)
        self.assertFalse(report["blocked"])
        self.assertTrue(report["needs_review"])
        self.assertEqual(report["finding"],
                         "WFCORE_LONG_TEXT_ECHO_NEEDS_REVIEW")

    def test_whitespace_only_not_a_manuscript(self):
        with self.assertRaisesRegex(
                NarrativeCoreError,"REPLAY_EMPTY"):
            detect_long_prose_replay(" \n\t ")
        with self.assertRaisesRegex(
                NarrativeCoreError,"REPLAY_INPUT_BOUNDS"):
            detect_long_prose_replay("字"*20001)

    def test_no_state_mutation_or_literary_truth_claim(self):
        report=detect_long_prose_replay(nonperiodic_body())
        self.assertFalse(report["literary_quality_verified"])
        self.assertTrue(report["original_prose_is_never_rewritten"])
        self.assertEqual(report["model_calls"],0)
        self.assertEqual(report["canon_writes"],0)

    def test_actual_continuity_writer_checks_before_turn_acceptance(self):
        text=inspect.getsource(AutonomousWriting.run)
        position=text.index("replay_check=detect_long_prose_replay")
        accepted=text.index("accepted_turns.append(evidence)")
        self.assertLess(position,accepted)
        self.assertIn('"unified_prose_replay_checks"',text)
        self.assertIn('"unified_completed_chapter_replay"',text)
        self.assertIn("WFCORE_ENTIRE_LONG_PROSE_REPEATED",text)

    def test_complete_chapter_guard_precedes_save_candidate(self):
        text=inspect.getsource(AutonomousWriting.run)
        check=text.index("complete_replay=detect_long_prose_replay(body)")
        saved=text.index("saved=save_candidate(packet,body")
        self.assertLess(check,saved)
        # Existing V96 rejection record retains exact error reason and
        # source hash while no candidate is promoted.
        self.assertIn("chapter-{index:03d}-rejected.json",text)
        self.assertIn('"canonical_fact_writes":0',text)
        self.assertIn('"automatic_repair_attempts":0',text)
        self.assertIn('"model_output_sha256":sha256(',text)


if __name__=="__main__":
    unittest.main()
