"""True old-WF vs opt-in semantic-WF A/B without leaking original text.

One SOURCE + one entirely new story task per trial. One old planner and one
semantic planner, same GLM writer, two draft manuscripts, one blinded Flash
critic. Model + role identity and text-length requirement are held fixed.
Only HOST-owned operations reach the Writer. No raw source/manuscript persisted.

One semantically unjustified selection may ABSTAIN before any writer call.
Abstention is distinct from literary quality, never made into a zero score.
"""
from __future__ import annotations
from hashlib import sha256
import json
from .reverse_real_training import raw_hash,_source_copy_guard
from .reverse_mechanism_boundary import (
    source_paragraphs,proposal_prompt,parse_selections,report_evidence,
    build_writer_packet,
)
from .reverse_semantic_evidence import (
    semantic_proposal_prompt,validate_semantic_selections,
)
from .reverse_cloud_ab import _choice_score,_brief,_has_long_exact_overlap,ABTrialError,DIMENSIONS

BUDGET_PROFILE=(4200,7700,6500)
COMMON_TARGET=1080
LENGTH_GATE=.15
LIMIT=4500

class LengthUnscorable(ABTrialError):
    """No literary score; bounded numeric diagnostics only, never raw prose."""
    def __init__(self,first_lengths:dict,final_lengths:dict):
        super().__init__("OLD_NEW_AB_LENGTH_MISMATCH_UNSCORABLE")
        self.safe_lengths={
            "initial":{name:int(first_lengths[name]) for name in ("legacy","semantic")},
            "after_symmetric_revision":{
                name:int(final_lengths[name]) for name in ("legacy","semantic")},
            "relative_final_difference":round(
                abs(final_lengths["legacy"]-final_lengths["semantic"])
                /max(final_lengths.values()),5),
            "no_literary_score":True,
        }

class SemanticTrialAbstained(ABTrialError):
    def __init__(self,reason:str,*,candidate:dict):
        super().__init__(reason)
        self.safe_candidate=candidate

def effective_task(task:str)->str:
    if not isinstance(task,str) or not 80<=len(task)<=800:
        raise ABTrialError("HOLDOUT_TASK_NOT_BOUNDED")
    return task+("\n本次两组共有相同的篇幅约束：包含标点约"
                 +str(COMMON_TARGET)+"个字符，容差8%；"
                 "用真正的叙事结束这一章，不写章节提纲。")

