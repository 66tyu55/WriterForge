"""Opt-in four-layer literary-evidence gate; legacy V28 APIs unchanged.

The host checks exact SOURCE anchors and field consistency before any Writer
call. Its own deterministic checks CANNOT establish semantic truth. Character
knowledge, transfer fit and risks remain *model hypotheses*, explicitly
unpromoted until an independent reader/reviewer verifies original + new task.

No raw quote, character, named plot or free-form planner text crosses from
this gate to the Writer. Return only existing HOST technique IDs and SHA.
"""
from __future__ import annotations
from hashlib import sha256
import json,re

from .reverse_mechanism_boundary import (
    TECHNIQUES,MAX_SELECTED,MAX_PARAGRAPHS,MAX_BOUND_INPUT_CHARS,
    MAX_PARAGRAPH_CHARS,MechanismBoundaryError,source_paragraphs,
)

REQUIRED={"id","evidence_id","source_span","character_knowledge",
          "local_cause_effect","new_task_fit","misuse_risk","decision"}
SCENARIOS={"SUPPORTED_FOR_TRIAL","INSUFFICIENT_EVIDENCE","RISK_IN_THIS_TASK"}
MAX_SPAN=48
MIN_SPAN=12

def semantic_proposal_prompt(paragraphs:tuple[dict,...], *, writing_task:str)->str:
    if not isinstance(writing_task,str) or not 40<=len(writing_task)<=800:
        raise MechanismBoundaryError("semantic task not bounded")
    if not isinstance(paragraphs,tuple) or not 1<=len(paragraphs)<=MAX_PARAGRAPHS:
        raise MechanismBoundaryError("semantic source paragraphs missing")
    defs="\n".join(f"{key}: {value}" for key,value in TECHNIQUES.items())
    return (
        "你是独立小说研究者，仅进行原著语义观察，不是正文写作者。"
        "必须区分作者写法和角色世界内事实。只从给定的宿主技巧ID选择0到2项，"
        "没有确切证据时返回 selections: []。"
        "每个选择必须恰含 id/evidence_id/source_span/character_knowledge/"
        "local_cause_effect/new_task_fit/misuse_risk/decision 八个字段。"
        "source_span 是 cited 段落中真实连续存在的12-48个字符，不得改写。"
        "character_knowledge 必须说明角色此时已知与未知的信息；"
        "local_cause_effect 解释局部观察如何影响选择及结果；"
        "new_task_fit 说明为何该机制适合当前全新题目，而不是照搬情节；"
        "misuse_risk 明示可能造成读者失焦、机械叙述或角色不合情理的风险。"
        "decision 仅可为 SUPPORTED_FOR_TRIAL、INSUFFICIENT_EVIDENCE 或 RISK_IN_THIS_TASK。"
        "若任何机制缺少源证据或者面临题材不适配，允许舍弃，不必选满两项。"
        "全部输出JSON，唯一顶层字段 selections，严禁发明新机制与原著后续事实。"
        "\n宿主现有技巧：\n"+defs+
        "\n独立原创写作任务（用于判断是否适配，禁止原著情节迁移）：\n"+writing_task+
        "\n已见来源段落（仅Planner可见）：\n"+
        json.dumps(paragraphs,ensure_ascii=False)
    )

def validate_semantic_selections(reply:dict, paragraphs:tuple[dict,...], *,
                                 writing_task:str)->tuple[tuple[dict,...],dict]:
    """Strictly validate source anchors without pretending semantic correctness."""
    if not isinstance(writing_task,str) or not 40<=len(writing_task)<=800:
        raise MechanismBoundaryError("semantic task invalid")
    if not isinstance(reply,dict) or set(reply)!={"selections"}:
        raise MechanismBoundaryError("SEMANTIC_PLANNER_SCHEMA_INVALID")
    values=reply["selections"]
    if not isinstance(values,list) or len(values)>MAX_SELECTED:
        raise MechanismBoundaryError("SEMANTIC_SELECTION_COUNT_INVALID")
    if not all(isinstance(p,dict) and set(p)=={"id","text"} for p in paragraphs):
        raise MechanismBoundaryError("semantic paragraphs malformed")
    known={p["id"]:p["text"] for p in paragraphs}
    selected=[]
    observed=[]
    used=set()
    for entry in values:
        if not isinstance(entry,dict) or set(entry)!=REQUIRED:
            raise MechanismBoundaryError("SEMANTIC_ENTRY_SCHEMA_INVALID")
        mechanism=entry["id"]
        para_id=entry["evidence_id"]
        span=entry["source_span"]
        if mechanism not in TECHNIQUES or mechanism in used:
            raise MechanismBoundaryError("SEMANTIC_MECHANISM_UNKNOWN_OR_REPEATED")
        if not isinstance(para_id,str) or para_id not in known:
            raise MechanismBoundaryError("SEMANTIC_EVIDENCE_PARAGRAPH_NOT_FOUND")
        if (not isinstance(span,str) or not MIN_SPAN<=len(span)<=MAX_SPAN
            or span not in known[para_id]):
            raise MechanismBoundaryError("SEMANTIC_EVIDENCE_NOT_IN_SOURCE")
        if entry["decision"] not in SCENARIOS:
            raise MechanismBoundaryError("SEMANTIC_DECISION_UNKNOWN")
        for key in ("character_knowledge","local_cause_effect","new_task_fit","misuse_risk"):
            note=entry[key]
            if not isinstance(note,str) or not 14<=len(note.strip())<=180:
                raise MechanismBoundaryError("SEMANTIC_UNSUPPORTED_OR_OVERSIZE_EXPLANATION")
            # These interpretations are NOT forwarded/persisted as learned rules.
        used.add(mechanism)
        accepted=entry["decision"]=="SUPPORTED_FOR_TRIAL"
        observed.append({
            "id":mechanism,"source_paragraph_id":para_id,
            "source_span_sha256":sha256(span.encode("utf-8")).hexdigest(),
            "explanation_sha256":{k:sha256(entry[k].encode("utf-8")).hexdigest()
                                  for k in ("character_knowledge","local_cause_effect",
                                            "new_task_fit","misuse_risk")},
            "model_decision":entry["decision"],
            "source_span_exact_match":True,
            "semantic_truth_independently_verified":False,
            "task_fit_independently_verified":False,
        })
        if accepted:
            selected.append({"id":mechanism,"evidence_ids":[para_id]})
    meta={
        "format":"writerforge.semantic-source-task-evidence-candidate.v1",
        "observed":observed,
        "source_anchor_check":"EXACT_CITED_PARAGRAPH_SPAN",
        "independent_semantic_review":"NOT_PERFORMED",
        "model_inference_not_literary_proof":True,
        "writer_received_model_explanations":False,
        "selected_count":len(selected),
        "candidate_only_no_promotion":True,
    }
    if len(json.dumps(meta,ensure_ascii=False))>4000:
        raise MechanismBoundaryError("SEMANTIC_EVIDENCE_METADATA_TOO_LARGE")
    return tuple(selected),meta
