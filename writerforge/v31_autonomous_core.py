"""Autonomous, bounded WriterForge *experimental* self-learning core.

No pretrained novel, outside critic, chat feedback, hard-coded replacement
literary rules or fake quality promotion. WF generates its own prompts, writes
its own drafts, diagnoses its own concrete weakness, then decides whether to
ADD, REPLACE_LAST, or REJECT a short transferable experimental rule.

This process gives genuine persistent self-proposed state changes, NOT a
proven improvement in literary ability. Only SHA-linked experimental snapshots
may feed the next creative turn. Stable official skill remains LOCKED.
"""
from __future__ import annotations
from hashlib import sha256
import json,re

SHA_RE=re.compile(r"[0-9a-f]{64}\Z")
MAX_CARDS=2
MAX_ROUNDS=3
DIMS=("perception","causality","information","continuity","language")
CARD_FIELDS={"scope","trigger","operation","avoid","self_check"}
REVIEW_FIELDS=CARD_FIELDS|{"evidence_anchor","observed_problem","decision"}
ACTIONS={"ADD","REPLACE_LAST","REJECT"}

class AutonomousLearningError(ValueError):
    pass

def digest(data:bytes|str)->str:
    return sha256(data.encode("utf-8") if isinstance(data,str) else data).hexdigest()

