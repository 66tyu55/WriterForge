"""V37 L2-only forensic reader: immutable V35 originals, no new prose.

Two independent non-WF critics inspect the actual classic-reading hypothesis,
frozen prewrite L2 foreshadowing choice, and untouched first/revised stories.
Their explicit evidence cites HOST sentence IDs from those exact manuscripts.

Never publish private original prose, model hypotheses or detailed critiques
via GitHub Actions. Full reviewer outputs live in PRIVATE R2, raw first.
Neither one critic nor agreement is human proof of a literary skill.
"""
from __future__ import annotations
from hashlib import sha256
import json,os,re,sys
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_discovery_models import (
    DiscoveryModel,DiscoveryCallBudget,DiscoveryError,
)
from writerforge.v35_observable_trace import sha,canonical
from writerforge.v35_xiyouji_exam import task
from scripts.run_v35_xiyouji_decision_trace import restore_stage
from scripts.debug_v36_xiyouji_learning_to_writing import (
    EXPECTED_ORIGINAL_SHA,AFTER_SHA,AFTER_EXAMINER_SHA,
    analyze as source_audit,
)
from writerforge.v33_exam_contracts import ExamContractError

ROOT="writerforge/v1/examiner/v37-xiyouji-L2-foreshadowing-forensic"
SESSION="20261017-L2-only-frozen-craft-decision-forensic-v1"
CRITICS=("deepseek-v4-pro-0813","minimax-m3")
MAX_PRIVATE=35000
FIELDS={
    "source_support","abstraction_fidelity","task_fit",
    "first_execution","revised_execution","foreshadow_payoff",
    "first_setup_ids","first_payoff_ids","revised_setup_ids",
    "revised_payoff_ids","source_reason","abstraction_reason",
    "task_reason","execution_reason","uncertainty",
}
SCHEMA={
    "source_support":{"SUPPORTED","PARTIAL","UNSUPPORTED","UNCERTAIN"},
    "abstraction_fidelity":{"FAITHFUL","PARTIAL","DISTORTED","UNCERTAIN"},
    "task_fit":{"APPROPRIATE","RISKY","INAPPROPRIATE","UNCERTAIN"},
    "first_execution":{"OBSERVED","PARTIAL","NOT_OBSERVED","UNCERTAIN"},
    "revised_execution":{"OBSERVED","PARTIAL","NOT_OBSERVED","UNCERTAIN"},
    "foreshadow_payoff":{"GROUNDED","WEAK","MISSING","UNCERTAIN"},
}

class L2ForensicError(ValueError):pass

def _need(test:bool,code:str):
    if not test:raise L2ForensicError(code)

def _read(vault,key,h):
    data=vault._get_small(key,MAX_PRIVATE)
    _need(sha(data)==h,"PRIVATE_FORENSIC_SHA_MISMATCH")
    return json.loads(data)

def _put(vault,path,value):
    data=canonical(value)
    _need(len(data)<=MAX_PRIVATE,"PRIVATE_FORENSIC_OVERSIZE")
    h=sha(data)
    key=f"{ROOT}/{SESSION}/{path}-{h}.json"
    vault._put_small_immutable(key,data,h)
    _need(vault._get_small(key,MAX_PRIVATE)==data,
          "PRIVATE_FORENSIC_R2_GET_MISMATCH")
    return h

