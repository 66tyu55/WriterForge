"""Single user-authorized, bounded second experiment for two INCOMPLETE models.

This is not a silent retry of HTTP errors. First real three-model run proved
GLM-5.3 and Kimi K2.6 each reached finish_reason=length at max_tokens=1450.
One new provider request sequence per model uses documented thinking-aware
parameters and explicit output caps. Model-generated original/decision/edit
wire remains unmodified, never gets graded or promoted to literary LEARN.
No DeepSeek rerun, R2, Canon, Railway or deployment.
"""
from pathlib import Path
import json
import os
import sys

from experiments import wf_three_existing_writer_models_real_20261024 as base

OUTPUT=Path("wf_discovery_two_model_length_followup_20261024")
FOLLOWUPS={
    "glm-5.3":{
        "write":4500,"decide":1500,"edit":2800,
    },
    "kimi-k2.6":{
        "write":2600,"decide":900,"edit":2000,
    },
}
assert sum(FOLLOWUPS["glm-5.3"].values())==8800
assert sum(FOLLOWUPS["kimi-k2.6"].values())==5500
MAX_NEW_CALLS=6


def main():
    token=os.environ.get("DISCOVERY_API_KEY")
    OUTPUT.mkdir(parents=True,exist_ok=False)
    base.OUTPUT=OUTPUT
    if not isinstance(token,str) or len(token)<12:
        state={
            "status":"DISCOVERY_EXISTING_KEY_UNAVAILABLE",
            "actual_calls":0,"max_calls":MAX_NEW_CALLS,
            "previous_real_probe_run":40094106486,
            "no_deepseek_retest":True,
            "zero_training_or_canon":True,
        }
        base.save_json(OUTPUT/"STATUS.json",state)
        print(json.dumps(state,ensure_ascii=False),flush=True)
        return 0
    try:
        availability=base.discover_models(token)
    except Exception as error:
        availability=set()
        print(json.dumps({
            "stage":"RECOVERY_AUTHENTIC_DISCOVERY_MODELS_FAILED",
            "error_code":base.safe_exception(error),
            "no_generation_billed":True},ensure_ascii=False),flush=True)
    results=[]
    for name,options in FOLLOWUPS.items():
        if name not in availability:
            results.append({
                "model":name,"status":"NOT_ON_CURRENT_AUTHENTIC_MODEL_LIST",
                "calls_attempted":0})
        else:
            results.append(base.test_one_model(
                name,"discovery",token,provider_token_caps=options))
    output={
        "format":"wf.real-two-discovery-length-followup-20261024.v1",
        "status":"ACTUAL_FOLLOWUP_FINISHED",
        "original_three_model_run":40094106486,
        "original_finish_reason":"length",
        "same_original_seed_sha256":base.h(base.SEED),
        "same_write_and_ai_self-review_prompts":True,
        "models_attempted":list(FOLLOWUPS),
        "provider_tuning":{
            "glm-5.3":"reasoning_effort_low",
            "kimi-k2.6":"thinking_type_disabled",
        },
        "requested_output_caps":FOLLOWUPS,
        "actual_calls":sum(r.get("calls_attempted",0) for r in results),
        "maximum_new_calls":MAX_NEW_CALLS,
        "previous_calls_not_refunded_or_reinterpreted":4,
        "no_automatic_network_retries":True,
        "no_deepseek_rerun":True,
        "no_training_or_R2_or_canon_writes":True,
        "only_original_same_writer_edits_if_it_opted_in":True,
        "literary_quality_independently_verified":False,
        "results":[{
            k:v for k,v in row.items() if k not in (
                "original_preview","final_prose_preview",
                "ai_choice_receipt","edit_receipt","calls",
                "ai_why_now","ai_risk_if_unchanged",
                "ai_intended_reader_effect","ai_source_quote")}
            for row in results],
    }
    base.save_json(OUTPUT/"STATUS.json",output)
    print(json.dumps({
        "stage":"DONE_TWO_PROVIDER_COMPLETION_FOLLOWUP",
        "calls":output["actual_calls"],"max":MAX_NEW_CALLS,
        "outcomes":[[r["model"],r["status"],r.get("ai_choice")]
                    for r in results],
        "no_literary_score":True,
    },ensure_ascii=False),flush=True)
    return 0


if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(json.dumps({
            "stage":"TWO_PROVIDER_FOLLOWUP_BLOCKED",
            "error_code":base.safe_exception(error),
            "partial_provider_wires_not_overwritten":True,
        },ensure_ascii=False),flush=True)
        sys.exit(2)
