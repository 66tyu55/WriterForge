"""WF 0.BG: local model runner and source ledger; NO live model in tests.

All fake-engine results are positively labeled SYNTHETIC_TEST_ONLY. The
real model is attempted only in the single isolated CPU Actions workflow,
with pinned third-party GGUF and no paid provider credentials.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from experiments.wf_0bg_first_local_open_weight_v1_v2_once import (
    prepare_inputs, execute_once, MODEL_SHA256, MODEL_URL,
    CASE_IDS, EXPECTED_CALLS, MAX_GENERATION_TOKENS,
)


class FakeLocalModel:
    calls=[]
    should_fail_on=None
    def __init__(self,**kwargs):
        self.__class__.calls=[]
    def create_completion(self,**kwargs):
        i=len(self.calls)
        self.calls.append(kwargs)
        if i==self.should_fail_on:
            raise RuntimeError("synthetic-local-cpu-failure")
        prose=f"THIS IS A SYNTHETIC MOCK COMPLETION {i}, NOT A MODEL RESPONSE."
        return {
            "choices":[{"text":prose,"finish_reason":"stop"}],
            "usage":{"prompt_tokens":110+i,"completion_tokens":32,
                     "total_tokens":142+i},
        }


class WF0BGRealModelPreconditions(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.directory=Path(self.temp.name)
        FakeLocalModel.should_fail_on=None

    def tearDown(self):
        self.temp.cleanup()

    def test_real_frozen_plan_requires_two_new_cases_and_four_original_envelopes(self):
        p=prepare_inputs()
        self.assertEqual(len(p["items"]),EXPECTED_CALLS)
        self.assertEqual(set(x["case_id"] for x in p["items"]),set(CASE_IDS))
        self.assertEqual(set(x["arm"] for x in p["items"]),{"v1","v2"})
        self.assertEqual(p["model_file_sha256"],MODEL_SHA256)
        self.assertEqual(p["model_url"],MODEL_URL)
        self.assertEqual(p["new_paid_provider_calls"],0)
        self.assertFalse(p["independent_literary_gain_proven"])
        self.assertTrue(p["local_cpu_model_only"])
        self.assertNotIn("flood-radio",json.dumps(p,ensure_ascii=False))

    def test_identical_context_and_writer_purpose_except_habit(self):
        arms={}
        for it in prepare_inputs()["items"]:
            arms.setdefault(it["case_id"],{})[it["arm"]]=it
        for name,pair in arms.items():
            a,b=pair["v1"],pair["v2"]
            self.assertEqual(a["source_sha256"],b["source_sha256"])
            self.assertEqual(a["task_sha256"],b["task_sha256"])
            self.assertEqual(a["seed"],b["seed"])
            self.assertEqual(a["generation_max_tokens"],b["generation_max_tokens"])
            self.assertEqual(a["generation_max_tokens"],MAX_GENERATION_TOKENS)
            self.assertNotEqual(a["prompt_sha256"],b["prompt_sha256"])
            self.assertIn("/no_think",a["prompt"])
            self.assertIn("/no_think",b["prompt"])
            self.assertTrue(a["prompt"].startswith("<|im_start|>system"))
            self.assertTrue(b["prompt"].endswith("<|im_start|>assistant\n"))

    def test_no_pinned_weights_blocks_actual_inference_before_output_dir(self):
        target=self.directory/"out"
        with self.assertRaisesRegex(PermissionError,"MODEL_WEIGHTS_NOT_SHA_PINNED"):
            execute_once(model_path=self.directory/"not-a-model.gguf",output=target)
        self.assertFalse(target.exists())

    def test_untrusted_fake_engine_never_runs_as_real(self):
        target=self.directory/"out"
        with self.assertRaisesRegex(PermissionError,"FAKE_ENGINE_CANNOT_CLAIM_REAL"):
            execute_once(model_path=self.directory/"fake-model.gguf",
                         output=target,fake_engine_factory=FakeLocalModel,
                         fixture_mode=False)
        self.assertFalse(target.exists())

    def test_fixture_outputs_keep_provenance_and_do_not_invent_gain(self):
        target=self.directory/"out"
        result=execute_once(model_path=self.directory/"fake-model.gguf",
                            output=target,fake_engine_factory=FakeLocalModel,
                            fixture_mode=True)
        self.assertEqual(result["status"],"LOCAL_CPU_SOURCE_VERIFIED_UNGRADED")
        self.assertEqual(result["source_kind"],"SYNTHETIC_TEST_ONLY")
        self.assertEqual(result["completed_calls"],4)
        self.assertEqual(result["failed_calls"],0)
        self.assertEqual(len(FakeLocalModel.calls),4)
        self.assertFalse(result["literary_quality_proven"])
        self.assertEqual(result["independent_reader_votes"],0)
        self.assertEqual(result["new_paid_model_requests"],0)
        self.assertEqual(len(list(target.glob("output_*.json"))),4)
        for rec in result["records"]:
            self.assertEqual(rec["source_kind"],"SYNTHETIC_TEST_ONLY")
            self.assertTrue(rec["no_provider_wire_claim"])
            name=next(target.glob(
                f"output_*_{rec['case_id']}_{rec['arm']}.json"))
            self.assertEqual(
                sha256(name.read_bytes()).hexdigest(),
                rec["raw_local_completion_sha256"])
        with self.assertRaisesRegex(FileExistsError,"NO_REPEAT"):
            execute_once(model_path=self.directory/"fake-model.gguf",
                         output=target,fake_engine_factory=FakeLocalModel,
                         fixture_mode=True)

    def test_half_failure_retains_only_completed_calls_no_rerun(self):
        target=self.directory/"out"
        FakeLocalModel.should_fail_on=1
        with self.assertRaisesRegex(RuntimeError,"synthetic-local-cpu-failure"):
            execute_once(model_path=self.directory/"fake-model.gguf",
                         output=target,fake_engine_factory=FakeLocalModel,
                         fixture_mode=True)
        status=json.loads((target/"STATUS.json").read_bytes())
        self.assertEqual(status["status"],"DORMANT_LOCAL_MODEL_ERROR_NO_RETRY")
        self.assertEqual(status["completed_calls"],1)
        self.assertEqual(status["failed_calls"],1)
        self.assertEqual(len(list(target.glob("output_*.json"))),1)
        self.assertEqual(status["independent_reader_votes"],0)
        self.assertFalse(status["literary_quality_proven"])
        self.assertEqual(status["new_paid_model_requests"],0)

    def test_no_active_or_canon_writes_in_cpu_records(self):
        p=prepare_inputs()
        self.assertFalse(p["production_skill_promotion"])
        self.assertTrue(p["author_prose_remains_unaccepted"])
        for record in p["items"]:
            self.assertNotIn("r2",record)
            self.assertNotIn("canon",record)
            self.assertNotIn("active",record)


if __name__=="__main__":
    unittest.main()
