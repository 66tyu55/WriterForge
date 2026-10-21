"""V110: distinguish model-authored FUTURE CONTENT from host-only branch IDs.

Zero model calls, no R2. The original JSON and original prose are never
changed by any deterministic ID correction. Cannot allow an identically
duplicated story branch to masquerade as two genuinely different futures.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from writerforge.v110_host_branch_identity import (
    recover_host_branch_identity,V110IdentityError,digest,
)
from writerforge.v105_forward_horizon import (
    validate_horizon,V105FutureCausalityError,packed,
)
from writerforge.writing_assist import (
    AutonomousWriting,WritingExecutionError,
)
from test_v105_forward_horizon import simple_branches
from test_v105_writing_integration import (
    V105TrueWritingEntrypoint,foresight_plan,replies,
)
from test_v98_rolling_causal_planner import OUTLINE,GOALS
from test_v96_causal_turns import turns

class BranchIdentityIsolationTest(unittest.TestCase):
    def duplicated(self):
        src=simple_branches()
        src["choices"][1]["id"]=src["choices"][0]["id"]
        return src

    def test_real_two_different_futures_can_get_host_only_labels(self):
        original=self.duplicated()
        stored=deepcopy(original)
        with self.assertRaisesRegex(V105FutureCausalityError,
                                    "BRANCH_ID_NOT_UNIQUE"):
            validate_horizon(original,author_pinned={"power:station":"on"})
        derived,audit=recover_host_branch_identity(original)
        self.assertEqual(original,stored)
        self.assertEqual([c["id"] for c in derived["choices"]],
                         ["wf110_branch_01","wf110_branch_02"])
        self.assertNotEqual(audit["original_horizon_sha256"],
                            audit["derived_horizon_sha256"])
        self.assertTrue(audit["only_routing_identifiers_changed"])
        self.assertTrue(audit["every_prose_action_and_future_debt_unchanged"])
        self.assertFalse(audit["literary_causal_quality_verified"])
        self.assertEqual(audit["no_additional_model_calls"],True)
        self.assertEqual(len(audit["replacements"]),2)
        for prior,later in zip(original["choices"],derived["choices"]):
            self.assertEqual(prior["steps"],later["steps"])
        checked=validate_horizon(derived,author_pinned={"power:station":"on"})
        self.assertEqual(checked["branches"][0]["status"],"SYMBOLICALLY_BLOCKED")
        self.assertEqual(checked["branches"][1]["status"],"CONDITIONAL_OR_UNKNOWN")
        self.assertFalse(checked["literary_causality_proven"])

    def test_identical_story_branches_cannot_be_repaired_as_two_futures(self):
        value=self.duplicated()
        value["choices"][1]["steps"]=deepcopy(value["choices"][0]["steps"])
        with self.assertRaisesRegex(V110IdentityError,
                                    "SAME_SUBSTANTIVE_FUTURE"):
            recover_host_branch_identity(value)
        self.assertEqual(value["choices"][0]["id"],value["choices"][1]["id"])

    def test_invalid_conditions_are_never_normalized_away(self):
        for bad in (
            {"choices":[]},
            {"choices":[{"id":"path_a","steps":[]},
                        {"id":"path_a","steps":[]}]},
            {"choices":[{"id":"path a","steps":[{}]},
                        {"id":"path a","steps":[{"id":"a"}]}]},
        ):
            with self.assertRaises(V110IdentityError):
                recover_host_branch_identity(bad)
        valid=simple_branches()
        with self.assertRaisesRegex(V110IdentityError,"NOT_A_DUPLICATE"):
            recover_host_branch_identity(valid)

    def test_duplicate_horizon_does_not_trick_new_factjournal_or_write(self):
        fixture=V105TrueWritingEntrypoint(
            "test_f_plans_before_prose_and_exports_future_and_real_open_debts")
        fixture.setUp()
        try:
            sample=json.loads(foresight_plan())
            sample["horizon"]["choices"][1]["id"]=sample["horizon"]["choices"][0]["id"]
            model_answers=replies()
            model_answers[0]=json.dumps(sample,ensure_ascii=False)
            doc,calls=fixture.run_f(
                model_answers,folder="v110-recovered",
                facts={"power:station":"on"})
            self.assertEqual(len(calls),4)
            ch=doc["chapters"][0]
            self.assertFalse(ch["accepted"])
            self.assertEqual(doc["canonical_fact_writes"],0)
            raw=json.loads(Path(ch["v105_raw_chapter_plan"]).read_text("utf8"))
            self.assertEqual(raw,sample)
            original_prose=Path(ch["candidate"]).read_text("utf8")
            self.assertGreater(len(original_prose),100)
            audit=json.loads(Path(ch["v110_branch_identity_receipt"]).read_text("utf8"))
            self.assertEqual(audit["receipt_sha256"],digest(
                {k:v for k,v in audit.items() if k!="receipt_sha256"}))
            self.assertTrue(ch["v110_only_software_labels_changed"])
            recovery=json.loads(Path(ch["v105_horizon_plan"]).read_text("utf8"))
            self.assertEqual(recovery["branches"][0]["branch_id"],"wf110_branch_01")
            self.assertNotIn("文学水平已证实",str(recovery))
        finally:
            fixture.tearDown()

    def test_identical_future_steps_still_fail_before_prose_without_retry(self):
        fixture=V105TrueWritingEntrypoint(
            "test_f_plans_before_prose_and_exports_future_and_real_open_debts")
        fixture.setUp()
        try:
            sample=json.loads(foresight_plan())
            sample["horizon"]["choices"][1]["id"]=sample["horizon"]["choices"][0]["id"]
            sample["horizon"]["choices"][1]["steps"]=deepcopy(
                sample["horizon"]["choices"][0]["steps"])
            with patch("writerforge.writing_assist.local_chat_completion",
                       return_value=json.dumps(sample,ensure_ascii=False)) as model:
                with self.assertRaisesRegex(WritingExecutionError,
                                            "WF110_SAME_SUBSTANTIVE_FUTURE"):
                    AutonomousWriting(fixture.assist).run(
                        outline=OUTLINE,chapter_goals=GOALS,
                        output_dir=fixture.root/"v110-identical",
                        draft_mode="foresight_rolling",
                        frozen_turn_outlines=(json.dumps(
                            turns(),ensure_ascii=False),))
            self.assertEqual(model.call_count,1)
            self.assertEqual(len(list((fixture.root/"v110-identical").rglob(
                "*-raw-plan.json"))),1)
            self.assertFalse(list((fixture.root/"v110-identical").rglob(
                "candidate.txt")))
        finally:
            fixture.tearDown()


if __name__=="__main__":
    unittest.main()
