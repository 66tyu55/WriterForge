"""V37b: fixed-format, two-stage independent L2 literary forensic evaluation.

Previous V37 invalid reviews remain immutable. This is a separate protocol
version, NOT a regrade picking whichever reviewer agrees with WF.
The only inputs are the frozen Xi You Ji source reading, L2 candidate, locked
prewrite decision, and unchanged first/revised manuscripts.

Each of two external critic models responds twice:
  phase A -- is source evidence/abstraction/task-fit defensible?
  phase B -- can exact numbered original/revised sentences demonstrate an
             early setup and later payoff, or is it absent/uncertain?
No novel generation, no WF self-critique, no averaging, no formal promotion.
All raw outputs are privately saved BEFORE parse validation, even if wrong.
"""
from __future__ import annotations
from hashlib import sha256
import json,os,re,sys

from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_discovery_models import (
    DiscoveryModel,DiscoveryCallBudget,DiscoveryError,
)
from writerforge.v35_observable_trace import sha,canonical
from scripts.forensic_v37_xiyouji_L2 import frozen_evidence,sentence_menu

ROOT="writerforge/v1/examiner/v37b-l2-independent-source-and-payoff"
SESSION="20261017-V37b-fixed-review-format-two-different-models"
CRITICS=("deepseek-v4-pro-0813","minimax-m3")
CAP=35000
SOURCE_ENUM={
    "source_support":{"SUPPORTED","PARTIAL","UNSUPPORTED","UNCERTAIN"},
    "abstraction_fidelity":{"FAITHFUL","PARTIAL","DISTORTED","UNCERTAIN"},
    "task_fit":{"APPROPRIATE","RISKY","INAPPROPRIATE","UNCERTAIN"},
}
DRAFT_ENUM={
    "first_execution":{"OBSERVED","PARTIAL","NOT_OBSERVED","UNCERTAIN"},
    "revised_execution":{"OBSERVED","PARTIAL","NOT_OBSERVED","UNCERTAIN"},
    "revised_payoff":{"GROUNDED","WEAK","MISSING","UNCERTAIN"},
}
SOURCE_FIELDS=set(SOURCE_ENUM)|{"source_reason","abstraction_reason","fit_reason","uncertainty"}
DRAFT_FIELDS=set(DRAFT_ENUM)|{
    "first_setup_numbers","first_payoff_numbers","revised_setup_numbers",
    "revised_payoff_numbers","execution_reason","uncertainty",
}

class L2SplitReviewError(ValueError):
    pass

def _check(expr:bool,code:str):
    if not expr:raise L2SplitReviewError(code)

def _root()->str:return f"{ROOT}/{SESSION}"

def _record(vault,name:str,document:dict)->str:
    blob=canonical(document)
    _check(len(blob)<=CAP,"V37B_PRIVATE_EVIDENCE_SIZE_EXCEEDED")
    h=sha(blob);key=f"{_root()}/{name}-{h}.json"
    vault._put_small_immutable(key,blob,h)
    _check(vault._get_small(key,CAP)==blob,"V37B_PRIVATE_EVIDENCE_GET_FAILED")
    return h

def _unwrap(reply:dict,fields:set[str])->dict:
    current=reply
    for _ in range(3):
        if not isinstance(current,dict):
            raise L2SplitReviewError("V37B_MODEL_REPLY_NOT_JSON_OBJECT")
        if set(current)==fields:return current
        if len(current)!=1:
            raise L2SplitReviewError("V37B_MODEL_MISSING_OR_EXTRA_FIELDS")
        key=next(iter(current))
        if key not in ("result","review","evaluation","data","analysis"):
            raise L2SplitReviewError("V37B_JSON_WRAPPER_NOT_ALLOWED")
        current=current[key]
    raise L2SplitReviewError("V37B_JSON_TOO_DEEPLY_WRAPPED")

def _safe_reason(value:str)->bool:
    return isinstance(value,str) and 15<=len(value.strip())<=275

def validate_source_phase(raw)->dict:
    record=_unwrap(raw,SOURCE_FIELDS)
    for k,valid in SOURCE_ENUM.items():
        _check(isinstance(record[k],str) and record[k] in valid,
               "V37B_UNKNOWN_SOURCE_JUDGMENT")
    for field in ("source_reason","abstraction_reason","fit_reason","uncertainty"):
        _check(_safe_reason(record[field]),"V37B_SOURCE_EXPLANATION_INVALID")
    return record

