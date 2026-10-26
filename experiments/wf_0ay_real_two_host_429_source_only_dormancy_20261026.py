"""WF 0.AZ: re-examine original 0.AY provider partial and classify resource stop.

Source is Actions 40354436598 artifact
WF-0AY-Two-REAL-Model-Hosts-Portable-Habit-Eight-Capped-Original-Wires.
Do NOT generate a fourth answer, assume it cost $0, or mark an unavailable
GLM counterfactual as a literary failure. All three original model wires are
unchanged. The HTTP 429 response *body* was not preserved by the transport;
the original Actions logs and STATUS are the only evidence of the status code.

No new memory, no new rule/judge, no API/network/R2/Canon interactions.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

from writerforge.evolution import (
    SkillStatus, HabitTrialEvidence, assess_habit_trial_continuation,
)

SOURCE=Path("wf0ay_real_two_hosts_partial_source")
OUTPUT=Path("wf_0ay_first_portable_habit_real_transfer_stop_forensics_20261026")
TRIAL_RUN=40354436598
TRIAL_ARTIFACT_ID=12664209371
CAPSULE=Path(".agents/skills/observe-before-next-choice/capsule.json")
FROZEN=Path("experiments/wf_0ay_portable_habit_fresh_cross_host_fixtures_20261026.json")
CAPSULE_SHA="42cad98118dea662cea472f708ef1de22f4bb139da3210b1f5c3c1f9ac12664d"
FROZEN_RAW_SHA="aa16fa7696440b86a942ddd2d4071dd8d13a6b6ad561c3456a841e700bb76373"
MODEL_SHAS={
 ("deepseek","flood-radio","control"):(
     "daa44c87493e5329b949d178a99eea00817ce8901b07b3525d1c4cbcb8ea4810",
     "8faf6aa520f8f9da6662fc9572ed70257d9e350cc575320b8bddfc3686c565bb"),
 ("deepseek","flood-radio","habit"):(
     "81827cf112daf0241c085726c989bf44a5e086b250bd66dc8823fa54a0ec5e17",
     "d64effd386c661bd6d63575b06b7641397223eb8dbf69c6aed650d3bfbd04c6b"),
 ("discovery","flood-radio","control"):(
     "11c29fd3d972af0fa45b6d7dc63131ce8238ff11522495217e682c119bbb7d9b",
     "2fbadc83a5580de5f817354d1cd44fd5ae451f83d3411b6462b9b43dcf7ac0e4"),
}
ATTEMPTS=(
 ("deepseek","flood-radio","control"),
 ("deepseek","flood-radio","habit"),
 ("discovery","flood-radio","control"),
 ("discovery","flood-radio","habit"),
)
REQUEST_COUNT=8
MAX_MODEL_CALLS=8


def h(value):
    return sha256(value if type(value) is bytes else value.encode("utf8")).hexdigest()


def need(test,code):
    if not test:
        raise ValueError(code)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,
                               indent=2)+"\n",encoding="utf8")


def replay_status():
    s=read(SOURCE/"STATUS.json")
    need(type(s) is dict and
         s.get("format")=="wf.0ay.true-two-provider-habit-vs-control.v1" and
         s.get("status")=="SAFE_PARTIAL_TWO_HOST_CROSS_TRANSFER_NO_RETRIES" and
         s.get("failure_code")=="WF0AY_SECOND_HOST_HTTP_429" and
         s.get("model_calls")==4 and
         s.get("model_output_reserved")==7200 and
         s.get("per_host_paid_calls")=={"deepseek":2,"discovery":2} and
         s.get("capsule_sha256")==CAPSULE_SHA and
         s.get("frozen_fixture_source_sha256")==FROZEN_RAW_SHA and
         s.get("authenticated_second_host_model_listing_passed") is True and
         len(s.get("events",[]))==4 and
         len(s.get("completed",[]))==3 and
         s.get("literary_quality_proven") is False and
         s.get("habit_still_shadow") is True and
         s.get("R2_reads")==s.get("R2_writes")==s.get("Canon_writes")==0 and
         s.get("Railway_deployments")==0 and
         s.get("main_modified") is False,
         "WF0AZ_ORIGINAL_PROVIDER_FAILURE_STATUS_DRIFT")
    return s


def replay_requests():
    need(h(CAPSULE.read_bytes())==CAPSULE_SHA,
         "WF0AZ_PORTABLE_CAPSULE_CHANGED_AFTER_REAL_EXPERIMENT")
    need(h(FROZEN.read_bytes())==FROZEN_RAW_SHA,
         "WF0AZ_FROZEN_NEW_HOLDOUT_TASKS_CHANGED")
    frozen=read(FROZEN)
    need(type(frozen) is dict and frozen.get("format")==
         "wf.0ay.two-real-hosts-new-scenarios.v1" and
         frozen.get("reuse_old_nightvalve") is False and
         len(frozen.get("tasks",[]))==2,
         "WF0AZ_ORIGINAL_SCENARIOS_DRIFT")
    cases={t["task_id"]:t for t in frozen["tasks"]}
    need(set(cases)=={"flood-radio","historic-seal"},
         "WF0AZ_FROZEN_CASES_CHANGED")
    for name,task in cases.items():
        actual=read(SOURCE/"frozen-new-tasks"/(name+".json"))
        need(actual==task,"WF0AZ_FROZEN_SCENE_PROSE_DRIFT")
        for line in task["prior_prose"]:
            need(type(line["prose"]) is str and
                 h(line["prose"])==line["sha256"],
                 "WF0AZ_OLD_SOURCE_LITERAL_SHA_CHANGED")
    contexts={}
    for host in ("deepseek","discovery"):
        for name in cases:
            for arm in ("control","habit"):
                request=read(SOURCE/"requests"/host/name/(arm+".json"))
                source_shas=[row["sha256"] for row in cases[name]["prior_prose"]]
                envelope=request["actual_provider_input_envelope"]
                envelope_sha=h(json.dumps(
                    envelope,ensure_ascii=False,sort_keys=True,
                    separators=(",",":"),allow_nan=False))
                need(request["host"]==host and
                     request["scene"]==name and
                     request["arm"]==arm and
                     request["model"]==(
                         "deepseek-flash" if host=="deepseek" else "glm-5.3") and
                     request["model_max_completion_tokens"]==1800 and
                     request["source_sha256s"]==source_shas and
                     request["input_envelope_sha256"]==envelope_sha and
                     request["active_cognitive_habit_included"]==(arm=="habit") and
                     request["independent_literary_gain_proven"] is False,
                     "WF0AZ_ORIGINAL_PROMPT_SOURCE_OR_HOST_BUDGET_DRIFT")
                contexts[(host,name,arm)]=request
    for name in cases:
        for arm in ("control","habit"):
            x=contexts[("deepseek",name,arm)]
            y=contexts[("discovery",name,arm)]
            need(x["source_sha256s"]==y["source_sha256s"],
                 "WF0AZ_DIFFERENT_ORIGINAL_SOURCE_BETWEEN_HOSTS")
            if arm=="habit":
                need(type(x["semantic_habit_core_sha256"]) is str and
                     len(x["semantic_habit_core_sha256"])==64 and
                     x["semantic_habit_core_sha256"]==
                     y["semantic_habit_core_sha256"],
                     "WF0AZ_COGNITIVE_HABIT_CHANGED_ACROSS_PROVIDERS")
            else:
                need(x["semantic_habit_core_sha256"] is
                     y["semantic_habit_core_sha256"] is None,
                     "WF0AZ_CONTROL_ALREADY_CONTAINS_HABIT")
    return contexts


def replay_provider_originals(status,requests):
    inspected=[]
    prior_success={}
    for ix,row in enumerate(status["events"]):
        key=(row["host"],row["scene"],row["arm"])
        need(key==ATTEMPTS[ix] and
             row["paid_call_index"]==ix+1 and
             row["reserved_completion_tokens"]==1800 and
             row["prompt_sha256"]==requests[key]["input_envelope_sha256"] and
             row["model"]==requests[key]["model"],
             "WF0AZ_PAID_ATTEMPT_SEQUENCE_OR_PROVIDER_INPUT_DRIFT")
        src=SOURCE/"original-provider-wires"/row["host"]/(
            row["scene"]+"-"+row["arm"]+".json")
        generated=SOURCE/"authored-unaccepted-fiction"/row["host"]/row["scene"]/(
            row["arm"]+".json")
        if ix==3:
            # Distinguish a reserved/attempted HTTP 429 from a successful
            # response or a guaranteed billable completion. Do NOT fabricate.
            need(row["original_wire_sha256"] is None and
                 row["wire_written_before_decode"] is False and
                 row["parsed_source_only"] is False and
                 not src.exists() and not generated.exists(),
                 "WF0AZ_GLMMODEL_429_MISSING_COUNTERFACTUAL_WAS_FORGED")
            inspected.append({
                "host":row["host"],"scene":row["scene"],"arm":row["arm"],
                "attempt_index":ix+1,"completion":"PROVIDER_HTTP_429_NO_TEXT",
                "model_response_preserved":False,
                "request_may_have_billed":True,
                "actual_provider_http_error_body_saved":False,
                "source_of_status_code":"signed_run_STATUS_plus_GitHub_Actions_logs",
                "prompt_sha256":row["prompt_sha256"],
                "reserved_completion_tokens":1800,
            })
            continue
        expect_wire,expect_prose=MODEL_SHAS[key]
        wire=src.read_bytes()
        need(h(wire)==expect_wire==row["original_wire_sha256"] and
             row["wire_written_before_decode"] is True and
             row["parsed_source_only"] is True,
             "WF0AZ_ORIGINAL_PROVIDER_WIRE_SHA_NOT_INTACT")
        provider=json.loads(wire)
        need(provider["model"]==row["model"] and
             provider["choices"][0]["finish_reason"]=="stop",
             "WF0AZ_SUCCESS_PROVIDER_MODEL_OR_FINISH_MISMATCH")
        original=json.loads(provider["choices"][0]["message"]["content"])
        artifact=read(generated)
        result=status["completed"][ix]
        need(type(original) is dict and
             set(original)=={"prose","chosen_step","still_unknown"} and
             h(original["prose"])==expect_prose==
                 artifact["prose_sha256"]==result["prose_sha256"] and
             artifact["prose"]==original["prose"] and
             artifact["chosen_step"]==original["chosen_step"]==
                 result["writer_choice"] and
             artifact["still_unknown"]==original["still_unknown"]==
                 result["unresolved"] and
             artifact["char_count"]==len(original["prose"])==result["chars"] and
             result["wire_sha256"]==expect_wire,
             "WF0AZ_ORIGINAL_AUTHOR_PROSE_OR_CHOICE_DRIFT")
        dest=OUTPUT/"unchanged-upstream-wire-copies"/row["host"]/(
            row["scene"]+"-"+row["arm"]+".json")
        need(not dest.exists(),"WF0AZ_NEVER_OVERWRITE_PREVIOUS_PROVIDER_BYTES")
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(wire)
        prior_success[key]=original
        inspected.append({
            "host":row["host"],"scene":row["scene"],"arm":row["arm"],
            "attempt_index":ix+1,"completion":"REAL_STOPPED_PROVIDER_RESPONSE",
            "provider_wire_sha256":expect_wire,
            "original_prose_sha256":expect_prose,
            "chars":len(original["prose"]),
            "prompt_sha256":row["prompt_sha256"],
            "reserved_completion_tokens":1800,
            "provider_wire_saved_before_decode":True,
            "original_author_decision_kept":True,
        })
    need(len(prior_success)==3 and
         len([r for r in inspected if r["completion"]==
              "PROVIDER_HTTP_429_NO_TEXT"])==1,
         "WF0AZ_UNMATCHED_PAIRS_FALSE_COMPLETION")
    return inspected,prior_success


def main():
    need(not OUTPUT.exists(),"WF0AZ_SOURCE_FIRST_EVIDENCE_NEVER_OVERWRITE")
    OUTPUT.mkdir(parents=True)
    status={
        "format":"wf.0az.429-dormant-habit-source-forensics.v1",
        "state":"STARTED","original_paid_run":TRIAL_RUN,
        "original_artifact_id":TRIAL_ARTIFACT_ID,
        "new_model_calls":0,"originals_modified":False,
        "literary_improvement_proven":False,
        "R2_reads":0,"R2_writes":0,"Canon_writes":0,
        "Railway_deployments":0,"main_modified":False,
    }
    try:
        old=replay_status()
        requests=replay_requests()
        events,originals=replay_provider_originals(old,requests)
        # Exactly one FULL matched pair (DeepSeek/flood-radio).
        # GLM habit arm does NOT exist, nor either historic-seal arm.
        observed=HabitTrialEvidence(
            habit_id="observe-before-next-choice",
            current_status=SkillStatus.SHADOW,
            verified_source_receipts=True,
            expected_pairs=4,
            completed_pairs=1,
            attempted_model_calls=old["model_calls"],
            completed_model_responses=len(old["completed"]),
            provider_failure_code=old["failure_code"],
            independent_literary_review=False,
            confirmed_literary_benefit=False,
            independently_confirmed_contamination=False,
            repeated_no_benefit_evidence=False)
        decision=assess_habit_trial_continuation(observed)
        need(decision.disposition=="DORMANT_HOST_RESOURCE" and
             decision.registry_status is SkillStatus.SHADOW and
             decision.literary_conclusion=="NOT_TESTED_INCOMPLETE" and
             decision.new_provider_calls_authorized==0 and
             decision.habit_promoted is False and
             decision.habit_falsified is False and
             decision.requires_external_restart_approval,
             "WF0AZ_RATE_LIMIT_WRONGLY_PUNISHED_HABIT")
        report={
            "status":"ORIGINAL_THREE_REAL_AUTHOR_WIRES_SHA_PASSED",
            "original_run":TRIAL_RUN,
            "original_artifact":TRIAL_ARTIFACT_ID,
            "frozen_synthetic_context_sha256":FROZEN_RAW_SHA,
            "portable_capsule_sha256":CAPSULE_SHA,
            "attempted_requests_potentially_billable":4,
            "reserved_output_tokens_not_provider_usage":7200,
            "completed_provider_responses":3,
            "matched_complete_A_B_pairs":1,
            "expected_matched_pairs":4,
            "provider_HTTP_429_raw_body_saved":False,
            "unreturned_fourth_GLMMODEL_response_does_not_exist":True,
            "model_calls_for_this_replay":0,
            "all_provider_inputs_are_application_envelopes_not_wire_request_bytes":True,
            "true_distinct_models_on_one_GitHub_harness_not_two_separate_app_hosts":True,
            "independent_literary_grades":None,
            "literary_quality_transfer_proven":False,
            "writer_prose_unaccepted":True,
            "new_canon_or_book_writes":0,
            "original_provider_events":events,
            "habit_evolution_stop_recommendation":{
                "disposition":decision.disposition,
                "registry_status_unchanged":decision.registry_status.value,
                "literary_conclusion":decision.literary_conclusion,
                "reason":decision.reason,
                "new_provider_calls_authorized":0,
                "requires_external_restart_approval":True,
                "no_skill_mutation":True,
            },
        }
        save(OUTPUT/"REAL_THREE_WIRES_AND_ONE_UNRETURNED_SOURCE_ONLY.json",report)
        txt=(
            "# 原始 DeepSeek 与 GLM 0.AY 跨模型认知习惯：真正已写与未写\n\n"
            "原始 Actions #40354436598；**零新增调用、不重试429**。"
            "故事全文只为合成实验，不进入小说原著、Canon 或技能包。\n\n"
            "DeepSeek 同题对照完整；GLM 只完成无习惯组。"
            "第4次 GLM 习惯组请求 429，缺失输出，不能补造。\n\n"
        )
        for key in ATTEMPTS:
            text=originals.get(key)
            txt+="## "+"/".join(key)+"\n\n"
            if text is None:
                txt+="**没有实际模型正文。HTTP 429，停止并休眠，不判文学胜负。**\n\n"
            else:
                txt+="原稿 SHA256：\`"+h(text["prose"])+ "\`\n\n"+text["prose"]+"\n\n"
                txt+="作者自选动作："+text["chosen_step"]+"\n\n"
        (OUTPUT/"REAL_MODEL_AUTHOR_ORIGINALS_READABLE.md").write_text(
            txt,encoding="utf8")
        status["state"]="SOURCE_VERIFIED_HOST_DORMANT_NO_MODEL_RETRY"
        status["recommendation"]=report["habit_evolution_stop_recommendation"]
        status["original_wires_sha256s"]=[r["provider_wire_sha256"]
            for r in events if "provider_wire_sha256" in r]
        print("WF0AZ_ORIGINAL_429_TRUE_DORMANCY_GREEN "+json.dumps({
            "attempted_requests":4,"original_responses":3,
            "matched_pairs":1,"habit_disposition":decision.disposition,
            "new_model_calls":0,"literary_improvement_proven":False,
        },ensure_ascii=False),flush=True)
    except Exception as e:
        msg=str(e)
        status["state"]="SOURCE_FIRST_FAIL_CLOSED_NO_PROVIDER_RETRY"
        status["failure_code"]=(
            msg if re.fullmatch(r"WF[A-Z0-9_:\\.-]{4,165}",msg)
            else type(e).__name__+":NO_RETRY")
    finally:
        save(OUTPUT/"STATUS.json",status)
    if status["state"]!="SOURCE_VERIFIED_HOST_DORMANT_NO_MODEL_RETRY":
        raise RuntimeError("WF0AZ_UPSTREAM_REAL_EVIDENCE_MISMATCH_NO_PAID_RETRY")


if __name__=="__main__":
    main()