def frozen_evidence(vault):
    _need(vault.config.bucket=="writerforge-private-library",
          "ONLY_PRIVATE_R2_ALLOWED")
    # First run the independent V36 source/stage/trace debugger, without
    # creating another V36 report or accessing model endpoints.
    parent=source_audit(vault,persist=False)
    _need(parent["transfer_trace"]["source_linked_prewrite_angles"]==
          ["foreshadowing"] and
          parent["transfer_trace"]["source_linked_angles_missing_postwrite_evidence"]==
          ["foreshadowing"],"V36_PRIOR_UNEXAMINED_L2_STATE_CHANGED")
    records=[]
    prior=None
    for index,h in enumerate(EXPECTED_ORIGINAL_SHA):
        item=restore_stage(vault,index,prior)
        _need(item is not None and item[1]==h,"V35_ORIGINAL_SOURCE_SHA_CHANGED")
        records.append(item[0]["payload"])
        prior=h
    source,observed,studied,prepared,first,edited=records
    _need(len(studied["lessons"])==2 and
          studied["lessons"][1]["id"]=="L2",
          "L2_NOT_IN_ORIGINAL_STUDY_RECORD")
    lesson=studied["lessons"][1]
    observation_index=lesson["source_observation_index"]
    _need(type(observation_index) is int and
          0<=observation_index<len(observed["observations"]),
          "L2_SOURCE_OBSERVATION_MISSING")
    seen=observed["observations"][observation_index]
    chapter=seen["chapter"]
    source_window=source["actual_model_read_windows"][str(chapter)]
    _need("".join(seen["source_quote"].split()) in
          "".join(source_window.split()),
          "L2_ORIGINAL_EXCERPT_NOT_IN_CHAPTER")
    linked=[x for x in prepared["plan"]["decisions"]
            if x["learned_lesson_id"]=="L2"]
    _need(len(linked)==1 and linked[0]["angle"]=="foreshadowing",
          "L2_PREWRITE_NOT_UNIQUE_OR_FROZEN")
    _need(prepared["exam"]["examiner_task"]==task(),
          "L2_EXAM_QUESTION_CHANGED")
    original=first["body"]
    revised=edited["edited_draft"]["body"] if edited["edited"] else original
    _need(sha(original)==first["body_sha256"] and
          sha(revised)==edited["final_body_sha256"] and
          len(original)==904 and len(revised)==1136,
          "L2_FIRST_OR_REVISED_ESSAY_CHANGED")
    return {
        "source_chapter":chapter,
        "source_window":source_window,
        "original_observation":seen,
        "original_lesson":lesson,
        "frozen_foreshadowing_decision":linked[0],
        "original_draft":original,
        "revised_draft":revised,
        "parent_v36_trace_sha256":parent["new_debugger_report_sha256"],
        "stage_sha256s":list(EXPECTED_ORIGINAL_SHA),
    }

def sentence_menu(text:str,prefix:str)->list[dict]:
    """Deterministic offset-verified sentence boundaries; preserve duplicates."""
    if not isinstance(text,str) or not 200<=len(text)<=4500:
        raise L2ForensicError("MANUSCRIPT_LENGTH_INVALID")
    segments=[]
    # Include the punctuation mark with its sentence and preserve offsets.
    for match in re.finditer(r"[^。！？；\n]+[。！？；]?|\n",text):
        raw=match.group()
        clean=raw.strip()
        if not clean or len(clean)<5:continue
        start=match.start()+len(raw)-len(raw.lstrip())
        end=start+len(clean)
        _need(text[start:end]==clean,"SENTENCE_OFFSET_MISMATCH")
        segments.append({"id":f"{prefix}{len(segments)+1:02d}",
                         "start":start,"end":end,
                         "text":clean,"text_sha256":sha(clean)})
    _need(5<=len(segments)<=100,"UNSAFE_SENTENCE_MENU_COUNT")
    return segments

def prompt(evidence:dict,menu_first:list,menu_revised:list)->str:
    return json.dumps({
        "purpose":"independent literary diagnostics; not learning or writing advice",
        "source_chapter":evidence["source_chapter"],
        "source_window_from_authentic_original":evidence["source_window"],
        "WF_first_reading_observation_hypothesis":evidence["original_observation"],
        "WF_L2_craft_hypothesis_before_exam":evidence["original_lesson"],
        "frozen_prewrite_foreshadowing_choice_and_reason":
            evidence["frozen_foreshadowing_decision"],
        "independent_exam_question":task(),
        "first_unmodified_essay_sentences":menu_first,
        "later_revision_essay_sentences":menu_revised,
        "output_contract":{
            "fields":sorted(FIELDS),
            "source_support":sorted(SCHEMA["source_support"]),
            "abstraction_fidelity":sorted(SCHEMA["abstraction_fidelity"]),
            "task_fit":sorted(SCHEMA["task_fit"]),
            "first_execution":sorted(SCHEMA["first_execution"]),
            "revised_execution":sorted(SCHEMA["revised_execution"]),
            "foreshadow_payoff":sorted(SCHEMA["foreshadow_payoff"]),
            "all_sentence_id_fields":"arrays of IDs from the matching first/revised sentence menu; empty [] means cannot find evidence",
            "four_reason_fields":"source_reason, abstraction_reason, task_reason, execution_reason each 18..280 Chinese characters",
            "uncertainty":"18..280 characters",
        },
        "quality_rules":{
            "no_shortcuts":"do not assume source mention proves technique correct or that author's prewrite intent was executed",
            "setup_payoff":"if calling payoff GROUNDED, cite distinct setup and later payoff sentences from revised draft",
            "can_refuse":"for missing evidence return NOT_OBSERVED, MISSING or UNCERTAIN, never invent passages",
            "never_publish_full_text":"detailed assessment stored privately",
            "no_numeric_aggregate_scores":True,
        },
    },ensure_ascii=False,separators=(",",":"))

