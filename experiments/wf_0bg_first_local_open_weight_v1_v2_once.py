"""WF 0.BG: real, FREE local open-weight writer trial; at most four outputs.

This is an intentionally SMALL, exploratory CPU model, NOT DeepSeek/GLM,
NOT an independent literary blind review, NOT a provider-authenticated wire
or production Skill advancement. Frozen 0.BE inputs only; no private corpus,
Canon or credentials. Fail closed on changed GGUF weights and partial outputs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import time

from experiments.wf_0be_v1_v2_preflight_only import build_preflight, canonical

MODEL_ID = "bartowski/Qwen_Qwen3-0.6B-GGUF"
MODEL_REVISION = "f9184d8b4c371cb52af5b8cb3d38e55e3cf0f4a0"
MODEL_FILENAME = "Qwen_Qwen3-0.6B-Q4_K_M.gguf"
MODEL_SHA256 = "9acfc1e001311f34b4252001b626f2e466d592a42065f66571bff3790d4e1b14"
MODEL_URL = (f"https://huggingface.co/{MODEL_ID}/resolve/"
             f"{MODEL_REVISION}/{MODEL_FILENAME}")
CASE_IDS = ("quiet-household-pause", "asynchronous-tool-return")
TRIAL_ID = "wf0bg-new-local-qwen3-06b-preview-20261027"
OUTPUT = Path("wf0bg_local_cpu_first_host_four_original_model_outputs")
FIXED_SEED = 20261027
MAX_GENERATION_TOKENS = 224
MODEL_CONTEXT_WINDOW = 3072
EXPECTED_CALLS = len(CASE_IDS) * 2


def sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _persist_once(path: Path, raw: bytes) -> None:
    # Never rewrite any source/model result or silently append later.
    with path.open("xb") as fh:
        fh.write(raw)


def prepare_inputs() -> dict:
    """Use the exact source-locked 0.BE v1/v2 arm inputs, never old 0.AY tasks."""
    frozen = build_preflight()
    chosen = [p for p in frozen["envelopes"] if p["case_id"] in CASE_IDS]
    if len(chosen) != EXPECTED_CALLS:
        raise RuntimeError("WF0BG_FROZEN_ARM_COUNT_CHANGED")
    items = []
    for i, e in enumerate(chosen):
        if e["case_id"] not in CASE_IDS or e["arm"] not in ("v1", "v2"):
            raise RuntimeError("WF0BG_UNEXPECTED_SOURCE_OR_OLD_TRIAL")
        if e["max_completion_tokens"] != 1800 or e["prospective"] is not True:
            raise RuntimeError("WF0BG_0BE_SOURCE_ENVELOPE_CHANGED")
        # Instruction prefix is identical across arms, only the protected
        # capsule cognitive procedure differs; no grader or expected answers.
        prompt = (
            "<|im_start|>system\n" + e["system_instruction"] + "\n"
            "<|im_end|>\n<|im_start|>user\n"
            + "请阅读下面的独立虚构前文，直接续写，不复述指令。\n"
            + "\n".join(e["source_segments"]) + "\n"
            + e["task"] + "\n"
            + "你可使用下列认知习惯辅助判断已发生、未知或未执行事项，"
              "但由你本人决定情节与叙事节奏：\n"
            + "\n".join(e["cognitive_procedure"])
            + "\n/no_think\n<|im_end|>\n<|im_start|>assistant\n"
        )
        raw = prompt.encode("utf-8")
        items.append({
            "index": i, "case_id": e["case_id"], "arm": e["arm"],
            "envelope_sha256": sha(canonical(e)),
            "source_sha256": e["source_sha256"],
            "task_sha256": e["task_sha256"],
            "capsule_sha256": e["capsule_sha256"],
            "prompt_sha256": sha(raw),
            "prompt": prompt,
            "generation_max_tokens": MAX_GENERATION_TOKENS,
            "seed": FIXED_SEED,
        })
    pairs = {}
    for item in items:
        pairs.setdefault(item["case_id"], set()).add(item["arm"])
    if set(pairs) != set(CASE_IDS) or any(arms != {"v1", "v2"} for arms in pairs.values()):
        raise RuntimeError("WF0BG_INCOMPLETE_FROZEN_PAIRS")
    return {
        "format": "wf.0bg.local-model-paired-preflight.v1",
        "trial_id": TRIAL_ID,
        "inherited_case_pack_sha256": frozen["frozen_case_pack_sha256"],
        "v1_capsule_sha256": frozen["v1_capsule_sha256"],
        "v2_capsule_sha256": frozen["v2_capsule_sha256"],
        "model_repo": MODEL_ID, "model_revision": MODEL_REVISION,
        "model_file_sha256": MODEL_SHA256,
        "model_url": MODEL_URL,
        "local_cpu_model_only": True,
        "new_paid_provider_calls_authorized": 0,
        "new_paid_provider_calls": 0,
        "actual_cpu_model_generations": 0,
        "production_skill_promotion": False,
        "independent_literary_gain_proven": False,
        "author_prose_remains_unaccepted": True,
        "items": items,
    }


def execute_once(*, model_path: Path, output: Path = OUTPUT,
                 fake_engine_factory=None, fixture_mode: bool = False) -> dict:
    """One bounded local inference per frozen arm, with a truthful raw trace.

    fake_engine_factory is test-only and MUST be passed with fixture_mode=True;
    such records are labeled SYNTHETIC, never passed off as real model work.
    """
    if output.exists():
        raise FileExistsError("WF0BG_RESULT_ALREADY_EXISTS_NO_REPEAT")
    preflight = prepare_inputs()
    weights = Path(model_path)
    if not fixture_mode:
        if fake_engine_factory is not None:
            raise PermissionError("WF0BG_FAKE_ENGINE_CANNOT_CLAIM_REAL_INFERENCE")
        if not weights.is_file() or sha(weights.read_bytes()) != MODEL_SHA256:
            raise PermissionError("WF0BG_MODEL_WEIGHTS_NOT_SHA_PINNED")
        from llama_cpp import Llama
        factory = Llama
        source_kind = "LOCAL_OPEN_WEIGHT_REAL_MODEL"
    else:
        if not callable(fake_engine_factory):
            raise PermissionError("WF0BG_SYNTHETIC_FIXTURE_ENGINE_REQUIRED")
        factory = fake_engine_factory
        source_kind = "SYNTHETIC_TEST_ONLY"

    output.mkdir(parents=True, exist_ok=False)
    # Write the immutable invocation plan BEFORE generating anything, so
    # interrupted work can be audited and NEVER inferred to have completed.
    _persist_once(output/"PREPARED.json", canonical(preflight))
    stripped = [{k:v for k,v in it.items() if k!="prompt"}
                for it in preflight["items"]]
    status = {
        "format": "wf.0bg.local-open-weight-inference-ledger.v1",
        "trial_id": TRIAL_ID, "status": "RUNNING",
        "source_kind": source_kind,
        "host_kind": "one_cpu_local_llama_runtime_not_independent_agent",
        "model_file_sha256": MODEL_SHA256 if not fixture_mode else None,
        "model_revision": MODEL_REVISION,
        "preflight_sha256": sha(canonical(preflight)),
        "planned_arms": stripped,
        "max_actual_calls": EXPECTED_CALLS,
        "completed_calls": 0,
        "failed_calls": 0,
        "records": [],
        "literary_quality_proven": False,
        "independent_reader_votes": 0,
        "human_reader_blindness_proven": False,
        "auto_activate_skill": False,
        "new_paid_model_requests": 0,
        "original_0ay_glm_retried": False,
    }
    def save():
        # Mutable STATUS is an explicit ledger, each per-arm raw output is
        # immutable. Never infer success from existence of a partial status.
        (output/"STATUS.json").write_bytes(canonical(status))

    save()
    instance = None
    try:
        instance = factory(
            model_path=str(weights), n_ctx=MODEL_CONTEXT_WINDOW,
            n_threads=2, n_gpu_layers=0, verbose=False)
        for i, item in enumerate(preflight["items"]):
            started = time.perf_counter()
            try:
                answer = instance.create_completion(
                    prompt=item["prompt"],
                    max_tokens=MAX_GENERATION_TOKENS,
                    temperature=0.0, top_p=1.0,
                    seed=FIXED_SEED, stop=["<|im_end|>"],
                )
                response_text = answer["choices"][0]["text"]
                usage = answer["usage"]
                stop_reason = answer["choices"][0]["finish_reason"]
                if (type(response_text) is not str or
                        not response_text.strip() or
                        stop_reason not in ("stop", "length") or
                        not isinstance(usage, dict) or
                        any(type(usage.get(k)) is not int or usage[k] < 0
                            for k in ("prompt_tokens","completion_tokens","total_tokens")) or
                        usage["prompt_tokens"] + usage["completion_tokens"] !=
                        usage["total_tokens"] or
                        usage["completion_tokens"] > MAX_GENERATION_TOKENS):
                    raise RuntimeError("WF0BG_INCOMPLETE_REAL_LOCAL_MODEL_RESULT")
                raw = canonical(answer)
                _persist_once(output/f"output_{i:02d}_{item['case_id']}_{item['arm']}.json",
                              raw)
                status["records"].append({
                    "case_id":item["case_id"], "arm":item["arm"],
                    "prompt_sha256":item["prompt_sha256"],
                    "source_sha256":item["source_sha256"],
                    "capsule_sha256":item["capsule_sha256"],
                    "raw_local_completion_sha256":sha(raw),
                    "authored_text_sha256":sha(response_text.encode("utf8")),
                    "finish_reason":stop_reason,
                    "prompt_tokens":usage["prompt_tokens"],
                    "completion_tokens":usage["completion_tokens"],
                    "total_tokens":usage["total_tokens"],
                    "local_elapsed_seconds":round(time.perf_counter()-started,3),
                    "source_kind":source_kind,
                    "no_provider_wire_claim":True,
                })
                status["completed_calls"]+=1
                save()
            except Exception as exc:
                status["failed_calls"]+=1
                status["status"]="DORMANT_LOCAL_MODEL_ERROR_NO_RETRY"
                status["failure_class"]=type(exc).__name__
                save()
                raise
        status["status"]="LOCAL_CPU_SOURCE_VERIFIED_UNGRADED"
        save()
        return status
    finally:
        # model instance is deliberately torn down with this run.
        del instance


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--output",type=Path,default=OUTPUT)
    args=p.parse_args()
    result=execute_once(model_path=args.model, output=args.output)
    print("WF0BG_REAL_LOCAL_TWO_PAIRS "+json.dumps({
        "status":result["status"],
        "completed_calls":result["completed_calls"],
        "source_kind":result["source_kind"],
        "new_paid_model_requests":0,
        "literary_quality_proven":False,
    },sort_keys=True), flush=True)
