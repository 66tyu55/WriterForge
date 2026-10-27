"""WF 0.BH fail-first: real stronger local author host, source frozen & bounded.

Every callback below is SYNTHETIC_TEST_ONLY; real Qwen2.5 3B GGUF is invoked
separately by a limited GitHub CPU job ONLY after its full published SHA256
is verified. No previous GLM 429 retries or private user prose.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from experiments.wf_0bh_stronger_local_writer_once import (
    prepare_stronger_inputs, execute_stronger_once,
    MODEL_SHA256, MODEL_REVISION, MODEL_ID, MODEL_URL,
    CASE_IDS, FIXED_SEED, MAX_CALLS, MAX_COMPLETION_TOKENS
)


class SyntheticEngine:
    calls = []
    fail_at = None

    def __init__(self, **kwargs):
        self.__class__.calls=[]
        self.__class__.constructor_args=kwargs

    def create_completion(self, **kwargs):
        i=len(self.calls)
        self.calls.append(kwargs)
        if i==self.fail_at:
            raise RuntimeError("fixture-mock-inference-failed")
        text=f"FAKE-OUTPUT-{i}: mock prose is not a real author model response."
        return {
            "choices":[{"text":text,"index":0,"finish_reason":"stop"}],
            "usage":{"prompt_tokens":220+i,"completion_tokens":32,
                     "total_tokens":252+i},
            "created":1234567890,
            "id":f"fake-{i}",
            "object":"text_completion",
            "model":"MOCK"
        }


class WF0BHStrongLocalWriterPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.root=Path(self.tmp.name)
        SyntheticEngine.fail_at=None

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_fresh_cases_exactly_three_distinct_pairs_not_old_0bg(self):
        data=prepare_stronger_inputs()
        self.assertEqual(data["format"],"wf.0bh.stronger-local-author-preflight.v1")
        self.assertEqual(len(data["items"]),MAX_CALLS)
        self.assertEqual(MAX_CALLS,6)
        self.assertEqual(len(CASE_IDS),3)
        self.assertEqual(set(x["case_id"] for x in data["items"]),set(CASE_IDS))
        self.assertNotIn("quiet-household-pause",CASE_IDS)
        self.assertNotIn("asynchronous-tool-return",CASE_IDS)
        self.assertNotIn("flood-radio",json.dumps(data,ensure_ascii=False))
        self.assertEqual(data["model_sha256"],MODEL_SHA256)
        self.assertEqual(data["model_revision"],MODEL_REVISION)
        self.assertEqual(data["model_url"],MODEL_URL)
        self.assertEqual(data["planned_new_paid_api_calls"],0)
        self.assertEqual(data["quality_winner"],None)
        self.assertEqual(data["reader_votes"],0)
        self.assertTrue(data["all_written_prose_is_unaccepted"])

    def test_matched_pair_only_changes_cognitive_procedure(self):
        pre=prepare_stronger_inputs()
        by={}
        for item in pre["items"]:
            by.setdefault(item["case_id"],{})[item["arm"]]=item
        for cid, arms in by.items():
            self.assertEqual(set(arms),{"v1","v2"})
            a,b=arms["v1"],arms["v2"]
            self.assertEqual(a["source_sha256"],b["source_sha256"])
            self.assertEqual(a["task_sha256"],b["task_sha256"])
            self.assertEqual(a["fixed_seed"],b["fixed_seed"])
            self.assertEqual(a["max_completion_tokens"],b["max_completion_tokens"])
            self.assertEqual(a["max_completion_tokens"],MAX_COMPLETION_TOKENS)
            self.assertEqual(a["source_segments"],b["source_segments"])
            self.assertEqual(a["task"],b["task"])
            self.assertEqual(a["system"],b["system"])
            self.assertNotEqual(a["cognitive_procedure"],b["cognitive_procedure"])
            self.assertNotEqual(a["prompt_sha256"],b["prompt_sha256"])
            self.assertTrue(a["prompt"].startswith("<|im_start|>system"))
            self.assertTrue(b["prompt"].endswith("<|im_start|>assistant\n"))
            self.assertNotIn("risk",json.dumps(a,ensure_ascii=False))
            self.assertNotIn("correct_answer",json.dumps(b,ensure_ascii=False))

    def test_real_inference_requires_actual_sha_pinned_weights(self):
        dest=self.root/"new"
        with self.assertRaisesRegex(PermissionError,"WEIGHTS_SHA_MISMATCH"):
            execute_stronger_once(model_path=self.root/"absent.gguf",output=dest)
        self.assertFalse(dest.exists())

    def test_fixture_cannot_masquerade_as_real_model(self):
        dest=self.root/"out"
        with self.assertRaisesRegex(PermissionError,"MOCK_IS_NOT_REAL"):
            execute_stronger_once(model_path=self.root/"mock.gguf",output=dest,
                                  engine_factory=SyntheticEngine)
        self.assertFalse(dest.exists())

    def test_offline_fixture_atomic_outputs_with_explicit_false_quality(self):
        dest=self.root/"done"
        result=execute_stronger_once(model_path=self.root/"mock.gguf",output=dest,
                                     engine_factory=SyntheticEngine,fixture_mode=True)
        self.assertEqual(result["status"],"SYNTHETIC_FIXTURE_COMPLETE_UNGRADED")
        self.assertEqual(result["evidence_class"],"SYNTHETIC_TEST_ONLY")
        self.assertEqual(result["completed_calls"],MAX_CALLS)
        self.assertEqual(result["failed_calls"],0)
        self.assertEqual(len(SyntheticEngine.calls),MAX_CALLS)
        self.assertFalse(result["independent_literary_gain_proven"])
        self.assertEqual(result["trusted_independent_reader_votes"],0)
        self.assertEqual(result["new_paid_provider_calls"],0)
        self.assertFalse(result["production_skill_activation"])
        self.assertEqual(len(list(dest.glob("output_*.json"))),MAX_CALLS)
        for row in result["records"]:
            file=dest/row["file"]
            self.assertEqual(sha256(file.read_bytes()).hexdigest(),
                             row["original_local_completion_sha256"])
            self.assertEqual(row["evidence_class"],"SYNTHETIC_TEST_ONLY")
            self.assertTrue(row["not_provider_http_wire"])
        with self.assertRaisesRegex(FileExistsError,"NO_REPEAT"):
            execute_stronger_once(model_path=self.root/"mock.gguf",output=dest,
                                  engine_factory=SyntheticEngine,fixture_mode=True)

    def test_one_inference_error_records_partial_and_refuses_retry(self):
        SyntheticEngine.fail_at=2
        dest=self.root/"partial"
        with self.assertRaisesRegex(RuntimeError,"fixture-mock-inference-failed"):
            execute_stronger_once(model_path=self.root/"mock.gguf",output=dest,
                                  engine_factory=SyntheticEngine,fixture_mode=True)
        state=json.loads((dest/"STATUS.json").read_text("utf8"))
        self.assertEqual(state["status"],"DORMANT_CPU_HOST_ERROR_NO_RETRY")
        self.assertEqual(state["completed_calls"],2)
        self.assertEqual(state["failed_calls"],1)
        self.assertEqual(len(list(dest.glob("output_*.json"))),2)
        self.assertEqual(state["new_paid_provider_calls"],0)
        self.assertFalse(state["production_skill_activation"])
        with self.assertRaises(FileExistsError):
            execute_stronger_once(model_path=self.root/"mock.gguf",output=dest,
                                  engine_factory=SyntheticEngine,fixture_mode=True)

    def test_no_other_providers_or_private_canon_are_in_preflight(self):
        pre=prepare_stronger_inputs()
        self.assertFalse(pre["old_glm_429_retried"])
        self.assertFalse(pre["read_private_r2"])
        self.assertFalse(pre["modify_canon"])
        self.assertEqual(pre["old_paid_model_calls"],0)
        for item in pre["items"]:
            self.assertNotIn("private",item)
            self.assertNotIn("r2",item)
            self.assertNotIn("canon",item)


if __name__=="__main__":
    unittest.main()
