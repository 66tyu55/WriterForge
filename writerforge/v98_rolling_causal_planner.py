"""V98 opt-in PROSE-DRIVEN rolling narrative plan (unaccepted drafts only).

WF's V97 C mode checked that action/effect quotations *exist*. This gate
makes the next writing objective contingent on an ACTUALLY emitted previous
effect, rather than blindly following the whole initial chapter beat list.

The model remains responsible for character motivation and literary craft.
The host only authenticates exact short citations, turn ID/order, chosen
actor within predeclared cast, parent effect and bounded proposal. It CANNOT
infer deep causality, whether a cost is real, or whether an intention is true.
No FactJournal, R2, training, canonical story, or reviewer writes occur here.
A soft "uncertain" candidate is not a confirmed world-state change.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .v96_causal_turns import (
    CAUSAL_KINDS,BEAT_FIELDS,_occurrences,parse_turn_outline,
    canonical,digest,V96CausalDraftError,
)

MAX_ROLLING_REPLANS_PER_JOB=14
MAX_ROLLING_JSON_BYTES=5500
MAX_ROLLING_CONTEXT_CHARS=3100
MAX_SHORT_QUOTE_CHARS=96
MAX_GOAL_CHARS=220
PROPOSAL_FIELDS=frozenset((
    "next_turn","basis_effect_quote","pressure_quote","cost_quote",
    "unresolved_question","reason_for_shift",
))


class V98RollingPlanError(ValueError):
    pass


def require(condition,code):
    if not condition:
        raise V98RollingPlanError(code)


def _bounded(value,minlen=1,maxlen=220):
    return (type(value) is str and
            minlen<=len(value.strip())<=maxlen and
            "\ufffd" not in value and "\x00" not in value and
            not any(ord(c)<32 for c in value))


def _decode(raw):
    require(type(raw) is str,"WF98_ROLLING_JSON_NOT_STRING")
    try:
        length=len(raw.encode("utf8","strict"))
    except UnicodeError:
        raise V98RollingPlanError("WF98_ROLLING_JSON_BAD_UNICODE") from None
    require(2<=length<=MAX_ROLLING_JSON_BYTES,
            "WF98_ROLLING_RESPONSE_SIZE")
    try:
        def unique(kv):
            obj={}
            for k,v in kv:
                if k in obj:
                    raise ValueError("duplicate JSON field")
                obj[k]=v
            return obj
        doc=json.loads(raw,object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(
                           ValueError("nonfinite")))
        canonical(doc)
    except (ValueError,TypeError,UnicodeError,OverflowError):
        raise V98RollingPlanError("WF98_ROLLING_JSON_INVALID") from None
    require(type(doc) is dict and set(doc)==PROPOSAL_FIELDS,
            "WF98_ROLLING_RESPONSE_SCHEMA")
    return doc


def _anchor(source,text,reason):
    """Only literal unique locations; this is NOT a semantic assessment."""
    require(_bounded(text,6,MAX_SHORT_QUOTE_CHARS),
            "WF98_"+reason+"_QUOTE_BOUND")
    loc=_occurrences(source,text)
    require(len(loc)==1,
            "WF98_"+reason+"_NOT_UNIQUE_IN_ACTUAL_PROSE")
    return {"start":loc[0],"end":loc[0]+len(text),
            "quote_sha256":digest(text.encode("utf8"))}


def latest_observed_effect(accepted):
    """Last V96-checked SOURCE effect quote; causation remains unproven.

    This must never be interpreted as a signed real-world causal relation.
    Quiet turns are skipped because they make no action/effect trace claim.
    """
    require(type(accepted) in (list,tuple) and
            len(accepted)>=1 and len(accepted)<=12,
            "WF98_NO_PRIOR_ACCEPTED_TURN")
    for turn in reversed(accepted):
        if (type(turn) is dict and
            type(turn.get("effect_quote")) is str and
            turn.get("effect_quote") and
            type(turn.get("prose")) is str):
            effect=turn["effect_quote"]
            require(len(_occurrences(turn["prose"],effect))==1,
                    "WF98_PARENT_EFFECT_NOT_UNIQUE_ANYMORE")
            receipt=turn.get("receipt")
            require(type(receipt) is dict and
                    receipt.get("causal_check")==
                        "EXACT_OBSERVABLE_ANCHORS_ONLY" and
                    receipt.get("turn_id")==turn.get("beat_id") and
                    receipt.get("prose_sha256")==
                        digest(turn["prose"].encode("utf8")) and
                    type(receipt.get("effect_anchor")) is dict and
                    receipt["effect_anchor"].get("quote_sha256")==
                        digest(effect.encode("utf8")) and
                    receipt["effect_anchor"].get("start")==
                        _occurrences(turn["prose"],effect)[0] and
                    receipt.get("receipt_sha256")==
                        digest(canonical({k:v for k,v in receipt.items()
                                 if k!="receipt_sha256"})),
                    "WF98_PARENT_V96_RECEIPT_NOT_INTACT")
            return turn
    raise V98RollingPlanError("WF98_NO_ACTUAL_PRIOR_EFFECT_TO_REPLAN_FROM")


def prepare_replan_instructions(*,accepted,seed_next_beat,
                                allowed_actor_names):
    previous=latest_observed_effect(accepted)
    source_review=previous["receipt"].get("source_causal_review_reason")
    require(type(seed_next_beat) is dict and
            set(seed_next_beat)==BEAT_FIELDS,
            "WF98_BAD_SEED_NEXT_BEAT")
    require(type(allowed_actor_names) in (tuple,list) and
            1<=len(allowed_actor_names)<=12 and
            all(_bounded(v,1,70) for v in allowed_actor_names),
            "WF98_INVALID_FROZEN_CAST")
    context=(
       "\n【刚刚真正写出的情节，而非计划中的情节】\n"
       +accepted[-1]["prose"][-760:]
       +"\n【前一项仅被确认在正文中出现的引句（未证明由先前动作造成）】\n"
       +previous["effect_quote"]
       +"\n【原来的下一事件建议，可根据实际变化改写，但不是已成立事实】\n"
       +json.dumps(seed_next_beat,ensure_ascii=False,separators=(",",":"))
       +"\n【已登场可选视角人物，不可虚构未出场的新身份】"
       +json.dumps(allowed_actor_names,ensure_ascii=False)
       +("\n【因果关系需审慎核实】先前两句字面先后只证明来源；"
         "出现巧合或限知猜测时不能自动认定动作造成了后果。"
         "可自然续写、调查或保留疑问，不得将人物猜测晋级已知事实。"
         if source_review else
         "\n【因果关系尚未独立证明】引句出现及先后仅是来源证据。")
       +"\n根据刚刚写出来的变化，提出**唯一一个**下一事件方向。"
       "人物必须仍有可理解的欲望和阻力；"
       "允许质疑原定目标、误会、倒叙、安静铺垫与开放悬念，"
       "不要求每个片段产生反转。新目标不是已知事实。"
       "\n只输出JSON，字段必须且只能为："
       '{"next_turn":{"id":"t02","kind":"decision","actor":"人物",'
       '"goal":"下一小步真正要解决的问题",'
       '"causal_parent":"t01","craft_focus":["detail"]},'
       '"basis_effect_quote":"必须逐字照抄上述真实变化",'
       '"pressure_quote":null或先前正文实际短引句,'
       '"cost_quote":null或先前正文实际短引句,'
       '"unresolved_question":"读者/人物还有什么不知道",'
       '"reason_for_shift":"为何这一步不同于最初静态计划"}。'
       "quote引句6至96字符且在旧正文唯一存在；"
       "代价未明确写出就填null，不得为了过测试伪造。"
       "只建议新情节，不能声明模型理解已被审核，也不能更改先前正文。"
    )
    require(len(context)<=MAX_ROLLING_CONTEXT_CHARS,
            "WF98_REPLAN_INPUT_BUDGET")
    return context


def validate_replan(raw,*,accepted,accepted_beats,seed_next_beat,
                    allowed_actor_names,author_forbidden_phrases=()):
    """One model proposal -> next frozen-for-this-step beat + metadata receipt.

    Caller saves the resulting private beat alongside draft, never CANON.
    All already generated prose is immutable during this operation. A plan
    is allowed to CHANGE because of consequences observed in the text.
    """
    require(type(accepted) in (tuple,list) and type(accepted_beats) in
            (tuple,list) and len(accepted)==len(accepted_beats) and
            1<=len(accepted)<=11,
            "WF98_ROLLING_HISTORY_INCOMPLETE")
    require(type(seed_next_beat) is dict and
            set(seed_next_beat)==BEAT_FIELDS,
            "WF98_BAD_FROZEN_PROPOSED_NEXT")
    require(type(allowed_actor_names) in (list,tuple) and
            1<=len(allowed_actor_names)<=12,
            "WF98_ROLLING_CAST_NOT_FROZEN")
    for t,beat in zip(accepted,accepted_beats):
        require(t.get("beat_id")==beat.get("id"),
                "WF98_HISTORY_BEAT_ID_CHANGED")
    parent=latest_observed_effect(accepted)
    doc=_decode(raw)
    proposal=doc["next_turn"]
    require(type(proposal) is dict and set(proposal)==BEAT_FIELDS and
            proposal.get("id")==seed_next_beat["id"] and
            proposal.get("actor") in allowed_actor_names and
            proposal.get("causal_parent")==parent["beat_id"],
            "WF98_NEXT_TURN_ID_CAST_OR_CAUSAL_PARENT_CHANGED")
    require(_bounded(doc["unresolved_question"],8,200) and
            _bounded(doc["reason_for_shift"],8,220),
            "WF98_ROLLING_MOTIVATION_OR_UNCERTAINTY_MISSING")
    require(doc["basis_effect_quote"]==parent["effect_quote"],
            "WF98_REPLAN_NOT_ANCHORED_TO_ACTUAL_EFFECT")
    basis=_anchor(parent["prose"],doc["basis_effect_quote"],"BASIS")
    costs={}
    for key in ("pressure_quote","cost_quote"):
        val=doc[key]
        if val is not None:
            # Optional. Missing cost is explicitly unknown rather than
            # a fabricated "price paid" from narrative planning.
            costs[key]=_anchor(parent["prose"],val,key.upper())
        else:
            costs[key]=None
    for forbidden in author_forbidden_phrases:
        require(type(forbidden) is str and
                len(forbidden)<=90 and forbidden not in
                (proposal["goal"]+" "+
                 doc["reason_for_shift"]+" "+
                 doc["unresolved_question"]),
                "WF98_AUTHOR_KNOWLEDGE_BOUNDARY_IN_NEXT_GOAL")
    try:
        parsed=parse_turn_outline(
            json.dumps({"turns":[*accepted_beats,proposal]},
                       ensure_ascii=False))
    except V96CausalDraftError as err:
        raise V98RollingPlanError(
            "WF98_NEXT_TURN_V96_OUTLINE_REJECTED_"+str(err)) from None
    require(parsed[-1]==proposal,
            "WF98_NEXT_TURN_MUTATED_AFTER_VALIDATION")
    parent_receipt=parent["receipt"]
    review_reason=parent_receipt.get("source_causal_review_reason")
    # Legacy receipts have no explicit source-relation classifier; do not
    # silently upgrade the older, purely lexical V96 evidence to fact.
    if "source_causal_review_required" not in parent_receipt:
        review_reason="LEGACY_SOURCE_ONLY_UNVERIFIED"
    candidate={
        "format":"wf.writing.rolling-proposal.v98",
        "beat_id":proposal["id"],
        "old_seed_beat_sha256":digest(canonical(seed_next_beat)),
        "proposed_beat_sha256":digest(canonical(proposal)),
        "grounded_prior_beat_id":parent["beat_id"],
        "grounded_prior_prose_sha256":digest(parent["prose"].encode("utf8")),
        "source_parent_relation_review_required":review_reason is not None,
        "source_parent_relation_review_reason":review_reason,
        "source_parent_causal_relation_verified":False,
        "source_basis_anchor":basis,
        "cost_anchor":costs["cost_quote"],
        "pressure_anchor":costs["pressure_quote"],
        "cost_state":"QUOTED_NOT_SEMANTICALLY_VERIFIED"
                     if costs["cost_quote"] else "UNRESOLVED_NOT_STATED",
        "open_question_sha256":digest(doc[
            "unresolved_question"].encode("utf8")),
        "reason_for_shift_sha256":digest(doc[
            "reason_for_shift"].encode("utf8")),
        "changed_from_frozen_seed":proposal!=seed_next_beat,
        "narrative_semantics_independently_verified":False,
        "character_knowledge_promoted_to_KNOWN":False,
        "canon_or_factjournal_writes":0,
        "skill_promotion_approved":False,
        "candidate_requires_author_acceptance":True,
        "model_calls_for_validation":0,
        "original_prose_and_explanation_not_exported":True,
    }
    candidate["receipt_sha256"]=digest(canonical(candidate))
    return proposal,candidate