def compare_old_vs_semantic(*,planner,writer,critic,first:str,second:str,
                            source_sha:str,source_window_sha:str,
                            writing_task:str)->dict:
    if (writer.provider,writer.name)==(critic.provider,critic.name):
        raise ABTrialError("WRITER_CANNOT_CRITIQUE_ITSELF")
    if not isinstance(first,str) or not 300<=len(first)<=5500 or not second:
        raise ABTrialError("SOURCE_WINDOW_BOUND_INVALID")
    if raw_hash(first)!=source_window_sha:
        raise ABTrialError("SOURCE_WINDOW_SHA_CHANGED")
    if BUDGET_PROFILE[0]*2+BUDGET_PROFILE[1]*4+BUDGET_PROFILE[2]>50000:
        raise ABTrialError("UNSAFE_SHARED_OUTPUT_RESERVATION")
    task=effective_task(writing_task)
    paragraphs=source_paragraphs(first)
    old=planner.ask(
        "你是源文分析器；仅选择宿主预置机制，不将原著情节或人物告知作者。"
        "只输出宿主指定的完整JSON。",
        proposal_prompt(paragraphs),num_predict=BUDGET_PROFILE[0])
    old_sel=parse_selections(old,paragraphs)
    new=planner.ask(
        "你是严格文学源文与创作任务语义审核者。不得杜撰源段落。"
        "如不适用必须弃权。只返回严格符合宿主合同的JSON。",
        semantic_proposal_prompt(paragraphs,writing_task=task),
        num_predict=BUDGET_PROFILE[0])
    new_sel,semantic=validate_semantic_selections(
        new,paragraphs,writing_task=task)
    if not new_sel:
        raise SemanticTrialAbstained(
            "NO_SOURCE_SUPPORTED_NEW_MECHANISM",
            candidate={"format":semantic["format"],
                       "selected_count":0,
                       "model_decisions":[x["model_decision"]
                           for x in semantic["observed"]],
                       "literary_quality_score":None,
                       "automatic_core_promotion":False,
                       "source_window_sha256":source_window_sha,
                       "writing_task_sha256":raw_hash(task)})
    selections={"legacy":old_sel,"semantic":new_sel}
    packets={arm:build_writer_packet(sel,enhanced=True,writing_task=task)
             for arm,sel in selections.items()}
    outputs={}
    for arm in ("legacy","semantic"):
        data=writer.ask(
            "你是原创中文长篇小说作者。只输出自然连续的首章正文，不作分析，"
            "不得借用参考原著人物事件或世界观，不输出提纲、Markdown或标题。",
            json.dumps(packets[arm],ensure_ascii=False),
            num_predict=BUDGET_PROFILE[1])
        result=data.get("scene")
        if not isinstance(result,str) or not 220<=len(result)<=LIMIT:
            raise ABTrialError("WRITER_DRAFT_NOT_BOUNDED")
        _source_copy_guard(result,first)
        outputs[arm]=result
    before={arm:len(outputs[arm]) for arm in outputs}
    revisions=0
    if abs(len(outputs["legacy"])-len(outputs["semantic"]))/max(map(len,outputs.values()))>LENGTH_GATE:
        edited={}
        for arm in ("legacy","semantic"):
            result=writer.ask(
                "你是原创小说编辑。只对你收到的这一份草稿进行一次独立修订，"
                "保持主角动机、行动因果和真实悬念，不接触另一稿。"
                "本次精确目标为约1080个含标点字符。宿主已计算你的本稿真实"
                "长度与目标差值，请依据数字缩写或补写，以完整新章节正文收尾。"
                "不可简单截断结尾、堆积形容词或补无关事件，不要提纲或说明。",
                json.dumps({"writing_instruction":packets[arm],
                    "own_draft":outputs[arm],
                    "own_draft_characters_including_punctuation":len(outputs[arm]),
                    "target_chars":COMMON_TARGET,
                    "characters_to_change":COMMON_TARGET-len(outputs[arm]),
                    "valid_target_range":[int(COMMON_TARGET*.94),int(COMMON_TARGET*1.06)],
                    "other_arm_text_or_length_shared":False},
                    ensure_ascii=False),num_predict=BUDGET_PROFILE[1]).get("scene")
            if not isinstance(result,str) or not 220<=len(result)<=LIMIT:
                raise ABTrialError("SYMMETRIC_MANUSCRIPT_REVISION_INVALID")
            _source_copy_guard(result,first)
            edited[arm]=result
            revisions+=1
        outputs=edited
    chars={arm:len(text) for arm,text in outputs.items()}
    if abs(chars["legacy"]-chars["semantic"])/max(chars.values())>LENGTH_GATE:
        raise LengthUnscorable(before,chars)
    # Deterministic blinding by draft SHA, before reviewer is called.
    ordered=sorted(outputs,key=lambda arm:raw_hash(outputs[arm]))
    anon={chr(65+i):outputs[arm] for i,arm in enumerate(ordered)}
    critique=critic.ask(
        "你是盲评文学编辑，不知道稿件对应哪个写作协议。"
        "不猜提示词，不默认某稿更好。"
        "仅根据同一道原创首章任务及这两篇匿名作品，逐项给出"
        "perception、causality、information、continuity、language"
        "五维0-100整数评分和短评。返回JSON，"
        "顶层只能包含 A、B、uncertainty；A/B各包含五项，"
        "每项严格含 score 整数与 reason 4-180字字符串，"
        "uncertainty为对评审盲点的4-180字说明。",
        json.dumps({"task":task,**anon},ensure_ascii=False),
        num_predict=BUDGET_PROFILE[2])
    if not isinstance(critique,dict) or set(critique)!={"A","B","uncertainty"}:
        raise ABTrialError("UNVERIFIED_AB_CRITIC_SCHEMA")
    rated={k:_choice_score(critique[k],anon[k],first) for k in ("A","B")}
    uncertainty=_brief(critique["uncertainty"],"uncertainty")
    if _has_long_exact_overlap(uncertainty,first,*outputs.values()):
        uncertainty="REVIEW_NOTE_REDACTED_"+raw_hash(uncertainty)[:18]
    views={}
    for arm in ("legacy","semantic"):
        name="A" if ordered[0]==arm else "B"
        dim=rated[name]
        views[arm]={
            "draft_sha256":raw_hash(outputs[arm]),"draft_chars":chars[arm],
            "critic_anonymous_label":name,
            "dimensions":dim,
            "model_mean":round(sum(dim[d]["score"] for d in DIMENSIONS)/5,2),
            "mechanism_ids":[x["id"] for x in selections[arm]],
            "source_evidence_hashes":report_evidence(
                selections[arm],paragraphs),
        }
    return {
        "format":"writerforge.old-vs-semantic-a-b.v29",
        "source_work":"wudongqiankun",
        "source_sha256":source_sha,
        "source_unit_sha256":source_window_sha,
        "following_unit_sha256":raw_hash(second),
        "writing_task_sha256":raw_hash(writing_task),
        "effective_task_sha256":raw_hash(task),
        "role_output_budgets":list(BUDGET_PROFILE),
        "model_roles":{"planner":planner.name,"writer":writer.name,"critic":critic.name},
        "comparisons":views,
        "semantic_minus_legacy_model_mean":round(
            views["semantic"]["model_mean"]-views["legacy"]["model_mean"],2),
        "same_host_mechanisms_selected":(
            set(views["legacy"]["mechanism_ids"])==
            set(views["semantic"]["mechanism_ids"])),
        "semantic_model_evidence_candidate":semantic,
        "original_lengths_before_revision":before,
        "symmetric_revision_calls":revisions,
        "relative_length_gate_max":LENGTH_GATE,
        "reviewer_uncertainty":uncertainty,
        "source_sent_to_writer_or_critic":False,
        "raw_manuscripts_saved":False,
        "human_independent_review":False,
        "literary_90_pct_verified":False,
        "first_window":"NOT_PASSED","second_window":"LOCKED",
        "core_promoted":False,
    }