def canonical(data)->bytes:
    return json.dumps(data,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode("utf-8")

def _safe_note(value,lo,hi):
    return isinstance(value,str) and lo<=len(value.strip())<=hi

def _overlaps(source,rule,window=18):
    if len(rule)<window:return False
    return any(rule[i:i+window] in source
               for i in range(len(rule)-window+1))

def validate_card(value:dict,*,draft:str)->dict:
    if not isinstance(value,dict) or set(value)!=CARD_FIELDS:
        raise AutonomousLearningError("INVALID_SELF_LEARNED_CARD_SCHEMA")
    if not isinstance(draft,str) or not 350<=len(draft)<=4500:
        raise AutonomousLearningError("UNBOUNDED_SELF_DRAFT")
    for key in CARD_FIELDS:
        if not _safe_note(value[key],16,140):
            raise AutonomousLearningError("CARD_NOT_BOUNDED_OR_EMPTY")
        if _overlaps(draft,value[key]):
            raise AutonomousLearningError("CARD_COPIED_FROM_DRAFT_NOT_TRANSFERABLE")
    return {key:value[key].strip() for key in sorted(CARD_FIELDS)}

def evaluate_self_proposal(reply:dict, *, own_draft:str,
                           current_cards:tuple[dict,...])->tuple[tuple[dict,...],dict]:
    if not isinstance(reply,dict) or set(reply)!=REVIEW_FIELDS:
        raise AutonomousLearningError("SELF_REVIEW_SCHEMA_INVALID")
    if not _safe_note(reply["observed_problem"],16,180):
        raise AutonomousLearningError("SELF_REVIEW_PROBLEM_NOT_SPECIFIC")
    anchor=reply["evidence_anchor"]
    if not isinstance(anchor,str) or not 10<=len(anchor)<=60 or anchor not in own_draft:
        raise AutonomousLearningError("SELF_REVIEW_NOT_GROUNDED_IN_OWN_DRAFT")
    decision=reply["decision"]
    if decision not in ACTIONS:
        raise AutonomousLearningError("UNKNOWN_SELF_REVISION_DECISION")
    if not isinstance(current_cards,tuple) or len(current_cards)>MAX_CARDS:
        raise AutonomousLearningError("UNBOUNDED_PRIOR_LEARNING")
    before=[digest(canonical(card)) for card in current_cards]
    if decision=="REJECT":
        return current_cards,{
            "decision":"REJECT","changed":False,"previous_rule_hashes":before,
            "self_observed_problem_sha256":digest(reply["observed_problem"]),
            "own_draft_span_sha256":digest(anchor),
            "new_rule_hashes":before,"literary_quality_verified":False,
        }
    card=validate_card({k:reply[k] for k in CARD_FIELDS},draft=own_draft)
    c=list(current_cards)
    new_digest=digest(canonical(card))
    if new_digest in before:
        decision="REJECT_DUPLICATE"
        result=current_cards
    elif decision=="REPLACE_LAST":
        if not c:
            result=(card,)
            decision="ADD_TO_EMPTY"
        else:
            c[-1]=card
            result=tuple(c)
    else:
        # A third different rule does not cause unbounded growth; the learner
        # must explicitly replace or reject instead of implicit eviction.
        if len(c)>=MAX_CARDS:
            raise AutonomousLearningError("RULE_MEMORY_FULL_REQUIRES_REPLACE_OR_REJECT")
        result=tuple(c+[card])
    after=[digest(canonical(r)) for r in result]
    return result,{
        "decision":decision,"changed":after!=before,"previous_rule_hashes":before,
        "new_rule_hashes":after,
        "self_observed_problem_sha256":digest(reply["observed_problem"]),
        "own_draft_span_sha256":digest(anchor),
        "literary_quality_verified":False,
    }

def task_prompt(round_index:int,prior_task_hashes:list[str])->str:
    if type(round_index) is not int or not 1<=round_index<=MAX_ROUNDS+1:
        raise AutonomousLearningError("INVALID_AUTONOMOUS_ROUND")
    return (
        "你是WriterForge内部情节试题设计器。独立设计一篇完整原创"
        "中国幻想/武侠/人情故事第一章的题目。你自己决定环境、人物、"
        "错误选择、实际后果、悬念和关系张力，不接受外部情节建议。"
        "不得照搬任何现有小说、用户示例或旧任务。请尽量避免重复前面"
        "已设计题目的故事设定。仅返回JSON对象，严格且仅含 task 字段；"
        "task为100到460个汉字左右的清晰完整独立题目，包含人物此刻"
        "能知道与不知道的边界，允许小说自由发挥；不要直接编写正文。"
        "本次训练序号："+str(round_index)+
        "。先前试题指纹（只作唯一性检查，不含试题内容）："+
        json.dumps(prior_task_hashes)
    )

def validate_task(answer,previous:list[str])->str:
    if not isinstance(answer,dict) or set(answer)!={"task"}:
        raise AutonomousLearningError("SELF_TASK_JSON_SCHEMA_INVALID")
    task=answer["task"]
    if not _safe_note(task,95,490):
        raise AutonomousLearningError("SELF_TASK_LENGTH_INVALID")
    if digest(task) in previous:
        raise AutonomousLearningError("SELF_REPEATED_PRIOR_TASK")
    return task.strip()

def writer_instruction(task:str,cards:tuple[dict,...])->str:
    if not _safe_note(task,95,490):
        raise AutonomousLearningError("UNVERIFIED_SELF_GENERATED_TASK")
    if len(cards)>MAX_CARDS:
        raise AutonomousLearningError("RULE_MEMORY_BUDGET_EXCEEDED")
    for card in cards:
        if not isinstance(card,dict) or set(card)!=CARD_FIELDS or any(
            not _safe_note(card[k],16,140) for k in CARD_FIELDS):
            raise AutonomousLearningError("UNTRUSTED_RULE_MEMORY_FORMAT")
    return json.dumps({
        "self_generated_task":task,
        "internal_experimental_rules":[dict(x) for x in cards],
        "rules_not_facts_or_source_prose":True,
        "only_write_complete_original_first_chapter":True,
        "requested_characters_including_punctuation":[850,1400],
        "no_title_no_markdown_no_prose_about_the_rules":True,
    },ensure_ascii=False,separators=(",",":"))

def self_review_prompt(task:str,draft:str,cards:tuple[dict,...])->str:
    if not isinstance(draft,str) or not 350<=len(draft)<=4500:
        raise AutonomousLearningError("SELF_DRAFT_LENGTH_INVALID")
    if len(cards)>MAX_CARDS:raise AutonomousLearningError("UNBOUNDED_RULE_SNAPSHOT")
    return (
        "你是WriterForge自己，不是外部评分机构。严格揭示这篇你自己"
        "写的原创小说首章中最可修复的具体缺点：人物认知越界、"
        "行为因果断裂、场景过渡、伏笔不能回查、语言失焦等。"
        "不得用平均分掩盖任何缺点，也不得自我吹捧。"
        "从自己的正文中给出连续10-60字的证据 evidence_anchor。"
        "你决定是否更新实验技能：ADD、REPLACE_LAST或REJECT。"
        "仅返回JSON，字段严格为 decision、observed_problem、"
        "evidence_anchor、scope、trigger、operation、avoid、self_check。"
        "后五个字段为可迁移的抽象操作，不能粘贴剧情、角色名、"
        "台词和原文句子，尽量避免与已存规则重复。"
        "每个字段16-140字（问题最多180）；证据必须在正文中精确出现。"
        "最多两条记忆；若已满请选REPLACE_LAST或REJECT。"
        "\n本轮任务："+task+
        "\n现有内部实验规则："+json.dumps(cards,ensure_ascii=False)+
        "\n仅本轮自写正文（使用后销毁）："+draft
    )

def self_blind_prompt(task:str,anon:dict)->str:
    if not isinstance(anon,dict) or set(anon)!={"A","B"}:
        raise AutonomousLearningError("BLIND_SELF_CHECK_ARMS_MISSING")
    return (
        "你是WF内部自测模块，非独立文学评审。对同一原创新题下的"
        "两篇匿名稿逐项指出五维具体缺点；不得知道哪份使用实验记忆，"
        "也不要推断标签。相同题必须用同一标准，任何负面维度不得用"
        "平均分抵消。输出严格JSON：顶层只有A、B两个对象，"
        "每个对象严格包含 perception/causality/information/"
        "continuity/language 五个0-100整数，不得有理由文字。"
        "内部自评分数仅用于自检，不能证明文学能力已提升。"
        "\n新试题："+task+"\n匿名作品："+json.dumps(anon,ensure_ascii=False)
    )

def validate_self_comparison(answer:dict,anon:dict,order:list[str])->dict:
    if not isinstance(answer,dict) or set(answer)!={"A","B"} or len(order)!=2:
        raise AutonomousLearningError("SELF_CHECK_INCOMPLETE")
    for label in ("A","B"):
        if (not isinstance(answer[label],dict) or
            set(answer[label])!=set(DIMS) or any(
                type(answer[label][k]) is not int or not 0<=answer[label][k]<=100
                for k in DIMS)):
            raise AutonomousLearningError("SELF_CHECK_SCORE_INVALID")
    scores={arm:answer["A" if order[0]==arm else "B"] for arm in order}
    differences={k:scores["with_memory"][k]-scores["without_memory"][k] for k in DIMS}
    return {
        "format":"writerforge.v31-internal-blind-self-evaluation.v1",
        "dimensions_with_memory_minus_without":differences,
        "negative_dimensions_uncancelled":{k:v for k,v in differences.items() if v<0},
        "self_critic_not_independent":True,
        "source_text_in_result":False,
        "literary_quality_improvement_proven":False,
    }
