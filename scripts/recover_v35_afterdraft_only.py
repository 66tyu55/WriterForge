"""V35 append-only after-draft examination repair (NO retraining, NO rewrites).

Reuses immutable real Xi You Ji stage-03 prewrite and stage-05 revised
manuscript. Every new model answer, including invalid attempts, is saved as
separate private R2 evidence. WF must select quotations from deterministically
extracted lines of its own frozen prose; examiner never supplies suggested
literary tactics. No score or core promotion is inferred.
"""
from __future__ import annotations
import os,json,re
from hashlib import sha256
from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.reverse_discovery_models import (
    DiscoveryModel,DiscoveryCallBudget,DiscoveryError,
)
from writerforge.v35_observable_trace import validate_after,TraceContractError,sha,canonical
from scripts.run_v35_xiyouji_decision_trace import (
    restore_stage,SESSION as BASE_SESSION,
)
from writerforge.v35_xiyouji_exam import task,manifest_sha

PREFIX="writerforge/v1/examiner/v35-after-draft-observation-repair"
SESSION="20261017-v35-original-essay-only-retrospect-correct-quote-v1"

def _root():return PREFIX+"/"+SESSION

def _put(vault,name,doc):
    data=_canonical(doc)
    if len(data)>36000:raise TraceContractError("RETROSPECT_RECORD_TOO_LARGE")
    h=sha(data);path=_root()+"/"+name+"-"+h+".json"
    vault._put_small_immutable(path,data,h)
    if vault._get_small(path,36000)!=data:
        raise TraceContractError("RETROSPECT_R2_DIGEST_MISMATCH")
    return h

def _stages(vault):
    current=None;records=[]
    for stage in range(6):
        r=restore_stage(vault,stage,current)
        if r is None:raise TraceContractError("PREVIOUS_REAL_STAGE_MISSING")
        records.append(r[0]);current=r[1]
    plan=records[3]["payload"]["plan"]
    first=records[4]["payload"]["body"]
    last=records[5]["payload"]
    final=(last["edited_draft"]["body"] if last["edited"] else first)
    if (last["final_body_sha256"]!=sha(final)
        or last["retained_original_draft_stage_sha256"]!=
            sha(canonical(records[4]["payload"]))
        or records[3]["payload"]["exam"]["manifest_sha256"]!=manifest_sha()):
        raise TraceContractError("FROZEN_ESSAY_OR_PREPLAN_INTEGRITY_FAILURE")
    return {"plan":plan,"final_text":final,"original":first,
            "original_stage5_sha256":current,
            "original_stage3_sha256":sha(canonical(records[3])),
            "original_session":BASE_SESSION}

def _quote_menu(text):
    parts=re.split(r"(?<=[。！？!?])",text)
    selected=[]
    for p in parts:
        s=p.strip()
        if len(s)>=13:
            s=s[:min(len(s),55)]
            if s not in selected:selected.append(s)
        if len(selected)>=20:break
    if len(selected)<2:raise TraceContractError("FROZEN_ESSAY_HAS_TOO_FEW_VERIFIABLE_SENTENCES")
    return {f"Q{i+1}":s for i,s in enumerate(selected)}

