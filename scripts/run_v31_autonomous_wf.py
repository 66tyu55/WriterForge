"""WF's own 3-cycle learning trial: no external critics or manual corrections.

All stories/tasks/defect hypotheses originate inside the WF models. Only
abstract, draft-copy-screened rules survive as immutable R2 experimental
memory. These are NOT officially promoted skill improvements.
"""
from __future__ import annotations
import json,os,sys
from writerforge.r2_storage import R2Config,R2StudyVault
from writerforge.reverse_discovery_models import (
    DiscoveryModel,DiscoveryCallBudget,DiscoveryError,ROLE_MODELS,
)
from writerforge.v31_stage_evidence import (
    get_stage,commit_stage,claim_stage,record_sha,record_bytes,
)
from writerforge.v31_autonomous_core import (
    MAX_ROUNDS,AutonomousLearningError,digest,canonical,
    task_prompt,validate_task,writer_instruction,self_review_prompt,
    evaluate_self_proposal,self_blind_prompt,validate_self_comparison,
)

def _models(key,budget):
    return (
        DiscoveryModel(role="planner",name=ROLE_MODELS["planner"],
                       api_key=key,budget=budget),
        DiscoveryModel(role="writer",name=ROLE_MODELS["writer"],
                       api_key=key,budget=budget,reasoning_effort="low"),
    )

def _draft(result):
    value=result.get("scene") if isinstance(result,dict) else None
    if not isinstance(value,str) or not 350<=len(value)<=4500:
        raise AutonomousLearningError("SELF_DRAFT_FAILED_BOUNDEDNESS")
    return value

def _usage(budget):
    return {"calls":budget.calls,
            "by_role":dict(budget.calls_by_role),
            "tokens_input_reported":budget.total_prompt_tokens,
            "tokens_output_reported":budget.total_completion_tokens,
            "reserved_tokens":budget.reserved_output_tokens}

def _prior(vault,index):
    if index==1:return [],[],None
    previous=get_stage(vault,index-1)
    if previous is None:raise AutonomousLearningError("MISSING_PRIOR_IMMUTABLE_ROUND")
    doc,parent=previous
    cards=doc.get("memory")
    hashes=doc.get("task_hashes")
    if (not isinstance(cards,list) or len(cards)>2
        or not isinstance(hashes,list) or len(hashes)!=index-1):
        raise AutonomousLearningError("INVALID_R2_MEMORY_CHAIN")
    return cards,hashes,parent

def round_one(vault,index,models):
    cached=get_stage(vault,index)
    if cached is not None:return cached
    before,history,parent=_prior(vault,index)
    claim_stage(vault,index)
    budget=DiscoveryCallBudget(max_calls=6,max_reserved_output_tokens=37000)
    learner,novelist=models(budget)
    task=validate_task(learner.ask(
        "你是WriterForge自身的试题生成模块。独立设定原创首章题目，"
        "不请求外部建议，不借用现成小说情节。只返回JSON。",
        task_prompt(index,history),num_predict=3000),history)
    task_id=digest(task)
    draft=_draft(novelist.ask(
        "你是WriterForge自身小说创作模块。仅输出真正的原创第一章正文，"
        "自己完成场景因果、人物反应和尾部悬念，不输出解释。",
        writer_instruction(task,tuple(before)),num_predict=8500))
    status="INVALID_SELF_REVIEW_NO_MEMORY_CHANGE"
    after=tuple(before)
    decision={"decision":"SELF_REVIEW_INVALID","changed":False}
    violations=[]
    for n in range(2):
        try:
            reply=learner.ask(
                "你是WriterForge的内部学习反思模块。严查自己所写故事的"
                "具体失误，再自主决定增加、替换或拒绝实验技巧；"
                "不要向外部评审寻求帮助，只返回严格JSON。",
                self_review_prompt(task,draft,tuple(before))+
                ("\n上一次自评协议不合格，请自己检查JSON字段和正文证据。"
                 if n else ""),num_predict=3300)
            after,decision=evaluate_self_proposal(
                reply,own_draft=draft,current_cards=tuple(before))
            status="SELF_RULE_DECISION_VALIDATED_AS_EXPERIMENT"
            break
        except AutonomousLearningError as exc:
            violations.append(str(exc))
        except DiscoveryError as exc:
            violations.append(str(exc))
            break
    doc={
        "phase":"LEARN_WRITE_SELF_REVIEW",
        "parent_sha256":parent,
        "task_hashes":history+[task_id],
        "self_generated_task_sha256":task_id,
        "self_generated_draft_sha256":digest(draft),
        "draft_length":len(draft),
        "prior_memory_hashes":[digest(canonical(c)) for c in before],
        "memory":list(after),
        "learned_rule_action":decision,
        "self_review_status":status,
        "self_review_protocol_failures":violations,
        "reviewer_external":False,
        "original_full_draft_retained":False,
        "models_used":{"WF_internal_task_and_self_review":ROLE_MODELS["planner"],
                       "WF_internal_novel_writer":ROLE_MODELS["writer"]},
        "usage":_usage(budget),
        "literary_improvement_verified":False,
    }
    return commit_stage(vault,index,doc)

