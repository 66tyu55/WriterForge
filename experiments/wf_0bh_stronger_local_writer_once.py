"""WF 0.BH: source-locked stronger CPU-only Qwen2.5 3B writer A/B.

Exactly three NEW 0.BE pre-registered cases, six actual fresh completions,
zero provider API calls. No retry; no literary verdict, no human reader,
no new skill promotion. A local llama.cpp engine is one runtime, not two
independent Agent hosts or a signed original remote-provider response.

Weights are pinned to an actual Hugging Face file commit and FULL 1.93GB
SHA256 (not a repository README checksum or a floating "main" branch).
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

from experiments.wf_0be_v1_v2_preflight_only import build_preflight, canonical

MODEL_ID="bartowski/Qwen2.5-3B-Instruct-GGUF"
MODEL_REVISION="254600e47ea694216f6108325376ce5b35d456a1"
MODEL_FILENAME="Qwen2.5-3B-Instruct-Q4_K_M.gguf"
MODEL_SHA256="9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94"
MODEL_URL=(f"https://huggingface.co/{MODEL_ID}/resolve/"
           f"{MODEL_REVISION}/{MODEL_FILENAME}")
MODEL_LICENSE="qwen-research"
CASE_IDS=("purposeful-second-attempt",
          "bounded-eyewitness",
          "custody-without-fulfillment")
TRIAL_ID="wf0bh-fresh-local-qwen25-3b-no-api-20261027"
OUTPUT=Path("wf0bh_real_qwen25_3b_three_fresh_pairs")
FIXED_SEED=20261027
MAX_COMPLETION_TOKENS=320
MODEL_CONTEXT_WINDOW=4096
MAX_CALLS=len(CASE_IDS)*2


def _digest(raw:bytes)->str:
    return sha256(raw).hexdigest()


def _file_sha256(path:Path)->str:
    """Never read 1.93 GB into Python memory just for provenance checking."""
    d=sha256()
    with path.open("rb") as stream:
        while True:
            chunk=stream.read(1024*1024)
            if not chunk:break
            d.update(chunk)
    return d.hexdigest()


def _write_once(path:Path,data:bytes)->None:
    with path.open("xb") as f:
        f.write(data)


def prepare_stronger_inputs()->dict:
    """Identical actual story/task/model context within each v1-v2 pair.

    Only cognitive_procedure differs. Uses published original 0.BE frozen
    case pack: no new hidden test cases, no literary grader answers, no
    historical 0.AY radio model calls.
    """
    pack=build_preflight()
    items=[]
    for e in pack["envelopes"]:
        if e["case_id"] not in CASE_IDS:
            continue
        if (e["arm"] not in ("v1","v2") or
                e.get("format")!="wf.0be.prepared-author-input.v1" or
                e["prospective"] is not True or
                e["max_completion_tokens"]!=1800 or
                e["model"]!="UNSPECIFIED_REQUIRES_FRESH_EXPLICIT_AUTHORIZATION"):
            raise ValueError("WF0BH_INVALID_FROZEN_SOURCE_ENVELOPE")
        # Qwen2.5's instruct turn format (it does NOT use the Qwen3
        # /no_think convention from the smaller 0.BG local runner).
        prompt=(
            "<|im_start|>system\n"
            +e["system_instruction"]
            +"<|im_end|>\n<|im_start|>user\n"
            +"以下是独立原创文学前文。只参考人物实际知道的情况：\n"
            +"\n".join(e["source_segments"])
            +"\n续写任务："+e["task"]
            +"\n可参考以下认知过程，但不允许代替你的文学判断：\n"
            +"\n".join(e["cognitive_procedure"])
            +"\n直接写120至220字的后续正文，避免解释提示词、重复原段或列提纲。"
            +"\n<|im_end|>\n<|im_start|>assistant\n"
        )
        items.append({
            "case_id":e["case_id"],"arm":e["arm"],
            "frozen_envelope_sha256":_digest(canonical(e)),
            "source_sha256":e["source_sha256"],
            "task_sha256":e["task_sha256"],
            "capsule_sha256":e["capsule_sha256"],
            "source_segments":e["source_segments"],"task":e["task"],
            "system":e["system_instruction"],
            "cognitive_procedure":e["cognitive_procedure"],
            "prompt":prompt,
            "prompt_sha256":_digest(prompt.encode("utf8")),
            "fixed_seed":FIXED_SEED,
            "max_completion_tokens":MAX_COMPLETION_TOKENS,
        })
    if len(items)!=MAX_CALLS:
        raise RuntimeError("WF0BH_SIX_FROZEN_ARMS_REQUIRED")
    for cid in CASE_IDS:
        two=[x for x in items if x["case_id"]==cid]
        if (len(two)!=2 or {x["arm"] for x in two}!={"v1","v2"} or
            any(two[0][k]!=two[1][k] for k in
                ("source_sha256","task_sha256","source_segments",
                 "task","system","fixed_seed","max_completion_tokens")) or
            two[0]["cognitive_procedure"]==two[1]["cognitive_procedure"]):
            raise RuntimeError("WF0BH_MISMATCHED_SOURCE_AUTHOR_BUDGET")
    return {
        "format":"wf.0bh.stronger-local-author-preflight.v1",
        "trial_id":TRIAL_ID,
        "frozen_0be_pack_sha256":pack["frozen_case_pack_sha256"],
        "v1_capsule_sha256":pack["v1_capsule_sha256"],
        "v2_capsule_sha256":pack["v2_capsule_sha256"],
        "model_id":MODEL_ID,
        "model_revision":MODEL_REVISION,
        "model_sha256":MODEL_SHA256,
        "model_url":MODEL_URL,
        "model_license":MODEL_LICENSE,
        "planned_new_paid_api_calls":0,
        "old_paid_model_calls":0,
        "actual_local_model_calls_so_far":0,
        "quality_winner":None,
        "reader_votes":0,
        "independent_literary_gain_proven":False,
        "all_written_prose_is_unaccepted":True,
        "old_glm_429_retried":False,
        "read_private_r2":False,
        "modify_canon":False,
        "items":items,
    }


def execute_stronger_once(*,model_path:Path,output:Path=OUTPUT,
                          engine_factory=None,fixture_mode:bool=False)->dict:
    """One-shot local inference. Output directory is NEVER overwritten.

    For tests only, a fake engine can be provided alongside explicit
    fixture_mode=True. Such results are never mislabeled REAL.
    """
    if output.exists():
        raise FileExistsError("WF0BH_RESULT_ALREADY_EXISTS_NO_REPEAT")
    plan=prepare_stronger_inputs()
    source=Path(model_path)
    if not fixture_mode:
        if engine_factory is not None:
            raise PermissionError("WF0BH_MOCK_IS_NOT_REAL")
        if not source.is_file() or _file_sha256(source)!=MODEL_SHA256:
            raise PermissionError("WF0BH_MODEL_WEIGHTS_SHA_MISMATCH")
        from llama_cpp import Llama
        factory=Llama
        evidence_class="REAL_LOCAL_OPEN_WEIGHT_GENERATION"
    else:
        if not callable(engine_factory):
            raise PermissionError("WF0BH_FAKE_ENGINE_NOT_AN_EXPLICIT_FIXTURE")
        factory=engine_factory
        evidence_class="SYNTHETIC_TEST_ONLY"
    output.mkdir(parents=True,exist_ok=False)
    _write_once(output/"FROZEN_INPUTS.json",canonical(plan))
    state={
        "format":"wf.0bh.source-locked-stronger-local-ledger.v1",
        "trial_id":TRIAL_ID,
        "status":"RUNNING",
        "evidence_class":evidence_class,
        "model_id":MODEL_ID,
        "model_revision":MODEL_REVISION,
        "model_sha256":MODEL_SHA256 if not fixture_mode else None,
        "engine":"llama-cpp-python==0.3.16" if not fixture_mode else "synthetic_test_engine",
        "preflight_sha256":_digest(canonical(plan)),
        "max_calls":MAX_CALLS,
        "completed_calls":0,
        "failed_calls":0,
        "records":[],
        "new_paid_provider_calls":0,
        "trusted_independent_reader_votes":0,
        "independent_literary_gain_proven":False,
        "production_skill_activation":False,
        "actual_other_agent_hosts_verified":0,
        "old_glm_429_retried":False,
        "prompt_and_completion_tokens_reported_by_local_engine":True,
        "all_outputs_unaccepted_author_work":True,
    }
    def save():
        (output/"STATUS.json").write_bytes(canonical(state))
    save()
    engine=None
    try:
        engine=factory(model_path=str(source),n_ctx=MODEL_CONTEXT_WINDOW,
                       n_threads=2,n_gpu_layers=0,verbose=False)
        for index,item in enumerate(plan["items"]):
            beginning=time.perf_counter()
            reply=engine.create_completion(
                prompt=item["prompt"],seed=FIXED_SEED,
                max_tokens=MAX_COMPLETION_TOKENS,
                temperature=0.0,top_p=1.0,
                stop=["<|im_end|>","</s>"],
            )
            if not isinstance(reply,dict):
                raise RuntimeError("WF0BH_MODEL_RETURNED_NO_REAL_RAW_OUTPUT")
            try:
                answer=reply["choices"][0]["text"]
                finish=reply["choices"][0]["finish_reason"]
                usage=reply["usage"]
                total=usage["total_tokens"]
                prompt_t=usage["prompt_tokens"]
                completion_t=usage["completion_tokens"]
            except (TypeError,IndexError,KeyError) as exc:
                raise RuntimeError("WF0BH_MISSING_LOCAL_MODEL_WIRE_OR_USAGE") from exc
            if (type(answer) is not str or not answer.strip() or
                finish not in ("stop","length") or
                any(type(k) is not int or k<=0 for k in
                    (total,prompt_t,completion_t)) or
                total!=prompt_t+completion_t or
                completion_t>MAX_COMPLETION_TOKENS):
                raise RuntimeError("WF0BH_UNTRUSTED_OR_TRUNCATED_LOCAL_RESULT")
            raw=canonical(reply)
            filename=f"output_{index:02d}_{item['case_id']}_{item['arm']}.json"
            _write_once(output/filename,raw)
            state["records"].append({
                "case_id":item["case_id"],
                "arm":item["arm"],
                "file":filename,
                "prompt_sha256":item["prompt_sha256"],
                "source_sha256":item["source_sha256"],
                "task_sha256":item["task_sha256"],
                "capsule_sha256":item["capsule_sha256"],
                "original_local_completion_sha256":_digest(raw),
                "authored_text_sha256":_digest(answer.encode("utf8")),
                "actual_prompt_tokens":prompt_t,
                "actual_completion_tokens":completion_t,
                "actual_total_tokens":total,
                "finish_reason":finish,
                "generation_capped_at_limit":finish=="length",
                "local_elapsed_seconds":round(time.perf_counter()-beginning,3),
                "not_provider_http_wire":True,
                "evidence_class":evidence_class,
            })
            state["completed_calls"]+=1
            save()
        state["status"]=(
            "SYNTHETIC_FIXTURE_COMPLETE_UNGRADED" if fixture_mode
            else "LOCAL_STRONGER_MODEL_COMPLETED_UNGRADED"
        )
        save()
        return state
    except Exception as exc:
        state["status"]="DORMANT_CPU_HOST_ERROR_NO_RETRY"
        state["failed_calls"]+=1
        state["failure_class"]=type(exc).__name__
        save()
        raise
    finally:
        del engine


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--model",required=True,type=Path)
    parser.add_argument("--output",type=Path,default=OUTPUT)
    args=parser.parse_args()
    result=execute_stronger_once(model_path=args.model,output=args.output)
    print("WF0BH_REAL_3B_LOCAL_AUTHOR "+
          json.dumps({
              "completed_calls":result["completed_calls"],
              "evidence_class":result["evidence_class"],
              "status":result["status"],
              "new_paid_provider_calls":0,
              "independent_literary_gain_proven":False,
          },sort_keys=True),flush=True)
