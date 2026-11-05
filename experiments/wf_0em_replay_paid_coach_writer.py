"""Replay an actual paid, source-validated 0.EM teacher without buying it again.

Download the PREVIOUS actual Actions artifact before running. Only the two
writer A/B arms make paid requests, using the SAME DeepSeek Pro model. This is
a behavior-practice experiment, not model fine-tuning or Canon promotion.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

from writerforge.reverse_discovery_models import (
    DiscoveryCallBudget, DiscoveryModel, DiscoveryError,
)
from experiments.wf_0em_paid_intern_s2_behavior_practice import (
    EXERCISES, FROZEN_LIBRARY, FROZEN_DIGEST, PracticeError,
    load_public_sources, validate_coach, writer_prompt,
    _copied_from_source, _save,
)

PREVIOUS_RUN_ID = 42006546104
PREVIOUS_COACH_SHA256 = "e444d2c8fce5bac1ea5b833b78a1c9af108952eab8f52a2cc8def29919817021"
EXERCISE_ID = "ford-tax"
MODEL = "deepseek-v4-pro-0813"
MAX_WIRE_CALLS = 4
WRITER_MAX_TOKENS = 3500
MAX_RESERVED_OUTPUT = 14000
EXECUTION_GATE = "WF0EM_PRO_REPLAY_VERIFIED_COACH_20261105"

def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()

def verify_previous_artifact(directory: Path) -> tuple[dict, dict]:
    base=directory / "wf0em-private-synthetic"
    try:
        manifest=json.loads((base/"manifest.json").read_text("utf8"))
        coach_bytes=(base/"ford-tax-coach.json").read_bytes()
        coach_json=json.loads(coach_bytes)
    except (OSError, ValueError, TypeError) as exc:
        raise PracticeError("PREVIOUS_ACTIONS_ARTIFACT_MISSING") from exc
    if (manifest.get("reference_library")!=FROZEN_LIBRARY or
        manifest.get("reference_full_library_sha256")!=FROZEN_DIGEST or
        manifest.get("teacher_model")!="deepseek-v4-flash-0731" or
        manifest.get("same_author_model_for_both_arms")!="kimi-k2.6" or
        manifest.get("results",[{}])[0].get("source_id")!="classic-0el-4-jm" or
        manifest["results"][0].get("source_choice")!="USE" or
        manifest["results"][0].get("failure_code")!="DISCOVERY_WRITER_OUTPUT_TRUNCATED" or
        manifest["results"][0].get("coach",{}).get("sha256")!=PREVIOUS_COACH_SHA256 or
        digest(coach_bytes)!=PREVIOUS_COACH_SHA256):
        raise PracticeError("PREVIOUS_PAID_COACH_OR_PROVENANCE_CHANGED")
    sources=load_public_sources()
    reading=sources[EXERCISE_ID]
    coach=validate_coach(coach_json,reading["original"])
    if coach["use"]!="USE" or len(coach["perspectives"])!=3:
        raise PracticeError("PREVIOUS_COACH_UNUSABLE")
    return coach, reading

def offline(directory: Path) -> dict:
    coach,reading=verify_previous_artifact(directory)
    example=next(x for x in EXERCISES if x["id"]==EXERCISE_ID)
    prompts={}
    for arm in ("A","B"):
        system,question=writer_prompt(example,None if arm=="A" else coach)
        prompts[arm]={
            "prompt_sha256":sha256((system+question).encode("utf8")).hexdigest(),
            "prompt_chars":len(system+question),
        }
    return {
        "format":"wf.0em.paid-coach-writer-replay.v1",
        "state":"VALIDATED_REUSE_WITHOUT_TEACHER_CHARGE",
        "model":MODEL,
        "source_library":FROZEN_LIBRARY,
        "previous_run_id":PREVIOUS_RUN_ID,
        "previous_coach_sha256":PREVIOUS_COACH_SHA256,
        "same_writer_model_for_A_B":True,
        "max_writer_wire_calls":MAX_WIRE_CALLS,
        "max_reserved_writer_tokens":MAX_RESERVED_OUTPUT,
        "new_teacher_calls":0,
        "model_weight_training":False,
        "canon_writes":0,
        "private_novel_uploaded":False,
        "auto_accepted":False,
        "actual_prose_quality_reviewed":False,
        "source_sha256":sha256(reading["original"].encode("utf8")).hexdigest(),
        "prompts":prompts,
    }

def live(directory: Path, output_dir: Path) -> dict:
    if os.environ.get("WF0EM_REPLAY_APPROVAL")!=EXECUTION_GATE:
        raise PracticeError("EXPLICIT_REPLAY_PAID_GATE_NOT_OPEN")
    key=os.environ.get("DISCOVERY_API_KEY")
    if not key or len(key)>512:
        raise PracticeError("DISCOVERY_KEY_NOT_AVAILABLE")
    record=offline(directory)
    output_dir.mkdir(parents=True,exist_ok=True)
    coach,reading=verify_previous_artifact(directory)
    # Preserve the actual paid coach and source SHA rather than rewriting its
    # words to fit our theory. Do not promote its opinions as model truth.
    coach_text=json.dumps(coach,ensure_ascii=False,indent=2)
    record["coach_copy"]=_save(output_dir/"validated-prior-coach.json",coach_text)
    example=next(x for x in EXERCISES if x["id"]==EXERCISE_ID)
    record["phase"]="RUNNING_UNACCEPTED"
    record["writing_outputs"]={}
    budget=DiscoveryCallBudget(
        max_calls=MAX_WIRE_CALLS,
        max_reserved_output_tokens=MAX_RESERVED_OUTPUT,
    )
    writer=DiscoveryModel(
        name=MODEL,role="writer",api_key=key,budget=budget)
    manifest=output_dir/"replay-manifest.json"
    try:
        for arm in ("A","B"):
            sys_prompt,question=writer_prompt(
                example,None if arm=="A" else coach)
            result=writer.ask(
                sys_prompt,question,num_predict=WRITER_MAX_TOKENS)
            prose=result["scene"]
            if _copied_from_source(prose,reading["original"]):
                raise PracticeError("SOURCE_LONG_COPY_IN_PROSE")
            record["writing_outputs"][arm]=_save(
                output_dir/("ford-tax-"+arm+".md"),prose)
            record["last_completed_arm"]=arm
        A=record["writing_outputs"]["A"]
        B=record["writing_outputs"]["B"]
        record["length_difference_ratio"]=round(
            abs(A["characters"]-B["characters"])/
            max(A["characters"],B["characters"]),3)
        record["phase"]="COMPLETE_UNREVIEWED"
        record["blind_quality_review"]="NOT_STARTED"
        record["literary_uplift_proven"]=False
    except (DiscoveryError, PracticeError, ValueError, TypeError, KeyError) as exc:
        record["phase"]="FAILED_WITHOUT_REBUYING_COACH"
        code=str(exc)
        record["failure_code"]=code if code.startswith(
            ("DISCOVERY_","SOURCE_","MODEL_")) else type(exc).__name__
    finally:
        record["writer_wire_calls_reserved"]=budget.calls
        record["reserved_completion_tokens_not_usage"]=budget.reserved_output_tokens
        record["provider_reported_prompt_tokens"]=budget.total_prompt_tokens
        record["provider_reported_completion_tokens"]=budget.total_completion_tokens
        record["writer_response_observations"]=budget.response_observations
        manifest.write_text(json.dumps(record,ensure_ascii=False,indent=2),
                            encoding="utf8")
    return record

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--previous-dir",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path)
    parser.add_argument("--live",action="store_true")
    args=parser.parse_args()
    if not args.live:
        r=offline(args.previous_dir)
        print(json.dumps({k:r[k] for k in (
            "state","previous_run_id","previous_coach_sha256",
            "model","new_teacher_calls","max_writer_wire_calls",
            "max_reserved_writer_tokens")},ensure_ascii=False))
        return 0
    if args.output_dir is None:
        raise SystemExit("live replay requires --output-dir")
    try:
        r=live(args.previous_dir,args.output_dir)
    except PracticeError as exc:
        print(json.dumps({"status":str(exc),"model_calls":0}))
        return 2
    print(json.dumps({
        "state":r["phase"],
        "complete_arms":len(r["writing_outputs"]),
        "characters":{k:v["characters"] for k,v in r["writing_outputs"].items()},
        "writer_wire_calls_reserved":r["writer_wire_calls_reserved"],
        "reserved_output_tokens_not_usage":r["reserved_completion_tokens_not_usage"],
        "reported_prompt_tokens":r["provider_reported_prompt_tokens"],
        "reported_completion_tokens":r["provider_reported_completion_tokens"],
        "failure_code":r.get("failure_code"),
        "new_teacher_calls":0,
        "unreviewed_and_unaccepted":True,
    },ensure_ascii=False))
    return 0 if r["phase"]=="COMPLETE_UNREVIEWED" else 3

if __name__=="__main__":
    raise SystemExit(main())