def _unwrap(reply):
    obj=reply
    for _ in range(3):
        if not isinstance(obj,dict):
            raise L2ForensicError("L2_CRITIC_RESPONSE_NOT_OBJECT")
        if set(obj)==FIELDS:return obj
        if len(obj)!=1:
            raise L2ForensicError("L2_CRITIC_FIELDS_MISSING_OR_EXTRA")
        k=next(iter(obj))
        if k not in ("result","review","analysis","data","evaluation"):
            raise L2ForensicError("L2_CRITIC_WRAPPER_UNRECOGNIZED")
        obj=obj[k]
    raise L2ForensicError("L2_CRITIC_SCHEMA_UNRECOVERABLE")

def _ids(reply,field:str,allowed:dict[str,dict],label:str):
    ids=reply[field]
    if (not isinstance(ids,list) or len(ids)>4 or
        any(not isinstance(i,str) or i not in allowed for i in ids)
        or len(set(ids))!=len(ids)):
        raise L2ForensicError("L2_UNKNOWN_OR_DUPLICATED_"+label+"_EVIDENCE_ID")
    return ids

def validate_review(reply,menus):
    record=_unwrap(reply)
    for name,choices in SCHEMA.items():
        if not isinstance(record[name],str) or record[name] not in choices:
            raise L2ForensicError("L2_CRITIC_ENUM_INVALID")
    for name in ("source_reason","abstraction_reason","task_reason",
                 "execution_reason","uncertainty"):
        if not isinstance(record[name],str) or not 18<=len(record[name].strip())<=280:
            raise L2ForensicError("L2_CRITIC_REASON_INVALID")
    allowed={
        "first":{x["id"]:x for x in menus["first"]},
        "revised":{x["id"]:x for x in menus["revised"]},
    }
    for field,kind in (("first_setup_ids","first"),("first_payoff_ids","first"),
                       ("revised_setup_ids","revised"),
                       ("revised_payoff_ids","revised")):
        _ids(record,field,allowed[kind],kind.upper())
    def order(setup_field,payoff_field,kind):
        a=record[setup_field];b=record[payoff_field]
        if a and b:
            first=min(allowed[kind][x]["start"] for x in a)
            last=max(allowed[kind][x]["start"] for x in b)
            if first>=last:
                raise L2ForensicError("L2_SETUP_PAYOFF_TEMPORAL_ORDER_INVALID")
    order("first_setup_ids","first_payoff_ids","first")
    order("revised_setup_ids","revised_payoff_ids","revised")
    if record["foreshadow_payoff"]=="GROUNDED":
        if not record["revised_setup_ids"] or not record["revised_payoff_ids"]:
            raise L2ForensicError("L2_GROUNDED_CLAIM_WITHOUT_EARLY_AND_LATE_QUOTES")
    for stage in ("first","revised"):
        if record[f"{stage}_execution"]=="NOT_OBSERVED" and (
            record[f"{stage}_setup_ids"] or record[f"{stage}_payoff_ids"]):
            raise L2ForensicError("L2_NO_EXECUTION_BUT_EVIDENCE_ASSERTED")
    return record

def public_summary(review,model,raw_sha):
    return {
        "reviewer_model":model,
        "original_private_review_sha256":raw_sha,
        "source_support":review["source_support"],
        "abstraction_fidelity":review["abstraction_fidelity"],
        "task_fit":review["task_fit"],
        "first_execution":review["first_execution"],
        "revised_execution":review["revised_execution"],
        "foreshadow_payoff":review["foreshadow_payoff"],
        "evidence_ids":{
            k:list(review[k]) for k in (
                "first_setup_ids","first_payoff_ids",
                "revised_setup_ids","revised_payoff_ids")},
        "model_opinion_not_independent_human_certification":True,
    }

