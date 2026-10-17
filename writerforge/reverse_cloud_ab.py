"""V28 cloud A/B: same original window, two different original drafts.

Both drafts are ephemeral; only source and draft SHA, bounded interpretations,
comparative model observations and budgets may persist. 90% is NOT verified.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from .reverse_real_training import RealTrainingError, raw_hash, _source_copy_guard
from .reverse_mechanism_boundary import (
    MechanismBoundaryError, source_paragraphs, proposal_prompt,
    parse_selections, build_writer_packet, report_evidence,
    guarded_proposal_prompt, guarded_selections,
)

MAX_AB_CALLS = 4
DIMENSIONS = ("perception","causality","information","continuity","language")
MAX_AB_DRAFT = 4500
BASE_TASK = (
    "创作全新的中国幻想故事开篇场景，主人公在压力中发现异样、"
    "作出有代价的选择，并留下真实的未解问题。使用原创人名与世界设定，"
    "不要续写、翻译、改写任何现成小说。要求视角清楚、场景因果连续、"
    "事件对主人公产生后果。长度700到1400汉字。"
)


class ABTrialError(RealTrainingError):
    pass


def _brief(value, key):
    if not isinstance(value,str) or not 4<=len(value.strip())<=180:
        raise ABTrialError("missing or unbounded literary evaluation: "+key)
    return value.strip()


def _has_long_exact_overlap(note: str, *references: str) -> bool:
    """Prevent saving >=18 consecutive characters of original or draft prose.

    A privacy filter; this does not claim to detect semantic copying.
    """
    width = 18
    return len(note) >= width and any(
        note[i:i + width] in reference
        for i in range(len(note) - width + 1)
        for reference in references
    )


def _choice_score(doc, draft, source):
    if not isinstance(doc,dict) or set(doc)!=set(DIMENSIONS):
        raise ABTrialError("comparison dimensions incomplete")
    result={}
    for name in DIMENSIONS:
        item=doc[name]
        if not isinstance(item,dict) or set(item)!={"score","reason"}:
            raise ABTrialError("invalid comparison dimension")
        n=item["score"]
        if type(n) is not int or not 0<=n<=100:
            raise ABTrialError("unbounded comparison score")
        reason=_brief(item["reason"], name)
        if _has_long_exact_overlap(reason, source, draft):
            reason="UNVERIFIED_QUOTATION_REDACTED_"+raw_hash(reason)[:18]
        result[name]={"score":n,"reason":reason}
    return result


class CloudABTrial:
    """Source-isolated AB. Planner chooses HOST-defined reusable mechanisms.

    Writer sees no source prose or plot; critic sees both anonymized drafts.
    Length mismatches fail closed; model score cannot promote literary skill.
    """
    def __init__(self, *, planner, writer, critic, evidence_first:bool=False,
                 quarantined_pairs:tuple=(), transfer_policy:dict|None=None):
        if (writer.provider,writer.name)==(critic.provider,critic.name):
            raise ABTrialError("writer cannot critique same identity")
        self.planner,self.writer,self.critic=planner,writer,critic
        self.evidence_first=bool(evidence_first)
        self.quarantined_pairs=quarantined_pairs
        if transfer_policy is not None and not evidence_first:
            raise ABTrialError("UNSAFE_POLICY_WITH_LEGACY_UNGUARDED_MODE")
        self.transfer_policy=transfer_policy

    def run(self, first:str, second:str, *, source_sha:str, window_hash:str,
            writing_task:str=BASE_TASK, role_tokens:tuple[int,int,int]=(6500,11000,8000)):
        if not 300<=len(first)<=5500 or not second:
            raise ABTrialError("source is not a real bounded first chapter window")
        if not isinstance(writing_task,str) or not 40<=len(writing_task)<=800:
            raise ABTrialError("invalid new original writing task")
        if (not isinstance(role_tokens,tuple) or len(role_tokens)!=3
            or any(type(n) is not int for n in role_tokens)
            or not (2500<=role_tokens[0]<=6500
                    and 6000<=role_tokens[1]<=11000
                    and 4000<=role_tokens[2]<=8000)):
            raise ABTrialError("invalid bounded role token reservation")
        if role_tokens!=(6500,11000,8000) and (
            role_tokens[0]+4*role_tokens[1]+role_tokens[2]>50000):
            # Two writer transport/visible retry attempts must still leave
            # enough reservation for the other Writer and Critic stages.
            raise ABTrialError("RETRY_RESILIENT_STAGE_BUDGET_INSUFFICIENT")
        if raw_hash(first)!=window_hash:
            raise ABTrialError("first window no longer matches R2 pin")
        # Source/plot only enters the planner; Writer and critic receive
        # only program-owned enum operations and the same neutral task.
        paragraphs=source_paragraphs(first)
        proposal=self.planner.ask(
            "你负责原著证据选择，不负责替写作者写剧情提纲。"
            "不能输出原著专名、事件描述或任意创作指令。"
            "严格按宿主的 id/evidence_ids JSON 结构回复。",
            guarded_proposal_prompt(paragraphs) if self.evidence_first
            else proposal_prompt(paragraphs),num_predict=role_tokens[0])
        if self.evidence_first:
            selections,decision=guarded_selections(
                proposal,paragraphs,source_window_sha256=window_hash,
                quarantined_pairs=self.quarantined_pairs)
            if not selections:
                # Preserve token budget, neutral baseline and existing craft
                # registry: do not force a new technique into a wrong context.
                raise ABTrialError("NO_VERIFIED_TRANSFERABLE_MECHANISM")
        else:
            selections=parse_selections(proposal,paragraphs)
            decision="LEGACY_EXPERIMENT_UNVERIFIED"
        if self.evidence_first and self.transfer_policy is not None:
            from .reverse_transfer_policy import should_withhold_opt_in
            pair=[item["id"] for item in selections]
            if should_withhold_opt_in(pair,self.transfer_policy):
                raise ABTrialError("MULTI_WINDOW_NEGATIVE_MECHANISM_PAIR_QUARANTINED")
        abstract_evidence=report_evidence(selections,paragraphs)
        neutral=build_writer_packet(selections,enhanced=False,writing_task=writing_task)
        enhanced=build_writer_packet(selections,enhanced=True,writing_task=writing_task)
        outputs={}
        for kind, instruction in (("baseline",neutral),("skill",enhanced)):
            response=self.writer.ask(
                "你是原创小说作家。只输出小说正文；不要包装为JSON、"
                "不要代码块、标题或解释性说明。"
                "不得使用参考作品人物、世界观、对话和情节。",
                json.dumps(instruction,ensure_ascii=False),
                num_predict=role_tokens[1])
            draft=response.get("scene")
            if not isinstance(draft,str) or not 220<=len(draft)<=MAX_AB_DRAFT:
                raise ABTrialError("writer failed to produce bounded original scene")
            _source_copy_guard(draft,first)
            outputs[kind]=draft
        # A/B must be comparable BEFORE any numerical critic score exists.
        # Earlier actual A/B had a 49% length difference, a severe confound.
        baseline_chars=len(outputs["baseline"])
        skill_chars=len(outputs["skill"])
        if (abs(baseline_chars-skill_chars)/max(baseline_chars,skill_chars))>0.15:
            raise ABTrialError("AB_LENGTH_MISMATCH_NOT_COMPARABLE")
        # Blind ordering is fixed by *draft hashes* before seeing evaluation,
        # so the critic never receives which prompt included the learned rule.
        # The critic must not see the source novel. Quality is assessed
        # only against the original creative assignment and anonymized drafts.
        ordered=sorted(outputs, key=lambda k:raw_hash(outputs[k]))
        masked={"A":outputs[ordered[0]],"B":outputs[ordered[1]]}
        comparison=self.critic.ask(
            "你是独立的文学批评模型。对以下两篇匿名原创稿按相同任务盲评，"
            "侧重主人公感知合理性、行为因果、信息释放、前后连续性及语言质量。"
            "返回完整有效的 JSON 对象：键 A 和 B 都必须含 perception、"
            "causality、information、continuity、language 五个对象；每个对象"
            "严格包含 score（0-100整数）和 reason（简短文本）两个字段。"
            "此外顶层必须含 uncertainty 和 learned_mechanism 两个字符串。"
            "不得省略字段、不得写省略号或使用Markdown。"
            "评论必须能指出真实文本差异，不能默认有技巧约束的稿子一定更好。"
            "不得引用大段原著或练习稿；分数只是模型未经校准的观察，"
            "不能视为专家90分证明。",
            json.dumps({"task":writing_task,
                        "A":masked["A"],"B":masked["B"]},ensure_ascii=False),
            num_predict=role_tokens[2])
        if not isinstance(comparison,dict) or set(comparison)!={
            "A","B","uncertainty","learned_mechanism"
        }:
            raise ABTrialError("critic returned incomplete blinded AB comparison")
        review={
            "A":_choice_score(comparison["A"],masked["A"],first),
            "B":_choice_score(comparison["B"],masked["B"],first),
        }
        neutral_note={}
        for key in ("uncertainty","learned_mechanism"):
            value=_brief(comparison[key],key)
            if _has_long_exact_overlap(value, first, *outputs.values()):
                value="UNVERIFIED_QUOTATION_REDACTED_"+raw_hash(value)[:18]
            neutral_note[key]=value
        def mean(name):
            return sum(review[name][k]["score"] for k in DIMENSIONS)//len(DIMENSIONS)
        labels={v:k for k,v in enumerate(ordered)}
        display={label:{
            "source_prompt":"skill" if label=="skill" else "baseline",
            "draft_sha256":raw_hash(outputs[label]),
            "draft_chars":len(outputs[label]),
            "anonymized_critic_label":"A" if ordered[0]==label else "B",
            "model_critic_score_unverified":mean("A" if ordered[0]==label else "B"),
            "dimension_review":review["A" if ordered[0]==label else "B"],
        } for label in ("baseline","skill")}
        return {
            "format":"writerforge.cloud-ab-v1",
            "source_work":"wudongqiankun","edition_sha256":source_sha,
            "source_unit_sha256":window_hash,"next_unit_sha256":raw_hash(second),
            "writing_task_sha256":raw_hash(writing_task),
            "stage":"true_model_calls_and_private_source_AB_comparison_unverified",
            "roles":{"planner":{"provider":self.planner.provider,"model":self.planner.name},
                     "writer":{"provider":self.writer.provider,"model":self.writer.name},
                     "critic":{"provider":self.critic.provider,"model":self.critic.name}},
            "planner_mechanisms_unreviewed":abstract_evidence,
            "writer_prompt_source_prose_or_plot":False,
            "critic_prompt_original_source_prose":False,
            "mechanism_registry":"host_static_only_v1",
            "planner_evidence_policy":decision,
            "role_output_token_profile":list(role_tokens),
            "length_gate":{"max_relative_difference":0.15,
                           "baseline_chars":baseline_chars,
                           "skill_chars":skill_chars,
                           "comparable":True},
            "comparisons":display,
            **neutral_note,
            "model_call_count_nominal":4,
            "drafts_retained":False,"human_blind_review_performed":False,
            "literal_master_quality_90pct_verified":False,
            "second_unit_unlocked":False,"core_automatically_promoted":False,
        }
