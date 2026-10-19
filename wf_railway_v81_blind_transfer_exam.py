"""V81 genuinely independent, pre-registered blind literary AB comparison.

Runs AFTER the full chapter7-12 training (never part of its prompts).
Inputs are three synthetic scenes frozen earlier in GitHub. The base model
and prompt schema are identical between groups; the only experimental
difference is the prior WF reading strategy from the signed chapter12 R2
experience. This tests a tiny observational association, not causality or
literary mastery. NO other model grades the answers: a fixed exact-quote and
mechanism rule is evaluated by Python, each response and result is R2-CAS
signed and independently recoverable.

Maximum SIX DeepSeek calls, each <=450 output tokens, no network retries.
This is a separate evaluation budget, not hidden in the 150k training batch.
No private original book sentence is sent as an exam question.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
import sys
import time
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

ENDPOINT="https://wf-r2-api.3227482831.workers.dev"
OLD_SOURCE_SHA="0f00a16f6a0c121404a28257f3aa728468c9dae78d464ff1341746a45c41ddbd"
OLD_SOURCE_KEY_SHA="370400053cded15ca89e3232e7be84b28aa20ca70542150138bef6201dc7cb22"
TRAINING_FINAL_BATCH_POINTER="TO_BE_PINNED_AFTER_CHAPTER12"
TRAINING_FINAL_EXPERIENCE_SHA="TO_BE_PINNED_AFTER_CHAPTER12"

def emit(v):
    print(json.dumps(v,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V81_PRE_FROZEN_INDEPENDENT_BLIND_ABLATION_START",flush=True)

def main():
    keys=("WF_API_TOKEN","WF_INDEX_UPLOAD_TOKEN","DEEPSEEK_API_KEY")
    if any(not os.getenv(k) for k in keys):
        emit({"status":"WF_V81_EXAM_EXISTING_CREDENTIALS_MISSING"})
        return 1
    model=None
    record_hashes=[]
    journal=None
    try:
        from writerforge.v79_provisional_r2_cas_journal import (
            WFProvisionalR2CASJournal)
        from writerforge.wf_learn_model_registry import new_wf_learn_model
        from writerforge.deepseek_flash_model import FlashBudget
        from writerforge.v81_frozen_blind_ablation import (
            CASES,EXAM_VERSION,MAX_MODEL_RESPONSE_TOKENS,
            frozen_sha,prompt_for_case,grade_case,decision_summary)
        from writerforge.r2_learn_journal import canonical
        if (len(TRAINING_FINAL_BATCH_POINTER)!=64 or
            len(TRAINING_FINAL_EXPERIENCE_SHA)!=64):
            raise ValueError("WF_V81_EXAM_TRAINING_POINTER_NOT_PINNED")
        journal=WFProvisionalR2CASJournal(endpoint=ENDPOINT)
        journal.require_writer_ready()  # zero-R2-write auth gate
        final=json.loads(journal._get_content(
            TRAINING_FINAL_BATCH_POINTER))
        exp=json.loads(journal._get_content(
            TRAINING_FINAL_EXPERIENCE_SHA))
        if not (
            final.get("batch_id")=="WF-V81-150K-20261019-CH7-12" and
            final.get("last_completed_chapter")==12 and
            final.get("source_sha256")==OLD_SOURCE_SHA and
            final.get("source_key_sha256")==OLD_SOURCE_KEY_SHA and
            final.get("latest_experience_sha256")==
                TRAINING_FINAL_EXPERIENCE_SHA and
            final.get("mastery_graduation_approved") is False and
            exp.get("format")=="wf.learn.experience.v80" and
            exp.get("chapter")==12 and
            exp.get("source_sha256")==OLD_SOURCE_SHA and
            exp.get("source_key_sha256")==OLD_SOURCE_KEY_SHA and
            exp.get("literary_quality_independently_verified") is False
        ):
            raise ValueError("WF_V81_EXAM_SIGNED_EXPERIENCE_MISMATCH")
        strategy=exp["reflection"]["next_strategy"]
        if not isinstance(strategy,str) or not 1<=len(strategy)<=200:
            raise ValueError("WF_V81_EXAM_PRIOR_STRATEGY_NOT_AVAILABLE")
        emit({
          "status":"WF_V81_TRAINED_STRATEGY_VERIFIED_BEFORE_BLIND_TEST",
          "frozen_blind_rubric_sha256":frozen_sha(),
          "training_batch_pointer":TRAINING_FINAL_BATCH_POINTER,
          "experience_sha256":TRAINING_FINAL_EXPERIENCE_SHA,
          "experience_strategy_sha256":sha256(strategy.encode()).hexdigest(),
          "blind_scenarios_never_in_training_runner":True,
          "model_calls_so_far":0,
          "user_novel_text_logged":False,
        })
        budget=FlashBudget(max_calls=6,max_reserved_output_tokens=2700)
        model=new_wf_learn_model(budget=budget)
        results=[]
        for case in CASES:
            # SHA-derived deterministic arm order, fixed before answering.
            flip=int(sha256(("v81-pair-"+case["id"]).encode()).hexdigest(),16)%2
            arms=("with_experience","without_experience") if flip else (
                  "without_experience","with_experience")
            for arm in arms:
                sys_prompt,user_prompt=prompt_for_case(
                    case,experience_strategy=(
                         strategy if arm=="with_experience" else None))
                response=model.ask_json(
                    role="craft_analysis",
                    system=sys_prompt,
                    user=user_prompt,
                    max_tokens=MAX_MODEL_RESPONSE_TOKENS)
                grade=grade_case(case,response)
                output_bytes=canonical(response)
                entry={
                    "format":"wf.exam.response.blind.ablation.v81",
                    "frozen_exam_sha256":frozen_sha(),
                    "case_id":case["id"],
                    "arm":arm,
                    "training_experience_sha256":
                        TRAINING_FINAL_EXPERIENCE_SHA if
                        arm=="with_experience" else None,
                    "input_sha256":sha256(
                        (sys_prompt+"|"+user_prompt).encode()).hexdigest(),
                    "output_sha256":sha256(output_bytes).hexdigest(),
                    "model_response":response,
                    "examiner_rubric":grade,
                    "provider":"deepseek",
                    "model":"deepseek-flash",
                    "literary_mastery_verified":False,
                }
                event_sha,_=journal._put_content(canonical(entry))
                results.append({
                    "case_id":case["id"],
                    "arm":arm,
                    "response_event_sha256":event_sha,
                    "output_sha256":entry["output_sha256"],
                    "grade":grade,
                })
                record_hashes.append(event_sha)
                emit({
                    "status":"WF_V81_BLIND_PAIR_RESPONSE_R2_SIGNED",
                    "case_id":case["id"],"arm":arm,
                    "response_event_sha256":event_sha,
                    "source_quote_exact":grade["source_exact"],
                    "frozen_rubric_score":grade["score"],
                    "total_calls":budget.calls_reserved,
                    "user_novel_sent_for_test":False,
                })
        verdict=decision_summary(results)
        summary={
            "format":"wf.exam.result.blind.ablation.v81",
            "frozen_exam_sha256":frozen_sha(),
            "training_batch_pointer_sha256":TRAINING_FINAL_BATCH_POINTER,
            "prior_experience_sha256":TRAINING_FINAL_EXPERIENCE_SHA,
            "cases":results,
            "examiner_deterministic_verdict":verdict,
            "model_usage":model.public_usage_report(),
            "third_party_billing_dashboard_reconciled":False,
            "reader_only_independent_readback_pending":True,
            "literary_level_promoted":False,
        }
        summary_sha,_=journal._put_content(canonical(summary))
        emit({
           "status":"WF_V81_FROZEN_BLIND_ABLATION_EXECUTED_AND_R2_SAVED",
           "summary_cas_sha256":summary_sha,
           "rubric":verdict,
           "model_usage":model.public_usage_report(),
           "model_calls":budget.calls_reserved,
           "source_original_read_by_exam":False,
           "full_literary_skill_transfer_proven":False,
           "needs_separate_reader_audit":True,
        })
        return 0
    except Exception as err:
        code=str(err)
        if not code.startswith(("WF_V81_","WF_FLASH_","WF_LEARN_",
                                "WF_V79_","WF_INDEX_","WF_USAGE_")):
            code="WF_V81_BLIND_UNEXPECTED_FAILURE"
        emit({
          "status":"WF_V81_BLIND_ABLATION_STOPPED_WITH_PARTIAL_R2_EVENTS",
          "error_code":code,"existing_response_event_sha256":record_hashes,
          "model_usage":model.public_usage_report() if model else None,
          "model_retries":0,
          "literary_level_promoted":False,
        })
        return 1

status=main()
print("WF_V81_BLIND_ABLATION_EXIT="+str(status),flush=True)
time.sleep(6)
raise SystemExit(status)
