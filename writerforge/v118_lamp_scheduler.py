"""V118 opt-in just-in-time literature lamps (zero model, existing WF engine).

The scene chooses creative prose; this module chooses IF a reminder is useful.
Hard preconditions remain in V114/Novel Studio/V117 and cannot be switched
off by a craft lane. Only one craft question, at most two source-backed risk
signals and a small bounded prompt. No automatic skill graduation, corpus
copying, canon writes, new model calls or parallel memory store.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

from .craft_engine import CraftEngine, CraftRequest

FORMAT="wf.writing.v118.event-guidance-lamp"
MAX_CHARS=460
MAX_RISKS=2
VALID_BEAT_KINDS=frozenset((
    "action","decision","reversal","setup","dialogue","quiet",
    "aftermath","transition",
))
VALID_FOCUS=frozenset((
    "dialogue","detail","interiority","pacing","restraint",
    "contrast","action","none",
))
SIGNALS={
    "dialogue":"dialogue",
    "detail":"description",
    "interiority":"interiority",
    "pacing":"pacing",
    "restraint":"over_explain",
    "contrast":"relationship_pressure",
    "action":"scene",
}
QUESTIONS={
    "dialogue_as_action":"这句对话试图改变什么？对方的反应是否真的改变了局势？",
    "public_private_goal_gap":"人物公开要求的，与心里真正想得到的，有何差距？",
    "telling_detail":"眼前哪个具体细节真的改变了角色判断，而不是填充画面？",
    "perception_motivation":"人物此刻在寻找、回避或误读什么？",
    "reaction_dilemma_decision":"这次感受或思考是否改变了人物下一步的选择？",
    "self_awareness_ceiling":"人物现在真的有能力看穿自己全部动机吗？",
    "trust_the_reader":"动作和后果已经表达清楚的地方，能否停在画面而非解释？",
    "delay_explanation":"这个秘密现在揭晓会推动选择，还是只会失去悬念？",
    "scene_delta":"这一场结束以后，事实、目标、关系、风险或读者问题变了什么？",
    "leave_after_turn":"这个场景已经完成作用了吗，是否需要及时离开？",
    "rhythm_by_function":"句子长短是否跟随此刻压力、犹豫和动作改变？",
    "narrative_magnification":"这件事值得正面展示，还是省略或压缩更有力？",
    "strategic_reversal":"逆转有没有此前可检验的资源与代价？",
    "punctuation_as_performance":"停顿与节拍是否服务当前动作，而不是花样？",
    "temporal_reordering":"时间重排后读者还能辨认发生顺序吗？",
    "detail_utility":"这个细节有何感官和叙事作用？",
    "free_indirect_voice":"叙述是否保持人物自己的感受和用词？",
    "motif_return":"重复意象是否产生了新的意义而非重复形容？",
}
CANONICAL_PHRASES={
    "arm":"如果此段要让受限的肢体重新承担动作，先提供可见的恢复依据；不要求写成说明书。",
    "resource":"如果此段要消耗或补充资源，交代来源与实际动作；提到物件不代表已经使用。",
    "transfer":"若此段要转动物件，先出现交接动作；上段的未证转移不能自动算作发生。",
    "knowledge":"此段人物可以猜测或误信，但不要把尚未获知的秘密写成其确定知识。",
}
NAME=re.compile(r"^[\u3400-\u9fffA-Za-z0-9_-]{1,20}$")
SHA=re.compile(r"^[0-9a-f]{64}$")

class LampDecisionError(ValueError):
    pass

def need(ok,code):
    if not ok:raise LampDecisionError(code)

def encode(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf8")

def digest(x):return sha256(encode(x)).hexdigest()

def checked_previous(old,project,chapter):
    if old is None:return None
    need(type(old) is dict and
         old.get("format")==FORMAT and
         old.get("project_id")==project and
         old.get("chapter_index")==chapter and
         type(old.get("receipt_sha256")) is str and
         SHA.fullmatch(old["receipt_sha256"]) and
         old["receipt_sha256"]==digest({
           k:v for k,v in old.items() if k!="receipt_sha256"
         }) and
         type(old.get("turn_index")) is int and
         type(old.get("craft_id")) in (str,type(None)),
         "WF118_LAMP_OLD_STATE_INVALID_OR_CROSS_PROJECT")
    return old

def frame_state(frame,*,project_id,chapter_index):
    if frame is None:return ([],[],{})
    need(type(frame) is dict and
         frame.get("format")=="wf.continuity.v117.pinned-oss-temporal-view" and
         frame.get("project_id")==project_id and
         frame.get("chapter_index")==chapter_index and
         frame.get("state_has_no_auto_canon_promotion") is True and
         frame.get("no_model_call") is True and
         frame.get("literary_truth_verified") is False,
         "WF118_UNTRUSTED_CONTINUITY_FRAME")
    state=frame.get("unreviewed_reducer_candidates")
    debt=frame.get("unresolved_open_debts",[])
    knowledge=frame.get("knowledge",{})
    need(type(state) is list and len(state)<=64 and
         type(debt) is list and len(debt)<=96 and
         type(knowledge) is dict,
         "WF118_SOURCE_FRAME_BOUNDS")
    return state,debt,knowledge

def plan_scene_lamps(*,project_id,chapter_index,turn_index,beat,
                     frame=None,previous=None):
    need(type(project_id) is str and 0<len(project_id)<=128 and
         type(chapter_index) is int and 0<=chapter_index<=1000000 and
         type(turn_index) is int and 0<=turn_index<=20 and
         type(beat) is dict and
         beat.get("kind") in VALID_BEAT_KINDS and
         type(beat.get("actor")) is str and len(beat["actor"])<=70 and
         type(beat.get("goal")) is str and 1<=len(beat["goal"])<=220 and
         type(beat.get("craft_focus")) is list and
         len(beat["craft_focus"])<=2 and
         all(x in VALID_FOCUS for x in beat["craft_focus"]),
         "WF118_LAMP_BAD_SCENE_CONTRACT")
    prior=checked_previous(previous,project_id,chapter_index)
    need(prior is None or turn_index==prior["turn_index"]+1,
         "WF118_LAMP_TURN_ORDER_OR_REPLAY")
    state,debt,knowledge=frame_state(frame,project_id=project_id,
                                    chapter_index=chapter_index)
    actor=beat["actor"]
    goal=beat["goal"]
    active=[]
    reasons=[]
    kind=beat["kind"]
    if kind in ("action","decision","reversal"):
        related_debt=next((r for r in reversed(debt)
                           if type(r) is dict and
                           r.get("kind") in ("UNPROVEN_ITEM_TRANSFER",
                               "ITEM_OWNER_CHANGE_WITHOUT_TRANSFER") and
                           type(r.get("item_key")) is str and
                           NAME.fullmatch(r["item_key"]) and
                           r["item_key"] in goal),None)
        if related_debt:
            active.append("transfer")
            reasons.append("PREVIOUS_UNRESOLVED_ITEM_SOURCE")
        for row in state:
            if type(row) is not dict:continue
            who=row.get("entity_id")
            pred=row.get("predicate")
            value=row.get("value")
            if (who==actor and pred in ("右臂可用性","右臂伤情")
                and value is not None and
                any(x in str(value) for x in ("受限","灼","伤","疼","无法","不能"))):
                if "arm" not in active:
                    active.append("arm")
                    reasons.append("SOURCE_ANCHORED_INJURY_REQUIRES_ACTION_COST")
            if (type(who) is str and "resource" not in active and
                row.get("domain")=="item" and
                (who in goal or any(x in goal for x in
                    ("灵力","法力","补充","回涨","吞","服","吃")))):
                active.append("resource")
                reasons.append("KNOWN_ITEM_NEEDS_EXPLICIT_RESOURCE_CHANGE")
        if (type(knowledge.get("unknown")) is list and knowledge["unknown"] and
            "knowledge" not in active):
            active.append("knowledge")
            reasons.append("POV_KNOWLEDGE_BOUNDARY_VISIBLE")
    active=active[:MAX_RISKS]
    reason_codes=reasons[:len(active)]

    # Existing CraftEngine, not a second catalogue of style recipes.
    keys=[SIGNALS[x] for x in beat["craft_focus"] if x in SIGNALS]
    if beat["craft_focus"]==["none"]:keys=[]
    if not keys and kind=="decision":keys=["interiority"]
    craft=CraftEngine().plan(CraftRequest(needs=tuple(keys),max_groups=1))
    chosen=craft.techniques[0].id if craft.techniques else None
    skip=None
    if chosen and prior and prior.get("craft_id")==chosen and (
         prior.get("source_checkpoint_sha256")==
         (frame.get("source_checkpoint_sha256") if frame else None)):
        skip="REPEATED_CRAFT_AND_UNCHANGED_EVIDENCE"
        chosen=None
    lines=[]
    if active:
        lines.append("【只在确实涉及该变化时遵守的前文约束】")
        lines.extend(CANONICAL_PHRASES[k] for k in active)
    if chosen:
        lines.append("【本段至多一个文学思考提示（不要求解释思考过程）】"+
                     QUESTIONS.get(chosen,"只让人物行为自然推动场景变化。"))
    # A quiet scene with no relevant signal must be allowed to stay quiet.
    prompt="\n".join(lines)
    need(len(prompt)<=MAX_CHARS,"WF118_LAMP_PROMPT_BUDGET")
    receipt={
        "format":FORMAT,
        "project_id":project_id,
        "chapter_index":chapter_index,
        "turn_index":turn_index,
        "beat_kind":kind,
        "source_checkpoint_sha256":frame.get("source_checkpoint_sha256")
            if frame else None,
        "risk_lamps":active,
        "risk_reason_codes":reason_codes,
        "craft_id":chosen,
        "craft_suppression":skip,
        "prompt":prompt,
        "prompt_chars":len(prompt),
        "zero_lamp_is_valid":not active and not chosen,
        "hard_reducer_preconditions_always_separate":True,
        "factjournal_canon_writes":0,
        "new_model_calls":0,
        "literary_quality_improvement_proven":False,
        "no_rewrite_of_original_prose":True,
        "source_text_copied_into_prompt":False,
    }
    receipt["receipt_sha256"]=digest(receipt)
    return receipt