def run():
    config=R2Config.from_environment()
    if config.bucket!="writerforge-private-library":
        raise TraceContractError("PRIVATE_R2_ONLY")
    vault=R2StudyVault(config)
    records=_stages(vault)
    menu=_quote_menu(records["final_text"])
    started=_root()+"/started.json"
    if vault._head(started) is not None:
        raise TraceContractError("AFTER_DRAFT_REVIEW_ALREADY_ATTEMPTED_NO_REPEAT")
    _put(vault,"started",{"session":SESSION,"original_stage5_sha256":
        records["original_stage5_sha256"],"only_reviewer_records":True})
    # An explicit started key is placed in content-addressed record above.
    # No silent attempt repeated, even on a validation failure.
    body=_canonical({"session":SESSION,
                     "original_stage5_sha256":records["original_stage5_sha256"],
                     "once":True})
    vault._put_small_immutable(started,body,sha(body))
    budget=DiscoveryCallBudget(max_calls=3,max_reserved_output_tokens=15500)
    key=os.environ.get("DISCOVERY_API_KEY","")
    if len(key)<12:raise DiscoveryError("REVIEW_MODEL_KEY_UNAVAILABLE")
    reviewer=DiscoveryModel(name="deepseek-v4-flash-0731",
        role="planner",api_key=key,budget=budget)
    plan=records["plan"]
    for attempt in range(2):
        result=reviewer.ask(
            "你是WF内部写后复盘模块，已写完的原始作文和写前决策都被锁定。"
            "禁止修改它们。要诚实审查是否真正采用所选叙事手法，"
            "不能凭空制造正文引文；请从给出的正文引用菜单原样"
            "复制完整文字，引用菜单由考官程序机械提取，不包含写法建议。"
            "只输出JSON，缺点要具体，不给自己评分。",
            "考前不可变构思："+json.dumps(plan["decisions"],ensure_ascii=False)+
            "\n已写完的原始考卷："+records["final_text"]+
            "\n从实际正文抽出的引用菜单："+json.dumps(menu,ensure_ascii=False)+
            "\n返回JSON仅有 checks/biggest_mistake。checks为2至4项，"
            "每项严格含 angle(须匹配考前计划)、"
            "actual_draft_quote(必须是上述Q菜单中的某个完整文本值，不能改写)、"
            "followed_prewrite_plan(布尔)、observed_gap(原因或未完成之处)、"
            "possible_next_revision(下一次写作应检验的行动，不修改本次稿)。"
            "biggest_mistake 是一个具体缺陷。"
            +(("\n上一版写后反思没有通过考官机器校验。这一版仍禁止"
               "更改已封存的思考和正文，务必逐字复制引用菜单的文字。")
              if attempt else ""),
            num_predict=4600)
        _put(vault,f"unfiltered-retrospective-{attempt+1}",{
            "phase":"MODEL_SELF_REVIEW_OUTPUT_BEFORE_EXAMINER_VALIDATION",
            "attempt":attempt+1,"raw_reply":result,
            "original_stage5_sha256":records["original_stage5_sha256"],
            "text_is_model_report_not_hidden_reasoning":True})
        try:
            validated=validate_after(result,records["final_text"],plan)
            if any(x["actual_draft_quote"] not in menu.values()
                   for x in validated["checks"]):
                raise TraceContractError("REVIEW_SELECTED_QUOTE_OUTSIDE_REAL_MENU")
            validated["original_v35_bad_quote_attempt_already_recorded"]=True
            validated["source_manifest_sha256"]=manifest_sha()
            validated["original_frozen_prewrite_sha256"]=records["original_stage3_sha256"]
            validated["original_frozen_final_draft_sha256"]=sha(records["final_text"])
            validated["repair_did_not_change_story_or_preplan"]=True
            valid_sha=_put(vault,"valid-retrospective",validated)
            decision_angles={x["angle"] for x in plan["decisions"]}
            cited_angles={x["angle"] for x in validated["checks"]}
            audit={
                "phase":"HOST_EXAMINER_AFTER_TRACE_QUOTE_VERIFIED",
                "original_training_completed_through_stage5":True,
                "original_self_quote_error_preserved":True,
                "frozen_original_essay_sha256":sha(records["final_text"]),
                "frozen_prewrite_sha256":records["original_stage3_sha256"],
                "new_visible_retrospective_record_sha256":valid_sha,
                "cited_angles":sorted(cited_angles),
                "uncited_prewrite_angles":sorted(decision_angles-cited_angles),
                "self_reported_not_followed":sum(
                    not x["followed_prewrite_plan"] for x in validated["checks"]),
                "real_source_and_draft_quotes_machine_verified":True,
                "independent_literary_quality_validation":False,
                "official_core_promoted":False,
                "model_calls_total":budget.calls,
            }
            audit_sha=_put(vault,"append-only-examiner-audit",audit)
            return {"status":"V35_AFTER_TRACE_SALVAGED_WITH_EXACT_EVIDENCE",
                    "revised_retrospect_sha256":valid_sha,
                    "examiner_audit_sha256":audit_sha,
                    "original_v35_stage5_sha256":records["original_stage5_sha256"],
                    "valid_checks":len(validated["checks"]),
                    "model_calls":budget.calls,
                    "no_originals_rewritten":True,"literary_progress_not_proven":True}
        except TraceContractError as e:
            _put(vault,f"failed-retrospect-validation-{attempt+1}",{
                "code":str(e),
                "attempt":attempt+1,
                "text_and_prior_prewrite_not_modified":True})
    return {"status":"V35_REPEAT_SELF_REVIEW_STILL_INVALID",
            "model_calls":budget.calls,
            "prior_successful_stages_unchanged":True,
            "literary_progress_not_proven":True}

if __name__=="__main__":
    result=run()
    print(json.dumps(result,ensure_ascii=False,sort_keys=True),flush=True)