def root():
    return f"{ROOT}/{SESSION}"

def run(vault=None,models_factory=None):
    vault=vault or R2StudyVault(R2Config.from_environment())
    if vault.config.bucket!="writerforge-private-library":
        raise L2ForensicError("PRIVATE_R2_ONLY")
    done=root()+"/complete.json"
    if vault._head(done) is not None:
        p=json.loads(vault._get_small(done,2048))
        h=p.get("sha256")
        if not isinstance(h,str) or not re.fullmatch("[0-9a-f]{64}",h):
            raise L2ForensicError("L2_PRIOR_RESULT_POINTER_INVALID")
        raw=vault._get_small(root()+f"/result-{h}.json",MAX_PRIVATE)
        _need(sha(raw)==h,"L2_PRIOR_RESULT_CHANGED")
        return {"status":"L2_EXISTING_REPORT_READ_BACK_NO_MODEL_CALLS",
                "report_sha256":h,"model_calls":0}
    evidence=frozen_evidence(vault)
    menus={
        "first":sentence_menu(evidence["original_draft"],"I"),
        "revised":sentence_menu(evidence["revised_draft"],"R"),
    }
    if vault._head(root()+"/started.json") is not None:
        raise L2ForensicError("L2_EXPERIMENT_ALREADY_STARTED_NO_REPEAT")
    start=canonical({
        "session":SESSION,"original_stages":evidence["stage_sha256s"],
        "v36_sha256":evidence["parent_v36_trace_sha256"],
        "critics":list(CRITICS),"budget_max_calls":4,
        "never_rewrite_literary_history":True,
    })
    vault._put_small_immutable(root()+"/started.json",start,sha(start))
    _need(vault._get_small(root()+"/started.json",2048)==start,
          "L2_START_CLAIM_NOT_RECOVERABLE")
    budget=DiscoveryCallBudget(max_calls=4,max_reserved_output_tokens=25500)
    key=os.environ.get("DISCOVERY_API_KEY","")
    if models_factory is None:
        _need(isinstance(key,str) and len(key)>12,"L2_DISCOVERY_KEY_UNAVAILABLE")
        def models_factory(name):
            return DiscoveryModel(name=name,role="critic",api_key=key,budget=budget)
    summaries=[]
    error_codes=[]
    try:
        inputs=prompt(evidence,menus["first"],menus["revised"])
        _need(len(inputs)<=24000,"L2_CRITIC_INPUT_TOO_LONG")
        for critic in CRITICS:
            model=models_factory(critic)
            validated=None
            for attempt in (1,2):
                response=model.ask(
                    "你是独立文学诊断考官，不是WF学习模块。你不知道WF是否写得好。"
                    "严格审阅《西遊記》局部原文是否真的支持抽象手法L2、"
                    "L2是否适合新的情境、首稿和修订稿是否分别出现"
                    "伏笔铺垫及后续回收。回答需要每一处具体原文句子ID，"
                    "引用可选择NONE而不是发明。不要以平均分取代缺点。"
                    "输出严格JSON，顶层含规定全部字段，不要额外文字。",
                    inputs+("\n【仅修复格式】上次的JSON字段或引用ID校验不合格。"
                            "不得改动考题、原著与作品，只重填严格格式字段。"
                            if attempt==2 else ""),
                    num_predict=5400)
                raw_sha=_put(vault,f"unvalidated-{critic}-{attempt}",{
                    "format":"writerforge.v37-private-raw-review.v1",
                    "reviewer":critic,"attempt":attempt,
                    "source_stage_sha256":EXPECTED_ORIGINAL_SHA[0],
                    "model_reply_unmodified":response,
                    "validated_at_this_point":False,
                    "literary_truth_not_certified":True,
                })
                try:
                    validated=validate_review(response,menus)
                    summaries.append(public_summary(validated,critic,raw_sha))
                    break
                except L2ForensicError as err:
                    code=str(err)
                    error_codes.append({"critic":critic,"attempt":attempt,
                                        "error_code":code,
                                        "unfiltered_response_sha256":raw_sha})
                    _put(vault,f"validation-error-{critic}-{attempt}",{
                        "model":critic,"attempt":attempt,
                        "reason_code":code,"raw_sha256":raw_sha,
                        "source_and_drafts_not_modified":True,
                    })
            if validated is None:
                break
        # No averaging of distinct model opinions. If either critic failed,
        # preserve the successful first opinion but DO NOT claim two reviews.
        complete=len(summaries)==len(CRITICS)
        labels=[x["source_support"] for x in summaries]
        fits=[x["task_fit"] for x in summaries]
        payoffs=[x["foreshadow_payoff"] for x in summaries]
        agreement=(complete and len(set(labels))==len(set(fits))==
                   len(set(payoffs))==1)
        result={
            "format":"writerforge.v37-L2-foreshadowing-forensic.v1",
            "status":("TWO_INDEPENDENT_CRITICS_VALID_NOT_HUMAN"
                      if complete else "INCOMPLETE_CRITIC_REVIEW_UNSCORED"),
            "source_provenance_full_original_stages":evidence["stage_sha256s"],
            "old_v35_recovered_review_preserved":AFTER_SHA,
            "linked_v36_debugger_sha256":evidence["parent_v36_trace_sha256"],
            "examiner_scope":"L2_ONLY_FORESHADOWING",
            "learner_plan_was_frozen_before_writing":True,
            "did_not_change_original_or_revised_novel":True,
            "original_essay_sha256":sha(evidence["original_draft"]),
            "revised_essay_sha256":sha(evidence["revised_draft"]),
            "sentence_menus_metadata":{
                kind:[{"id":s["id"],"start":s["start"],"end":s["end"],
                       "sha256":s["text_sha256"]} for s in rows]
                for kind,rows in menus.items()},
            "critics":summaries,
            "critic_data_validation_failures":error_codes,
            "two_critic_coarse_agreement":agreement,
            "averaging_contradictory_reviews":False,
            "human_reading_verification_done":False,
            "source_semantics_proved_objectively":False,
            "learned_skill_true_improvement_proven":False,
            "literary_skill_promoted":False,
            "model_calls":budget.calls,
            "reported_input_tokens":budget.total_prompt_tokens,
            "reported_output_tokens":budget.total_completion_tokens,
            "first_window":"NOT_PASSED","second_window":"LOCKED",
        }
        h=_put(vault,"result",result)
        pointer=canonical({"session":SESSION,"sha256":h})
        _need(vault._head(done) is None,"L2_COMPLETED_BEFORE_POINTER")
        vault.client.put_object(Bucket=vault.config.bucket,Key=done,
                                Body=pointer,ContentType="application/json")
        _need(vault._get_small(done,2048)==pointer,
              "L2_FINAL_POINTER_FRESH_READBACK_FAILED")
        return {"status":result["status"],"report_sha256":h,
                "models":summaries,"errors":error_codes,
                "two_critic_coarse_agreement":agreement,
                "original_and_revised_sha_unchanged":True,
                "model_calls":budget.calls,
                "literary_skill_promoted":False}
    except Exception as err:
        code=str(err)
        if not re.fullmatch("[A-Z0-9_]{3,96}",code or ""):
            code=type(err).__name__
        h=_put(vault,"failed",{
            "format":"writerforge.v37-actual-error.v1",
            "error_code":code,
            "previous_original_R2_stages_unchanged":True,
            "model_calls":budget.calls,
            "reviewer_models_partially_finished":len(summaries),
        })
        print(json.dumps({"status":"V37_FAILED_NO_FALSE_LITERARY_JUDGMENT",
                          "error_code":code,"private_failure_sha256":h,
                          "model_calls":budget.calls},ensure_ascii=False))
        raise

if __name__=="__main__":
    try:
        result=run()
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    except Exception as e:
        code=str(e)
        if not re.fullmatch("[A-Z0-9_]{3,96}",code or ""):
            code=type(e).__name__
        print(json.dumps({"status":"V37_NO_PASS",
                          "error_code":code,
                          "old_R2_not_overwritten":True}),file=sys.stderr)
        raise SystemExit(1)