def _citation_numbers(value,menu,kind:str)->list[dict]:
    _check(isinstance(value,list) and len(value)<=4 and
           all(type(v) is int and 1<=v<=len(menu) for v in value) and
           len(set(value))==len(value),
           "V37B_INVALID_NUMBERED_"+kind+"_CITATIONS")
    return [menu[n-1] for n in value]

def validate_draft_phase(raw,menus:dict)->dict:
    row=_unwrap(raw,DRAFT_FIELDS)
    for field,enum in DRAFT_ENUM.items():
        _check(isinstance(row[field],str) and row[field] in enum,
               "V37B_UNKNOWN_DRAFT_JUDGMENT")
    for field in ("execution_reason","uncertainty"):
        _check(_safe_reason(row[field]),"V37B_DRAFT_EXPLANATION_INVALID")
    cited={}
    for field in ("first_setup_numbers","first_payoff_numbers",
                  "revised_setup_numbers","revised_payoff_numbers"):
        stage="first" if field.startswith("first") else "revised"
        cited[field]=_citation_numbers(row[field],menus[stage],field.upper())
    for stage in ("first","revised"):
        starts=cited[stage+"_setup_numbers"]
        payoffs=cited[stage+"_payoff_numbers"]
        if starts and payoffs:
            _check(min(x["start"] for x in starts) <
                   max(x["start"] for x in payoffs),
                   "V37B_PAYOFF_OCCURRED_BEFORE_SETUP")
        if row[stage+"_execution"]=="NOT_OBSERVED":
            _check(not starts and not payoffs,
                   "V37B_NO_EXECUTION_WITH_ASSERTED_CITATIONS")
    if row["revised_payoff"]=="GROUNDED":
        _check(bool(cited["revised_setup_numbers"] and
                    cited["revised_payoff_numbers"]),
               "V37B_GROUNDED_WITHOUT_EARLY_AND_LATE_ANCHOR")
    if row["revised_payoff"]=="MISSING":
        _check(not cited["revised_payoff_numbers"],
               "V37B_MISSING_PAYOFF_BUT_HAS_PAYOFF_CITATION")
    return row

def _source_input(evidence:dict)->str:
    return json.dumps({
        "role":"examiner not student",
        "genuine_chapter_window":evidence["source_window"],
        "WF_original_source_observation":evidence["original_observation"],
        "WF_L2_unreviewed_craft_hypothesis":evidence["original_lesson"],
        "examiner_original_story_task":__import__(
            "writerforge.v35_xiyouji_exam",fromlist=["task"]).task(),
        "WF_frozen_before_writing_foreshadowing_choice":
            evidence["frozen_foreshadowing_decision"],
        "output_contract":{
            "exact_fields":sorted(SOURCE_FIELDS),
            "source_support":sorted(SOURCE_ENUM["source_support"]),
            "abstraction_fidelity":sorted(SOURCE_ENUM["abstraction_fidelity"]),
            "task_fit":sorted(SOURCE_ENUM["task_fit"]),
            "reason_fields":"four fields each 15..275 Chinese characters",
            "no_numeric_score":True,
            "if_unproven_choose_uncertain":True,
        },
    },ensure_ascii=False,separators=(",",":"))

def _draft_input(evidence:dict,menus:dict)->str:
    from writerforge.v35_xiyouji_exam import task
    return json.dumps({
        "role":"independent examiner only no rewriting or assistance",
        "examiner_story_task":task(),
        "WF_frozen_foreshadowing_intent":evidence["frozen_foreshadowing_decision"],
        "first_draft_indexed_exact_sentences":[
            {"number":i,"start":x["start"],"text":x["text"]}
            for i,x in enumerate(menus["first"],1)],
        "revised_draft_indexed_exact_sentences":[
            {"number":i,"start":x["start"],"text":x["text"]}
            for i,x in enumerate(menus["revised"],1)],
        "output_contract":{
            "exact_fields":sorted(DRAFT_FIELDS),
            "first_execution":sorted(DRAFT_ENUM["first_execution"]),
            "revised_execution":sorted(DRAFT_ENUM["revised_execution"]),
            "revised_payoff":sorted(DRAFT_ENUM["revised_payoff"]),
            "citation_fields":"lists of 1-based NUMBER integers shown above; [] if absent",
            "setup_must_precede_payoff":True,
            "no_imagined_sentence_ids_or_prose":True,
            "no_numeric_quality_score":True,
            "if_no_proof_choose_missing_or_uncertain":True,
        },
    },ensure_ascii=False,separators=(",",":"))

