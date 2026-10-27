"""WF 0.BE fail-first: test v1-v2 VALUE, not another quality-rule gadget.

Every case is fresh synthetic source, not the archived 0.AY paid trial. Source
and rules frozen before future provider results. This module MUST NEVER call
a model or call a fabricated literary gain a result.
"""
from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from experiments.wf_0be_v1_v2_preflight_only import (
    build_preflight, report_cost_and_verification, freeze_for_host,
    BUDGET_REQUIRED_STATUS,
)

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/"experiments/wf_0be_v1_v2_falsification_cases_20261027.json"
V1=ROOT/".agents/skills/observe-before-next-choice/capsule.json"
V2=ROOT/"experiments/wf_0bd_portable_habit_snapshots/0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10/capsule.json"
V1_SHA="42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d"
V2_SHA="0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10"


class WF0BEValueAttackPreflight(unittest.TestCase):
    def test_capsules_are_byte_pinned_and_original_v1_kept(self):
        self.assertEqual(sha256(V1.read_bytes()).hexdigest(),V1_SHA)
        self.assertEqual(sha256(V2.read_bytes()).hexdigest(),V2_SHA)
        a=json.loads(V1.read_bytes())
        b=json.loads(V2.read_bytes())
        self.assertEqual(a["revision"],1)
        self.assertEqual(b["revision"],2)
        self.assertEqual(a["lifecycle"],b["lifecycle"])
        self.assertEqual(a["lifecycle"],"SHADOW")
        self.assertEqual(a["authority"],b["authority"])
        self.assertEqual(a["stopping"],b["stopping"])

    def test_preflight_pre_registers_eight_fresh_balanced_cases(self):
        plan=build_preflight()
        self.assertEqual(plan["status"],BUDGET_REQUIRED_STATUS)
        self.assertEqual(plan["new_provider_calls"],0)
        self.assertEqual(plan["model_outputs_present"],0)
        self.assertEqual(plan["literary_improvement_proven"],False)
        self.assertEqual(len(plan["cases"]),8)
        self.assertEqual(len(plan["envelopes"]),16)
        self.assertEqual(len({c["case_id"] for c in plan["cases"]}),8)
        self.assertEqual(set(e["arm"] for e in plan["envelopes"]),{"v1","v2"})
        self.assertEqual(plan["new_paid_model_calls_authorized"],0)
        self.assertEqual(plan["prospective_total_requests_if_authorized"],16)
        self.assertTrue(all(p["source_sha256"] for p in plan["cases"]))
        self.assertTrue(all(set(p["arms"])=={"v1","v2"} for p in plan["cases"]))

    def test_each_pair_has_identical_source_task_model_and_output_cap(self):
        plan=build_preflight()
        by={}
        for row in plan["envelopes"]:
            by.setdefault(row["case_id"],{})[row["arm"]]=row
        self.assertEqual(len(by),8)
        for cid,arms in by.items():
            a,b=arms["v1"],arms["v2"]
            self.assertEqual(a["source_sha256"],b["source_sha256"])
            self.assertEqual(a["task_sha256"],b["task_sha256"])
            self.assertEqual(a["max_completion_tokens"],b["max_completion_tokens"])
            self.assertEqual(a["model"],b["model"])
            self.assertEqual(a["source_segments"],b["source_segments"])
            self.assertEqual(a["task"],b["task"])
            self.assertEqual(a["system_instruction"],b["system_instruction"])
            self.assertNotEqual(a["cognitive_procedure"],b["cognitive_procedure"])
            self.assertEqual(a["writer_retains_next_choice"],True)
            self.assertEqual(b["writer_retains_next_choice"],True)
            self.assertNotIn("risk",a)
            self.assertNotIn("risk",b)
            self.assertNotIn("correct_answer",a)
            self.assertNotIn("correct_answer",b)

    def test_input_cost_exact_not_fake_token_usage(self):
        plan=build_preflight()
        delta=plan["contract_cost"]
        self.assertEqual(delta["v1_step_1_chars"],138)
        self.assertEqual(delta["v2_step_1_chars"],417)
        self.assertEqual(delta["step_1_extra_chars"],279)
        self.assertEqual(delta["falsifier_extra_chars"],183)
        self.assertEqual(delta["contract_extra_chars"],462)
        self.assertEqual(delta["actual_prompt_tokens"],None)
        self.assertEqual(delta["actual_completion_tokens"],None)
        self.assertFalse(delta["literary_gain_verified"])
        self.assertEqual(plan["historical_glm_429_retries"],0)

    def test_no_model_auth_or_reader_ratings_stops_without_creating_results(self):
        ready=build_preflight()
        result=report_cost_and_verification(ready)
        self.assertEqual(result["disposition"],BUDGET_REQUIRED_STATUS)
        self.assertEqual(result["falsified"],False)
        self.assertEqual(result["auto_promote"],False)
        self.assertEqual(result["new_model_calls"],0)
        self.assertIsNone(result["winner_sha256"])
        self.assertEqual(result["quality_evidence"],"NONE")
        self.assertFalse(result["independent_reader_evidence"])

    def test_source_hypothesis_does_not_leak_old_radio_originals(self):
        plan=build_preflight()
        raw=json.dumps(plan,ensure_ascii=False)
        self.assertNotIn("阮知",raw)
        self.assertNotIn("沈闻",raw)
        self.assertNotIn("第四站回执号码异常",raw)
        self.assertFalse(any("flood-radio" in x["case_id"] for x in plan["cases"]))
        self.assertTrue(all(x["prospective"] for x in plan["envelopes"]))

    def test_budget_or_pretend_winner_cannot_be_injected(self):
        original=json.loads(PACK.read_text("utf8"))
        with TemporaryDirectory() as root:
            path=Path(root)/"altered.json"
            doc=json.loads(json.dumps(original))
            doc["new_paid_provider_calls_authorized"]=16
            path.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf8")
            with self.assertRaises((ValueError,PermissionError)):
                build_preflight(pack_path=path)
            doc=json.loads(json.dumps(original))
            doc["cases"][0]["case_id"]=doc["cases"][1]["case_id"]
            path.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf8")
            with self.assertRaises(ValueError):
                build_preflight(pack_path=path)
            doc=json.loads(json.dumps(original))
            doc["blind_plan"]["require_independent_reviewers"]=0
            path.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf8")
            with self.assertRaises(ValueError):
                build_preflight(pack_path=path)

    def test_can_freeze_without_network_or_replay_provider_history(self):
        with TemporaryDirectory() as d:
            target=Path(d)/"preview"
            with patch("urllib.request.urlopen",side_effect=AssertionError(
                  "NO_MODEL_OR_NETWORK_CALL_FOR_PREVIEW")):
                got=freeze_for_host(output=target)
            self.assertEqual(got["status"],BUDGET_REQUIRED_STATUS)
            self.assertTrue((target/"PREVIEW.json").exists())
            preview=json.loads((target/"PREVIEW.json").read_text("utf8"))
            self.assertEqual(preview["new_provider_calls"],0)
            self.assertTrue(preview["has_no_model_results"])
            self.assertEqual(preview["writer_model"],"UNSPECIFIED_REQUIRES_FRESH_EXPLICIT_AUTHORIZATION")
            with self.assertRaisesRegex(FileExistsError,"ALREADY_EXISTS"):
                freeze_for_host(output=target)


if __name__=="__main__":
    unittest.main()
