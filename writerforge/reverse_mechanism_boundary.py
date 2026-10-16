"""Strict HOST-owned boundary between copyrighted source analysis and writing.

Only fixed, reusable literary *operations* can reach Writer. No planner
names, events, prose, source excerpts or retrieval identifiers are forwarded.
Model's claimed evidence is verified by source-paragraph IDs, NOT treated as
proof that a literary mechanism is correct (that needs independent review).
"""
from __future__ import annotations

from hashlib import sha256
import json
import re


class MechanismBoundaryError(ValueError):
    pass


# Fixed program-owned writing operations, never synthesized from the source.
TECHNIQUES = {
    "GOAL_FILTERS_ATTENTION": (
        "在新故事中先固定人物此刻的目标及认知限制，只让其察觉"
        "与目标、风险和经验有关的少量具体刺激；避免罗列所有环境物。"
    ),
    "COST_VISIBLE_IN_ACTION": (
        "让人物在两种可行行动之间做有代价的选择，先用行动和可见后果"
        "表现代价，不要先用解释性独白宣布人物的品质。"
    ),
    "WITHHOLD_CAUSE_SHOW_CLUE": (
        "先提供至少一个可供读者回查的异常线索，再短暂推迟其原因。"
        "未解事实应能影响人物当下的决策，而不只是增加神秘名词。"
    ),
    "EMOTIONAL_TURN_WITH_EVIDENCE": (
        "情绪变化前安排实际刺激、误解被修正或行动后果，并让身体"
        "动作、对话选择自然反映变化；避免直接宣告心理转折。"
    ),
}
# No model-controlled descriptions, references, names or plot in write packet.
MAX_SELECTED = 2
MAX_PARAGRAPHS = 36
MAX_PARAGRAPH_CHARS = 650
MAX_BOUND_INPUT_CHARS = 5500
MAX_PLAN_JSON_CHARS = 5500


def source_paragraphs(first: str) -> tuple[dict, ...]:
    if not isinstance(first,str) or not 300 <= len(first) <= MAX_BOUND_INPUT_CHARS:
        raise MechanismBoundaryError("invalid bounded source window")
    paragraphs=[]
    for section in first.splitlines():
        section=section.strip()
        if not section:
            continue
        if len(section)>MAX_PARAGRAPH_CHARS:
            raise MechanismBoundaryError("oversized source paragraph: requires source-side segmentation")
        if len(paragraphs)>=MAX_PARAGRAPHS:
            raise MechanismBoundaryError("source paragraph count exceeds bound")
        paragraphs.append({
            "id":"P"+str(len(paragraphs)),
            "text":section,
        })
    if not paragraphs:
        raise MechanismBoundaryError("no source paragraphs")
    return tuple(paragraphs)


def proposal_prompt(paragraphs: tuple[dict,...]) -> str:
    ids="
".join("- "+id+": "+description for id,description in TECHNIQUES.items())
    return (
        "你只能从宿主提供的机制 ID 里选择最多两项最有依据的叙事操作。"
        "对每个选择给出至少一个已经出现的段落 ID，不能猜后文。"
        "只返回 JSON 对象，唯一顶层字段 selections；"
        "selections 是 1~2 项数组，每项严格包含 id（宿主机制 ID）"
        "和 evidence_ids（1~3 个 P 编号）的字段。不要复述原文情节。"
        "
宿主操作定义：
"+ids+"
仅供分析器阅读的原文段落：
"
        +json.dumps(paragraphs,ensure_ascii=False)
    )


def parse_selections(reply: dict,paragraphs:tuple[dict,...]) -> tuple[dict,...]:
    if not isinstance(reply,dict) or set(reply)!={"selections"}:
        raise MechanismBoundaryError("planner returned unrecognized analysis or plot fields")
    raw=reply["selections"]
    if not isinstance(raw,list) or not 1<=len(raw)<=MAX_SELECTED:
        raise MechanismBoundaryError("planner selection count must be 1..2")
    known={p["id"] for p in paragraphs}
    unique=set()
    selected=[]
    for item in raw:
        if not isinstance(item,dict) or set(item)!={"id","evidence_ids"}:
            raise MechanismBoundaryError("planner entry has untrusted fields")
        key=item["id"]
        evidence=item["evidence_ids"]
        if not isinstance(key,str) or key not in TECHNIQUES or key in unique:
            raise MechanismBoundaryError("invalid or duplicate technique ID")
        if not isinstance(evidence,list) or not 1<=len(evidence)<=3:
            raise MechanismBoundaryError("invalid evidence count")
        if any(not isinstance(pid,str) or pid not in known for pid in evidence):
            raise MechanismBoundaryError("planner cited missing source paragraph")
        if len(evidence)!=len(set(evidence)):
            raise MechanismBoundaryError("duplicate evidence paragraph")
        unique.add(key)
        selected.append({"id":key,"evidence_ids":list(evidence)})
    return tuple(selected)


def build_writer_packet(selections:tuple[dict,...],*,enhanced:bool,writing_task:str)->dict:
    """Never include planner reply, novel text, source names, or evidence IDs."""
    if not isinstance(writing_task,str) or not 1<=len(writing_task)<=800:
        raise MechanismBoundaryError("unbounded creative task")
    packet={"writing_task":writing_task,"return_json":{"scene":"string"}}
    if enhanced:
        if not selections or len(selections)>MAX_SELECTED:
            raise MechanismBoundaryError("unverified technique selection")
        if any(x.get("id") not in TECHNIQUES for x in selections):
            raise MechanismBoundaryError("unknown technique")
        packet["technique_operations"]=[
            {"id":entry["id"],"operation":TECHNIQUES[entry["id"]]}
            for entry in selections
        ]
    return packet


def report_evidence(selections:tuple[dict,...],paragraphs:tuple[dict,...])->list[dict]:
    """Hashes only; no prose copied from original into R2."""
    known={p["id"]:p["text"] for p in paragraphs}
    return [{
        "technique_id":entry["id"],
        "source_paragraphs":[{
            "id":pid,"source_text_sha256":sha256(known[pid].encode("utf-8")).hexdigest()
        } for pid in entry["evidence_ids"]],
        "semantic_support_unreviewed":True,
    } for entry in selections]
