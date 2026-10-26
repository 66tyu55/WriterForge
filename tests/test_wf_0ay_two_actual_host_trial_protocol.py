"""0.AY: fully offline audit of the cross-host literary comparison BEFORE billing.

These tests DO NOT assert any literary winner. Two actual model families are
only tested if the exact guarded one-shot workflow has both configured keys.
"""
from __future__ import annotations

import json
from pathlib import Path
import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments import wf_0ay_two_real_hosts_portable_habit_ab_once_20261026 as trial


class PortableHabitTwoActualHostsPreflight(unittest.TestCase):
    def test_exact_two_real_provider_models_are_distinct(self):
        self.assertEqual(trial.MODELS,(("deepseek","deepseek-flash"),
                                       ("discovery","glm-5.3")))
        self.assertEqual(trial.MAX_MODEL_CALLS,8)
        self.assertEqual(trial.PER_MODEL_CALLS,4)
        self.assertEqual(trial.MAX_TOTAL_RESERVED,14400)
        self.assertEqual(trial.SCENARIOS,("flood-radio","historic-seal"))
        self.assertEqual(trial.ARMS,("control","habit"))
        self.assertFalse(trial.REGISTRATION["human_or_independent_literary_gain_proven"])
        self.assertTrue(trial.REGISTRATION["prompt_input_cost_confounded"])

    def test_offline_source_and_same_contract_for_both_host_envelopes(self):
        with TemporaryDirectory() as d:
            with patch.object(trial,"ROOT",Path(d)/"dry"):
                trial.preflight()
                root=trial.ROOT
                report=json.loads((root/"PREFLIGHT.json").read_text("utf8"))
                self.assertEqual(report["real_host_models_called"],0)
                self.assertEqual(report["prepared_control_and_habit_requests"],8)
                self.assertEqual(report["tasks"],list(trial.SCENARIOS))
                self.assertTrue(report["source_same_between_arms"])
                self.assertTrue(report[
                    "same_semantic_habit_core_in_both_adapters"])
                self.assertFalse(report["literary_quality_proven"])
                # Host differences affect transport, not the capsule itself.
                a=json.loads((root/"requests/deepseek/flood-radio/habit.json").read_text("utf8"))
                b=json.loads((root/"requests/discovery/flood-radio/habit.json").read_text("utf8"))
                self.assertEqual(a["semantic_habit_core_sha256"],
                                 b["semantic_habit_core_sha256"])
                self.assertEqual(a["source_sha256s"],b["source_sha256s"])
                self.assertEqual(a["actual_provider_input_envelope"]["adapter"],
                                 "chat_messages")
                self.assertEqual(b["actual_provider_input_envelope"]["adapter"],
                                 "plain_prompt")
                for host,_ in trial.MODELS:
                    for case in trial.SCENARIOS:
                        control=json.loads((root/"requests"/host/case/
                                            "control.json").read_text("utf8"))
                        habit=json.loads((root/"requests"/host/case/
                                          "habit.json").read_text("utf8"))
                        self.assertEqual(control["source_sha256s"],
                                         habit["source_sha256s"])
                        self.assertEqual(control["model_max_completion_tokens"],
                                         habit["model_max_completion_tokens"])
                        self.assertNotEqual(control["input_envelope_sha256"],
                                            habit["input_envelope_sha256"])

    def test_hard_eight_call_total_and_no_retries(self):
        cap=trial.OneShotCap()
        for _ in range(4):
            for host,_ in trial.MODELS:
                cap.reserve(host,trial.TOKENS_PER_REQUEST)
        self.assertEqual(cap.calls,8)
        self.assertEqual(cap.reserved,14400)
        self.assertEqual(cap.per_host,{"deepseek":4,"discovery":4})
        with self.assertRaisesRegex(trial.TrialError,"COST_CAP"):
            cap.reserve("deepseek",trial.TOKENS_PER_REQUEST)
        self.assertEqual(cap.calls,8)

    def test_failed_second_host_missing_credentials_fails_before_any_paid_model(self):
        with TemporaryDirectory() as d:
            with patch.object(trial,"ROOT",Path(d)/"never-billed"):
                with patch.dict(os.environ,{},clear=True):
                    with self.assertRaisesRegex(RuntimeError,
                                                "PARTIAL_SAVED_NO_RETRY"):
                        trial.live()
                s=json.loads((trial.ROOT/"STATUS.json").read_text("utf8"))
                self.assertEqual(s["model_calls"],0)
                self.assertEqual(s["completed"],[])
                self.assertEqual(s["per_host_paid_calls"],
                                 {"deepseek":0,"discovery":0})
                self.assertEqual(s["status"],
                                 "SAFE_PARTIAL_TWO_HOST_CROSS_TRANSFER_NO_RETRIES")
                self.assertEqual(s["failure_code"],
                                 "WF0AY_NEEDS_BOTH_AUTHORIZED_HOST_KEYS_BEFORE_PAID_CALL")
                self.assertFalse(s["literary_quality_proven"])

    def test_no_fake_quality_promotion_if_both_outputs_valid_json(self):
        result=trial._valid_result({
          "prose":"窗下的人仍在等候消息。"*10,
          "chosen_step":"她决定先核对另一处回执。",
          "still_unknown":"谁确实听到了广播仍然不明。",
        })
        self.assertTrue(result["from_actual_provider"])
        self.assertFalse(result["literary_quality_proven"])
        with self.assertRaisesRegex(trial.TrialError,
                                    "RESPONSE_SHAPE_OR_LENGTH"):
            trial._valid_result({"prose":"写得好","chosen_step":"Yes",
                                 "still_unknown":"None"})


if __name__=="__main__":
    unittest.main()
