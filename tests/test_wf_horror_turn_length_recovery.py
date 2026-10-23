"""Bounded original-prose rescue from an actual 975-codepoint horror failure.

This is an INVENTED test fixture, not a copy of any model/manuscript. Legacy
V96 still refuses >950; unified guarded candidate may keep <=1024 without
truncation and with an explicit review flag. Only bad trace is reviewable.
"""
import inspect
import json
import unittest

from writerforge.v96_causal_turns import (
    check_turn,review_only_model_turn,trace_failure_reviewable,
    MAX_PROSE_CHARS,CONTINUITY_MAX_PROSE_CHARS,V96CausalDraftError,
)
from writerforge.writing_assist import AutonomousWriting


def sample(length):
    action="秦真把一张观察纸合上，选择留在门外继续等待。"
    result="她的选择让门里的异响暂时失去回应，同行者只好停下。"
    base="窗边的旧石灰留下雨水经过的痕迹，夜气渐渐沉下来。"
    rest=length-len(action)-len(result)
    assert rest>=150
    prose=(base*((rest//len(base))+1))[:rest]+action+result
    assert len(prose)==length
    return json.dumps({
        "prose":prose,
        "trace":{"action_quote":action,"effect_quote":result,
                 "parent_effect_quote":None}
    },ensure_ascii=False,separators=(",",":")),prose


def beat():
    return {"id":"t01","kind":"decision","actor":"秦真",
            "goal":"秦真选择保留不确定性并暂时不打开旧门",
            "causal_parent":None,"craft_focus":[]}


class GuardedProseLength(unittest.TestCase):
    def test_existing_legacy_950_limit_is_unchanged(self):
        self.assertEqual(MAX_PROSE_CHARS,950)
        self.assertEqual(CONTINUITY_MAX_PROSE_CHARS,1024)
        prose,_=sample(975)
        with self.assertRaisesRegex(
                V96CausalDraftError,"WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID"):
            check_turn(prose,beat(),mode="causal_guard")

    def test_exact_975_char_original_kept_without_any_rewrite(self):
        raw,body=sample(975)
        row=check_turn(raw,beat(),mode="causal_guard",
                       max_prose_chars=CONTINUITY_MAX_PROSE_CHARS)
        self.assertEqual(row["prose"],body)
        self.assertEqual(len(row["prose"]),975)
        self.assertTrue(row["receipt"]["source_turn_requires_length_review"])
        self.assertTrue(row["receipt"]["prose_not_silently_truncated"])
        self.assertFalse(row["receipt"]["eligible_for_factjournal_KNOWN"])
        self.assertEqual(row["receipt"]["causal_check"],
                         "EXACT_OBSERVABLE_ANCHORS_ONLY")

    def test_above_unified_bound_still_refused(self):
        raw,_=sample(1025)
        with self.assertRaisesRegex(
                V96CausalDraftError,"WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID"):
            check_turn(raw,beat(),mode="causal_guard",
                       max_prose_chars=CONTINUITY_MAX_PROSE_CHARS)
        with self.assertRaisesRegex(
                V96CausalDraftError,"WF96_UNTRUSTED_TURN_PROSE_LIMIT"):
            check_turn(raw,beat(),mode="causal_guard",max_prose_chars=90000)

    def test_real_length_or_schema_failure_is_not_disguised_as_trace(self):
        self.assertFalse(trace_failure_reviewable(
            "WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID"))
        self.assertFalse(trace_failure_reviewable(
            "WF96_AUTHOR_CONFIRMED_KNOWLEDGE_BOUNDARY_VIOLATION"))
        self.assertTrue(trace_failure_reviewable(
            "WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED"))
        src=inspect.getsource(AutonomousWriting.run)
        self.assertIn("not trace_failure_reviewable(",src)
        self.assertIn("_WF96_GUARDED_TURN_CHARS",src)
        self.assertIn("unified_source_length_reviews",src)
        self.assertIn("WFCORE_OVERSIZED_TURN_SOURCE_REVIEW",src)


if __name__=="__main__":
    unittest.main()
