"""0.CA replay of 0.BZ REAL local original bytes; no model inference.

Only candidate source prose can survive an untrusted *optional trace* envelope.
Never turn copied model claims into effects/known facts; malformed JSON, missing
prose, prohibited source text and unsourced character choices stay RED.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from writerforge.v96_causal_turns import (
    V96CausalDraftError,parse_turn_outline,check_turn,
    review_only_model_turn,
)
from writerforge.writing_assist import _normalize_optional_model_craft_labels

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"experiments/wf_0bz_real_local_originals_20261029"


def real_reply(scene,arm,n):
    path=SOURCE/scene/arm/f"call_{n:02d}_raw.json"
    return json.loads(path.read_text("utf8"))["choices"][0]["text"]


class RealAuthorSourceFirstRecovery(unittest.TestCase):
    def test_short_real_character_goals_survive_without_changing_authored_intent(self):
        original=real_reply("medicine-rights","wf_g",2)
        adjusted,receipt=_normalize_optional_model_craft_labels(original)
        self.assertIsNotNone(receipt)
        beats=parse_turn_outline(adjusted)
        self.assertEqual(len(beats),10)
        self.assertEqual(beats[1]["goal"],"扣住药签")
        self.assertEqual(beats[1]["causal_parent"],"t01")
        self.assertEqual(beats[4]["actor"],"夏舟")
        self.assertEqual(beats[4]["craft_focus"],[])
        self.assertNotEqual(original,adjusted)
        self.assertEqual(receipt["model_calls"],0)

    def test_actual_original_prose_is_kept_only_for_review_with_invalid_trace(self):
        plan=real_reply("medicine-rights","wf_g_reading",2)
        beats=parse_turn_outline(plan)
        raw=real_reply("medicine-rights","wf_g_reading",3)
        original_doc=json.loads(raw)
        self.assertEqual(original_doc["trace"],{})
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID"):
            check_turn(raw,beats[0],mode="causal_guard",
                       max_prose_chars=1024)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "WF96_TRACE_RECOVERY_NOT_AN_OPTIONAL_CITATION_FAILURE"):
            review_only_model_turn(
                raw,beats[0],
                failure_code="WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID",
                max_prose_chars=1024)
        candidate=review_only_model_turn(
            raw,beats[0],
            failure_code="WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID",
            max_prose_chars=1024,
            allow_untrusted_trace_envelope=True)
        self.assertEqual(candidate["prose"],original_doc["prose"].strip())
        self.assertIsNone(candidate["effect_quote"])
        receipt=candidate["receipt"]
        self.assertTrue(receipt["source_causal_review_required"])
        self.assertEqual(receipt["causal_check"],
                         "TRACE_REJECTED_SOURCE_PROSE_REVIEW_ONLY")
        self.assertEqual(receipt["model_trace_failure_code"],
                         "WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID")
        self.assertTrue(receipt["untrusted_trace_envelope_ignored"])
        self.assertFalse(receipt["causal_relation_verified"])
        self.assertFalse(receipt["eligible_for_factjournal_KNOWN"])
        self.assertFalse(receipt["eligible_for_experience_promotion"])
        self.assertTrue(receipt["candidate_requires_author_acceptance"])

    def test_not_a_general_json_or_story_repair(self):
        raw=real_reply("mountain-array","wf_g",2)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "WF96_JSON_INVALID_OR_DUPLICATE_KEYS"):
            parse_turn_outline(raw)
        bad=real_reply("mountain-array","wf_g_reading",2)
        adjusted,_=_normalize_optional_model_craft_labels(bad)
        with self.assertRaisesRegex(V96CausalDraftError,
                                    "WF96_TURN_PLAN_FIELDS_ID_OR_CRAFT_INVALID"):
            parse_turn_outline(adjusted)

    def test_missing_prose_extra_story_facts_and_approved_exclusions_stay_red(self):
        raw=real_reply("medicine-rights","wf_g_reading",3)
        beat=parse_turn_outline(
            real_reply("medicine-rights","wf_g_reading",2))[0]
        obj=json.loads(raw)
        cases=[
            {**obj,"prose":""},
            {**obj,"prose":"写"},
            {**obj,"confirmed_private_fact":"伪造"},
            {**obj,"trace":{"whatever":"unverified"}},
        ]
        for case in cases:
            with self.subTest(case=str(case)[:75]):
                with self.assertRaisesRegex(V96CausalDraftError,
                                            "WF96_TRACE_RECOVERY_UNSAFE_PROSE_OR_SCHEMA"):
                    review_only_model_turn(
                        json.dumps(case,ensure_ascii=False),beat,
                        failure_code="WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID",
                        max_prose_chars=1024,
                        allow_untrusted_trace_envelope=True)
        with self.assertRaisesRegex(
                V96CausalDraftError,
                "WF96_AUTHOR_CONFIRMED_KNOWLEDGE_BOUNDARY_VIOLATION"):
            review_only_model_turn(
                raw,beat,
                failure_code="WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID",
                max_prose_chars=1024,
                allow_untrusted_trace_envelope=True,
                author_confirmed_forbidden_phrases=("失踪者姐姐的弟弟夏舟",))

    def test_original_model_still_is_not_claimed_to_have_used_a_reading(self):
        for scene in ("medicine-rights","mountain-array"):
            answer=real_reply(scene,"wf_g_reading",1)
            if answer.startswith("```json"):
                answer=answer.split("\n",1)[1].rsplit("```",1)[0]
            doc=json.loads(answer)
            self.assertIn(doc["decision"],("USE","SKIP"))
            self.assertNotIn("reading_choice",doc)


if __name__=="__main__":
    unittest.main()
