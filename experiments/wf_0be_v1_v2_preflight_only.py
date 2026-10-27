"""WF 0.BE: fresh v1-v2 VALUE falsification preflight, NEVER run a model.

This file prepares identical author-owned tasks under the archived v1 and
ungraded conversational v2. It freezes provider-neutral envelopes and shows
input character overhead, not token usage. NO literary scoring, external
provider call, model key discovery, original R2, Canon or automatic promotion.
To run actual author responses, a separate explicitly approved protocol with
new independent graders, original provider receipts and capped budget is needed.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/"experiments/wf_0be_v1_v2_falsification_cases_20261027.json"
V1=ROOT/".agents/skills/observe-before-next-choice/capsule.json"
V2=ROOT/"experiments/wf_0bd_portable_habit_snapshots/0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10/capsule.json"
V1_SHA="42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d"
V2_SHA="0d43a023bc278ac12e3165e319d2acb73dcf40c0d9af453e623c786f3b476a10"
OUTPUT=Path("wf0be_v1_v2_prospective_preflight")
BUDGET_REQUIRED_STATUS="DORMANT_NEEDS_AUTHORIZED_MODEL_AND_READER_EVIDENCE"
MODEL_UNSPECIFIED="UNSPECIFIED_REQUIRES_FRESH_EXPLICIT_AUTHORIZATION"
SYSTEM="你是中文原创文本的实际作者，保留情节、人物、行动与修改的决定权。先认真读前文，只按人物可知的事实续写，不解释写作技巧，不照抄示例。允许不行动、重试、犹豫或安静停顿，不把计划等同已发生。"
EXPECTED_CRITERIA={
    "observable causal fidelity to literal actions rather than inferred success",
    "preserve legitimate omission and deliberate repetition",
    "character bounded knowledge not converted into omniscient fact",
    "meaningful author-owned next choices",
    "prose readability and genre-appropriate pacing",
    "actual provider input/output tokens and calls rather than reserved tokens",
}
NEGATIVE_CONTROLS={
    "completed-delivery","quiet-household-pause",
    "unfulfilled-promise","plan-on-board-not-executed",
}


def canonical(value) -> bytes:
    return json.dumps(
        value,ensure_ascii=False,sort_keys=True,
        separators=(",",":"),allow_nan=False
    ).encode("utf8")


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def _read_capsules() -> tuple[dict,dict]:
    v1_raw=V1.read_bytes()
    v2_raw=V2.read_bytes()
    need(digest(v1_raw)==V1_SHA and digest(v2_raw)==V2_SHA,
         "WF0BE_CAPSULE_SHA_CHANGED")
    v1=json.loads(v1_raw)
    v2=json.loads(v2_raw)
    need(v1["revision"]==1 and v2["revision"]==2 and
         v1["lifecycle"]==v2["lifecycle"]=="SHADOW" and
         v1["authority"]==v2["authority"] and
         v1["stopping"]==v2["stopping"] and
         v1["transfer"]==v2["transfer"] and
         len(v1["procedure"])==len(v2["procedure"])==4 and
         len(v1["falsifiers"])==len(v2["falsifiers"])==4,
         "WF0BE_INVALID_SHADOW_V1_V2_COMPARISON")
    return v1,v2


def _read_pack(pack_path: Path) -> tuple[dict,str]:
    raw=Path(pack_path).read_bytes()
    need(len(raw)<40_000,"WF0BE_CASE_PACK_TOO_LARGE")
    cfg=json.loads(raw)
    need(type(cfg) is dict and set(cfg)=={
        "format","created","status","writer_compared",
        "v1_capsule_sha256","v2_capsule_sha256",
        "original_0ay_glm_429_requires_permanent_no_retry",
        "fresh_cases_only","task_family","experimental_treatment",
        "real_provider_calls_performed",
        "new_paid_provider_calls_authorized","prospective_max_pairs",
        "prospective_total_requests_if_separately_authorized",
        "prospective_max_completion_tokens_per_request",
        "provider_or_model","same_model_same_task_same_output_cap_required",
        "inputs_contain_no_original_novel_R2_or_Canon","blind_plan","cases"
    },"WF0BE_PACK_SCHEMA_UNEXPECTED")
    need(cfg["format"]=="wf.0be.v1-v2-prospective-falsification.v1" and
         cfg["status"]=="PRE_REGISTERED_UNRUN_NO_MODEL_EVIDENCE" and
         cfg["writer_compared"]=="observe-before-next-choice" and
         cfg["v1_capsule_sha256"]==V1_SHA and
         cfg["v2_capsule_sha256"]==V2_SHA and
         cfg["original_0ay_glm_429_requires_permanent_no_retry"] is True and
         cfg["fresh_cases_only"] is True and
         cfg["real_provider_calls_performed"]==0 and
         cfg["new_paid_provider_calls_authorized"]==0 and
         cfg["provider_or_model"]==MODEL_UNSPECIFIED and
         cfg["same_model_same_task_same_output_cap_required"] is True and
         cfg["inputs_contain_no_original_novel_R2_or_Canon"] is True and
         type(cfg["prospective_max_completion_tokens_per_request"]) is int and
         cfg["prospective_max_completion_tokens_per_request"]==1800,
         "WF0BE_NO_PROVIDER_BUDGET_OR_PROVENANCE_POLICY")
    plan=cfg["blind_plan"]
    need(type(plan) is dict and
         plan.get("require_independent_reviewers")==2 and
         plan.get("score_on_actual_model_outputs_only") is True and
         plan.get("blinded_arm_labels_only") is True and
         plan.get("allow_no_clear_winner") is True and
         plan.get("no_bonus_for_more_specific_prompt") is True and
         plan.get("no_automatic_promotion") is True and
         set(plan.get("outcomes_of_interest",[]))==EXPECTED_CRITERIA and
         set(plan.get("negative_controls",[]))==NEGATIVE_CONTROLS,
         "WF0BE_INDEPENDENT_BLIND_REVIEW_POLICY_CHANGED")
    cases=cfg["cases"]
    need(type(cases) is list and len(cases)==8 and
         cfg["prospective_max_pairs"]==8 and
         cfg["prospective_total_requests_if_separately_authorized"]==16,
         "WF0BE_UNMATCHED_OR_PARTIAL_TASKS")
    names=set()
    for case in cases:
        need(type(case) is dict and set(case)=={
            "case_id","genre","type","prior_prose","task","risk"
        },"WF0BE_CASE_SCHEMA_INVALID")
        cid=case["case_id"]
        need(type(cid) is str and re.fullmatch(r"[a-z][a-z0-9-]{3,79}",cid)
             is not None and cid not in names and "flood-radio" not in cid,
             "WF0BE_DUPLICATE_OR_OLD_PAID_TASK")
        names.add(cid)
        need(type(case["prior_prose"]) is list and
             len(case["prior_prose"])==2 and
             all(type(s) is str and 35 <= len(s) <= 400
                 for s in case["prior_prose"]) and
             type(case["task"]) is str and
             25 <= len(case["task"]) <= 310 and
             type(case["genre"]) is str and
             3 <= len(case["genre"]) <= 64 and
             type(case["type"]) is str and
             3 <= len(case["type"]) <= 80 and
             type(case["risk"]) is str and
             15 <= len(case["risk"]) <= 240,
             "WF0BE_CASE_TEXT_OR_SCOPE_INVALID")
    return cfg,digest(raw)


def build_preflight(*,pack_path:Path=PACK)->dict:
    """Freeze author envelopes; no model or third-party tool is used."""
    cfg,pack_sha=_read_pack(pack_path)
    v1,v2=_read_capsules()
    entries=[]
    cases=[]
    for case in cfg["cases"]:
        task_id=case["case_id"]
        source=case["prior_prose"]
        task=case["task"]
        source_sha=digest(canonical(source))
        task_sha=digest(task.encode("utf8"))
        cases.append({
            "case_id":task_id,"source_sha256":source_sha,
            "task_sha256":task_sha,"arms":["v1","v2"],
            "negative_control":task_id in NEGATIVE_CONTROLS
        })
        # Deterministic opposite-first order avoids always showing v2 after
        # v1. It does not claim to control provider randomness/call conditions.
        order=("v1","v2") if int(digest(task_id.encode())[:2],16)%2==0 else ("v2","v1")
        for arm in order:
            capsule=v1 if arm=="v1" else v2
            entries.append({
                "format":"wf.0be.prepared-author-input.v1",
                "case_id":task_id,"arm":arm,
                "source_sha256":source_sha,"task_sha256":task_sha,
                "source_segments":source,
                "task":task,
                "cognitive_procedure":list(capsule["procedure"]),
                "capsule_sha256":V1_SHA if arm=="v1" else V2_SHA,
                "model":MODEL_UNSPECIFIED,
                "system_instruction":SYSTEM,
                "max_completion_tokens":1800,
                "writer_retains_next_choice":True,
                "literary_improvement_proven":False,
                "prospective":True,
            })
    costs={
        "v1_step_1_chars":len(v1["procedure"][1]),
        "v2_step_1_chars":len(v2["procedure"][1]),
        "step_1_extra_chars":len(v2["procedure"][1])-len(v1["procedure"][1]),
        "falsifier_extra_chars":len(v2["falsifiers"][0])-len(v1["falsifiers"][0]),
        "contract_extra_chars":len(json.dumps(v2,ensure_ascii=False))-len(
            json.dumps(v1,ensure_ascii=False)),
        "actual_prompt_tokens":None,
        "actual_completion_tokens":None,
        "literary_gain_verified":False,
        "token_cost_proven":False,
        "chars_not_tokens":True,
    }
    need(costs["v1_step_1_chars"]==138 and
         costs["v2_step_1_chars"]==417 and
         costs["step_1_extra_chars"]==279 and
         costs["falsifier_extra_chars"]==183 and
         costs["contract_extra_chars"]==462,
         "WF0BE_UNEXPECTED_V1_V2_CONTEXT_DRIFT")
    return {
        "format":"wf.0be.falsification-preflight-only.v1",
        "status":BUDGET_REQUIRED_STATUS,
        "frozen_case_pack_sha256":pack_sha,
        "v1_capsule_sha256":V1_SHA,
        "v2_capsule_sha256":V2_SHA,
        "cases":cases,
        "envelopes":entries,
        "contract_cost":costs,
        "new_provider_calls":0,
        "new_paid_model_calls_authorized":0,
        "model_outputs_present":0,
        "prospective_total_requests_if_authorized":16,
        "historical_glm_429_retries":0,
        "writer_model":MODEL_UNSPECIFIED,
        "literary_improvement_proven":False,
        "all_model_inputs_unaccepted_synthetic_data":True,
        "original_0ay_source_artifact_not_required":True,
    }


def report_cost_and_verification(preflight:dict)->dict:
    """No outcome labels until independent source-matched real provider arms."""
    if (type(preflight) is not dict or
        preflight.get("format")!="wf.0be.falsification-preflight-only.v1" or
        preflight.get("status")!=BUDGET_REQUIRED_STATUS or
        preflight.get("model_outputs_present")!=0 or
        preflight.get("new_provider_calls")!=0 or
        preflight.get("new_paid_model_calls_authorized")!=0 or
        preflight.get("literary_improvement_proven") is not False):
        raise ValueError("WF0BE_NO_REAL_PROVIDER_OR_EDITOR_EVIDENCE")
    return {
        "disposition":BUDGET_REQUIRED_STATUS,
        "source_locked_case_pack_sha256":preflight["frozen_case_pack_sha256"],
        "tested_candidate_sha256":V2_SHA,
        "baseline_capsule_sha256":V1_SHA,
        "observed_context_extra_chars":preflight["contract_cost"]["contract_extra_chars"],
        "verified_model_input_tokens":None,
        "verified_model_output_tokens":None,
        "winner_sha256":None,
        "quality_evidence":"NONE",
        "independent_reader_evidence":False,
        "falsified":False,
        "auto_promote":False,
        "new_model_calls":0,
        "old_glm_429_retried":False,
    }


def freeze_for_host(*,output:Path=OUTPUT)->dict:
    """Write preview only. There is no HTTP client in this protocol."""
    if output.exists():
        raise FileExistsError("WF0BE_PREVIEW_ALREADY_EXISTS_NO_OVERWRITE")
    plan=build_preflight()
    status=report_cost_and_verification(plan)
    output.mkdir(parents=True,exist_ok=False)
    summary=dict(plan,**{
        "has_no_model_results":True,
        "independent_literary_review":False,
        "host_call_permitted":False,
        "auto_promotion":False,
    })
    (output/"PREVIEW.json").write_text(json.dumps(
        summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf8")
    (output/"NO_PROVEN_VALUE_YET.json").write_text(json.dumps(
        status,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print("WF0BE_VALUE_FALSIFICATION_UNRUN "+json.dumps({
        "status":status["disposition"],
        "fresh_cases":len(plan["cases"]),
        "future_pairs":len(plan["envelopes"])//2,
        "extra_contract_chars":status["observed_context_extra_chars"],
        "new_model_calls":0,
        "new_literary_evidence":False,
    },ensure_ascii=False,sort_keys=True),flush=True)
    return summary


if __name__=="__main__":
    freeze_for_host()