def _safe_public(vault,model,phase,row,sha_):
    if phase=="source":
        return {"model":model,"phase":phase,"raw_receipt_sha256":sha_,
                "source_support":row["source_support"],
                "abstraction_fidelity":row["abstraction_fidelity"],
                "task_fit":row["task_fit"],
                "unreviewed_reason_sha256s":{
                    k:sha(row[k]) for k in
                    ("source_reason","abstraction_reason","fit_reason","uncertainty")}}
    return {"model":model,"phase":phase,"raw_receipt_sha256":sha_,
            "first_execution":row["first_execution"],
            "revised_execution":row["revised_execution"],
            "revised_payoff":row["revised_payoff"],
            "exact_host_sentence_numbers":{
                name:list(row[name]) for name in (
                    "first_setup_numbers","first_payoff_numbers",
                    "revised_setup_numbers","revised_payoff_numbers")},
            "unreviewed_reason_sha256s":{
                k:sha(row[k]) for k in ("execution_reason","uncertainty")}}

def run(vault=None,models_factory=None)->dict:
    vault=vault or R2StudyVault(R2Config.from_environment())
    _check(vault.config.bucket=="writerforge-private-library",
           "V37B_PRIVATE_BUCKET_REQUIRED")
    done=_root()+"/complete.json"
    if vault._head(done) is not None:
        pointer=json.loads(vault._get_small(done,2048))
        h=pointer.get("sha256")
        _check(isinstance(h,str) and re.fullmatch(r"[0-9a-f]{64}",h) is not None,
               "V37B_COMPLETED_POINTER_BAD")
        blob=vault._get_small(f"{_root()}/report-{h}.json",CAP)
        _check(sha(blob)==h,"V37B_PRIOR_RESULT_TAMPERED")
        return {"status":"V37B_ALREADY_DONE_NO_CHARGE","report_sha256":h,
                "model_calls_now":0}
    evidence=frozen_evidence(vault)
    menus={
        "first":sentence_menu(evidence["original_draft"],"I"),
        "revised":sentence_menu(evidence["revised_draft"],"R"),
    }
    requestA=_source_input(evidence)
    requestB=_draft_input(evidence,menus)
    _check(len(requestA)<=16000 and len(requestB)<=22000,
           "V37B_PROMPT_EXCEEDS_BOUND")
    start=_root()+"/started.json"
    _check(vault._head(start) is None,"V37B_ALREADY_ATTEMPTED_NO_RECHARGE")
    body=canonical({
        "session":SESSION,"original_stage_sha256s":evidence["stage_sha256s"],
        "review_protocol":"two distinct models, two separate smaller phases",
        "no_official_literary_quality_claim":True,
    })
    vault._put_small_immutable(start,body,sha(body))
    _check(vault._get_small(start,2048)==body,"V37B_START_NOT_RECOVERABLE")
    budget=DiscoveryCallBudget(max_calls=4,max_reserved_output_tokens=26500)
    if models_factory is None:
        key=os.environ.get("DISCOVERY_API_KEY","")
        _check(isinstance(key,str) and len(key)>=12,"V37B_MODEL_SECRET_MISSING")
        def models_factory(name):
            return DiscoveryModel(name=name,role="critic",api_key=key,budget=budget)
    results=[]
    failures=[]
    try:
        for model_id in CRITICS:
            agent=models_factory(model_id)
            for phase,user,max_tokens in (
                ("source",requestA,5100),("draft",requestB,6700)):
                try:
                    reply=agent.ask(
                        "你是与WF学习/创作模型独立的文学审查者。"
                        "只能评判指定阶段，不得帮助WF修改原著理解、"
                        "写前决策或正文。缺少证据应选择 UNCERTAIN、"
                        "NOT_OBSERVED 或 MISSING，不得杜撰引文和评分。"
                        "严格只输出一个完整JSON对象，字段恰好与任务约定一致。",
                        user,num_predict=max_tokens)
                    raw_sha=_record(vault,
                        f"unfiltered-{model_id}-{phase}",{
                            "model":model_id,"phase":phase,
                            "unmodified_model_response":reply,
                            "before_validation":True,
                            "source_sha256s":evidence["stage_sha256s"],
                            "no_learning_or_writing_by_this_critic":True})
                    try:
                        parsed=(validate_source_phase(reply) if phase=="source"
                                else validate_draft_phase(reply,menus))
                        results.append(_safe_public(vault,model_id,phase,
                                                    parsed,raw_sha))
                    except L2SplitReviewError as err:
                        failures.append({
                            "model":model_id,"phase":phase,
                            "failure_code":str(err),
                            "raw_response_sha256":raw_sha,
                            "no_invented_model_judgment":True})
                except (DiscoveryError,L2SplitReviewError) as err:
                    msg=str(err)
                    if not re.fullmatch("[A-Z0-9_]{3,96}",msg or ""):
                        msg=type(err).__name__
                    failures.append({"model":model_id,"phase":phase,
                                     "failure_code":msg,
                                     "no_invented_model_judgment":True})
        complete=len(results)==4 and not failures
        by_model={m:{
            p:next((x for x in results
                    if x["model"]==m and x["phase"]==p),None)
            for p in ("source","draft")} for m in CRITICS}
        agreement={}
        if complete:
            for field in (*SOURCE_ENUM,*DRAFT_ENUM):
                phase="source" if field in SOURCE_ENUM else "draft"
                left=by_model[CRITICS[0]][phase][field]
                right=by_model[CRITICS[1]][phase][field]
                agreement[field]=(left==right)
        report={
            "format":"writerforge.v37b-L2-diagnostic.v1",
            "status":("FOUR_VALID_INDEPENDENT_MODEL_PHASES"
                      if complete else "INCOMPLETE_MODEL_EVIDENCE_NO_CONCLUSION"),
            "stage_sha256s":evidence["stage_sha256s"],
            "old_v37_schema_failure_preserved":True,
            "source_and_drafts_not_edited":True,
            "frozen_student_prewrite":True,
            "critic_models":list(CRITICS),
            "per_model_per_phase":results,
            "invalid_model_phases":failures,
            "two_critic_agreement_by_field":agreement,
            "any_critic_disagreement_in_selected_fields":(
                complete and not all(agreement.values())),
            "no_score_averages":True,
            "literary_causality_not_independently_human_verified":True,
            "learned_skill_not_promoted":True,
            "model_calls":budget.calls,
            "reported_input_tokens":budget.total_prompt_tokens,
            "reported_output_tokens":budget.total_completion_tokens,
            "first_window":"NOT_PASSED","second_window":"LOCKED",
        }
        h=_record(vault,"report",report)
        pointer=canonical({"session":SESSION,"sha256":h})
        _check(vault._head(done) is None,"V37B_CONCURRENT_FINALIZATION")
        vault.client.put_object(Bucket=vault.config.bucket,Key=done,
                                Body=pointer,ContentType="application/json")
        _check(vault._get_small(done,2048)==pointer,
               "V37B_FINAL_POINTER_NOT_RECOVERABLE")
        return {"status":report["status"],"report_sha256":h,
                "opinions":results,"failures":failures,"agreement":agreement,
                "model_calls":budget.calls,
                "literary_progress_proven":False}
    except Exception as err:
        code=str(err)
        if not re.fullmatch("[A-Z0-9_]{3,96}",code or ""):
            code=type(err).__name__
        h=_record(vault,"failed",{
            "format":"writerforge.v37b-failure.v1",
            "code":code,"model_calls":budget.calls,
            "successful_phase_count":len(results),
            "old_learning_and_writing_stages_unchanged":True,
        })
        print(json.dumps({"stage":"V37B_FAILED","code":code,
                          "private_failure_sha256":h,
                          "model_calls":budget.calls},ensure_ascii=False))
        raise

if __name__=="__main__":
    try:
        print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
    except Exception as exc:
        code=str(exc)
        if not re.fullmatch("[A-Z0-9_]{3,96}",code or ""):code=type(exc).__name__
        print(json.dumps({"stage":"V37B_INCOMPLETE","code":code,
                          "did_not_retrain_WF":True}),file=sys.stderr)
        raise SystemExit(1)