def final_challenge(vault,models):
    index=MAX_ROUNDS+1
    cached=get_stage(vault,index)
    if cached is not None:return cached
    before,history,parent=_prior(vault,index)
    claim_stage(vault,index)
    if not before:
        return commit_stage(vault,index,{
            "phase":"NO_TRANSFER_RULE_SURVIVED_SELF_REVIEW",
            "parent_sha256":parent,"task_hashes":history,
            "memory":[],"candidate_transfer_test_done":False,
            "literary_improvement_verified":False,"usage":{"calls":0},
        })
    budget=DiscoveryCallBudget(max_calls=7,max_reserved_output_tokens=39000)
    learner,novelist=models(budget)
    new_task=validate_task(learner.ask(
        "你是WriterForge自身的全新迁移试题模块。独立设计陌生情节，"
        "不得接受外部文学建议，只返回JSON。",
        task_prompt(index,history),num_predict=2900),history)
    drafts={}
    for label,cards in (("without_memory",()),("with_memory",tuple(before))):
        drafts[label]=_draft(novelist.ask(
            "你是WF内部创作模块。独立写全新小说第一章。"
            "只输出正文，不谈是否使用内部记忆，不依赖外部专家。",
            writer_instruction(new_task,cards),num_predict=8500))
    if digest(drafts["without_memory"])==digest(drafts["with_memory"]):
        return commit_stage(vault,index,{
            "phase":"IDENTICAL_TRANSFER_DRAFTS_NO_GAIN",
            "parent_sha256":parent,
            "task_hashes":history+[digest(new_task)],
            "memory":list(before),
            "fresh_task_sha256":digest(new_task),
            "draft_sha256":digest(drafts["with_memory"]),
            "candidate_transfer_test_done":True,
            "identical_drafts_not_scorable_for_improvement":True,
            "literary_improvement_verified":False,
            "usage":_usage(budget),
        })
    order=sorted(drafts,key=lambda x:digest(drafts[x]))
    anon={"A":drafts[order[0]],"B":drafts[order[1]]}
    review=validate_self_comparison(
        learner.ask("你是WriterForge内部自检模块，不是外部文学评论者；"
                    "只返回JSON，不用平均分掩盖任何缺点。",
                    self_blind_prompt(new_task,anon),num_predict=3300),
        anon,order)
    lengths={k:len(v) for k,v in drafts.items()}
    comparable=(abs(lengths["without_memory"]-lengths["with_memory"])
                /max(lengths.values())<=.15)
    return commit_stage(vault,index,{
        "phase":"INTERNAL_FRESH_TRANSFER_PROBE",
        "parent_sha256":parent,"task_hashes":history+[digest(new_task)],
        "memory":list(before),
        "with_memory_input_rule_hashes":[digest(canonical(c)) for c in before],
        "fresh_task_sha256":digest(new_task),
        "draft_hashes":{k:digest(v) for k,v in drafts.items()},
        "draft_lengths":lengths,
        "relative_length_comparable":comparable,
        "self_assessed_only":review,
        "candidate_transfer_test_done":True,
        "original_full_draft_retained":False,
        "literary_improvement_verified":False,
        "usage":_usage(budget),
    })

def audit(vault):
    history=[]
    previous=None
    for n in range(1,MAX_ROUNDS+2):
        entry=get_stage(vault,n)
        if entry is None:
            history.append({"round":n,"status":"NOT_COMPLETED"})
            break
        record,h=entry
        if record.get("parent_sha256")!=previous:
            raise AutonomousLearningError("BROKEN_IMMUTABLE_MEMORY_PARENT")
        previous=h
        history.append({
            "round":n,"phase":record.get("phase"),
            "snapshot_sha256":h,
            "rules_available_after_round":len(record.get("memory",[])),
            "rules_loaded_from_prior_round":len(record.get("prior_memory_hashes",[])),
            "self_rule_decision":record.get("learned_rule_action",{}).get("decision"),
            "self_rule_changed":record.get("learned_rule_action",{}).get("changed"),
            "model_calls":record.get("usage",{}).get("calls",0),
            "transfer_test_done":record.get("candidate_transfer_test_done"),
            "transfer_relative_length_comparable":record.get("relative_length_comparable"),
            "self_reported_negative_transfer_dimensions":record.get(
                "self_assessed_only",{}).get("negative_dimensions_uncancelled",{}),
        })
    return {
        "status":"AUTONOMOUS_THREE_ROUND_SELF_EVOLUTION_TRIAL",
        "completed_all_stages":len(history)==4 and all(
            "snapshot_sha256" in x for x in history),
        "number_of_completed_learning_rounds":sum(
            x.get("phase")=="LEARN_WRITE_SELF_REVIEW" for x in history),
        "self_rule_changes":sum(x.get("self_rule_changed") is True for x in history),
        "immutable_memory_snapshots":history,
        "external_human_critic_or_literary_edits":False,
        "independent_literary_improvement_verified":False,
        "official_core_promoted":False,
        "first_window":"NOT_PASSED","second_window":"LOCKED",
    }

def run(vault,models):
    if vault.config.bucket!="writerforge-private-library":
        raise AutonomousLearningError("SELF_RUN_PRIVATE_BUCKET_REQUIRED")
    for n in range(1,MAX_ROUNDS+1):
        round_one(vault,n,models)
    final_challenge(vault,models)
    return audit(vault)

def main():
    token=os.environ.get("DISCOVERY_API_KEY","")
    if not isinstance(token,str) or len(token)<12:
        raise DiscoveryError("SELF_RUN_KEY_UNAVAILABLE")
    vault=R2StudyVault(R2Config.from_environment())
    def models(budget):
        return _models(token,budget)
    return run(vault,models)

if __name__=="__main__":
    try:
        print(json.dumps(main(),ensure_ascii=False,sort_keys=True),flush=True)
    except Exception as exc:
        status=str(exc) if isinstance(exc,(DiscoveryError,AutonomousLearningError,ValueError)) else type(exc).__name__
        if not status or len(status)>90 or not all(
            c.isupper() or c.isdigit() or c=="_" for c in status):
            status=type(exc).__name__
        print(json.dumps({"status":"SELF_EVOLUTION_PILOT_INCOMPLETE",
                          "failure_code":status,"no_external_rescue":True,
                          "official_promotion":False},ensure_ascii=False),
              file=sys.stderr,flush=True)
        raise SystemExit(1)
