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
    CAUSAL_KINDS,BEAT_FIELDS,CRAFT,_occurrences,parse_turn_outline,
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


def latest_source_basis_for_replan(accepted):
    """Prefer the latest literal decision when its effect is still UNKNOWN.

    Never turn a pending action into an observed outcome. Validate the old
    V96 provenance and its complete receipt before a writer sees the text.
    Legacy effect-only paths retain latest_observed_effect's strict gate.
    """
    require(type(accepted) in (list,tuple) and
            1<=len(accepted)<=12,
            "WF98_NO_PRIOR_ACCEPTED_TURN")
    for turn in reversed(accepted):
        if type(turn) is not dict or type(turn.get("prose")) is not str:
            continue
        receipt=turn.get("receipt")
        if (type(receipt) is dict and
            receipt.get("outcome_pending_source_only") is True):
            anchor=receipt.get("action_anchor")
            prose=turn["prose"]
            valid=(
                receipt.get("kind")=="decision" and
                receipt.get("causal_check")=="EXACT_OBSERVABLE_ANCHORS_ONLY" and
                receipt.get("source_causal_review_reason")==
                    "DECISION_EFFECT_UNOBSERVED" and
                receipt.get("turn_id")==turn.get("beat_id") and
                receipt.get("prose_sha256")==digest(prose.encode("utf8")) and
                receipt.get("receipt_sha256")==digest(canonical({
                    k:v for k,v in receipt.items() if k!="receipt_sha256"})) and
                turn.get("effect_quote") is None and
                type(anchor) is dict and
                type(anchor.get("start")) is int and
                type(anchor.get("end")) is int and
                0<=anchor["start"]<anchor["end"]<=len(prose)
            )
            require(valid,"WF98_PARENT_PENDING_SOURCE_RECEIPT_NOT_INTACT")
            text=prose[anchor["start"]:anchor["end"]]
            require(6<=len(text)<=96 and
                    digest(text.encode("utf8"))==anchor.get("quote_sha256") and
                    len(_occurrences(prose,text))==1,
                    "WF98_PARENT_PENDING_ACTION_SOURCE_NOT_UNIQUE")
            return turn,text,"DECISION_ACTION_ONLY_OUTCOME_PENDING"
        if type(turn.get("effect_quote")) is str and turn["effect_quote"]:
            previous=latest_observed_effect((turn,))
            return previous,previous["effect_quote"],"EFFECT_SOURCE_ONLY"
    raise V98RollingPlanError("WF98_NO_ACTUAL_PRIOR_SOURCE_TO_REPLAN_FROM")


def g_source_replan_eligibility(accepted,*,allow_prose_only=False):
    """G: source-gate the immediately preceding real prose, not old beats.

    By default, preserve 0.AU's strict effect-only policy. Explicit G+V98
    may instead ask the *same author* to consider a signed REVIEW-only or
    quiet paragraph, provided it is never labelled a verified effect,
    causality, objective fact or canonical knowledge. This repairs the
    source-true literary stall seen after 0.AV's actual third paragraph.
    """
    require(type(accepted) in (tuple,list) and len(accepted)>0,
            "WF98_G_REPLAN_NO_SOURCE")
    require(type(allow_prose_only) is bool,
            "WF98_G_SOURCE_ONLY_SETTING_NOT_BOOL")
    last=accepted[-1]
    require(type(last) is dict and type(last.get("prose")) is str,
            "WF98_G_REPLAN_BAD_PREVIOUS")
    prose=last["prose"]
    receipt=last.get("receipt")
    require(type(receipt) is dict and
            receipt.get("prose_sha256")==digest(prose.encode("utf8")) and
            receipt.get("receipt_sha256")==digest(canonical({
                k:v for k,v in receipt.items() if k!="receipt_sha256"})) and
            receipt.get("turn_id")==last.get("beat_id"),
            "WF98_G_REPLAN_SOURCE_HASH_MISMATCH")
    mode=receipt.get("causal_check")
    source_only_kind=None
    if mode=="TRACE_REJECTED_SOURCE_PROSE_REVIEW_ONLY":
        reason="PREVIOUS_TRACE_REVIEW_ONLY"
        # A rejected claim about action/effect is NOT a rejection of the
        # writer's literal prose, nor proof that its events happened.
        if receipt.get("source_causal_review_reason")=="TRACE_REJECTED":
            source_only_kind="REVIEW_ONLY_PROSE_AUTHOR_ONLY"
    elif (receipt.get("outcome_pending_source_only") is True or
          type(last.get("effect_quote")) is str and last["effect_quote"]):
        # Reuse existing strict V98 validation instead of trusting metadata.
        latest_source_basis_for_replan((last,))
        reason=None
    else:
        reason="NO_VERIFIED_SOURCE_BASIS"
        if (mode=="EXACT_OBSERVABLE_ANCHORS_ONLY" and
                receipt.get("kind") in
                ("quiet","dialogue","setup","aftermath",
                 "transition","interiority") and
                receipt.get("action_anchor") is None and
                receipt.get("effect_anchor") is None and
                last.get("effect_quote") is None):
            source_only_kind="QUIET_PROSE_AUTHOR_ONLY"
    author_prose_only=allow_prose_only and source_only_kind is not None
    return {
        "eligible":reason is None or author_prose_only,
        "reason":None if author_prose_only else reason,
        "previous_source_review_reason":reason if author_prose_only else None,
        "source_basis_kind":source_only_kind if author_prose_only else None,
        "prose_only_unverified":author_prose_only,
        "source_sha256":receipt["prose_sha256"],
        "causal_truth_verified":False,"model_calls":0,
    }


def prepare_replan_instructions(*,accepted,seed_next_beat,
                                allowed_actor_names,allow_g_prose_only=False):
    require(type(allow_g_prose_only) is bool,
            "WF98_SOURCE_ONLY_WRITER_MODE_INVALID")
    if allow_g_prose_only:
        gate=g_source_replan_eligibility(
            accepted,allow_prose_only=True)
        require(gate["eligible"] and gate["prose_only_unverified"],
                "WF98_NO_SIGNED_PROSE_ONLY_WRITER_BASIS")
        previous=accepted[-1]
        basis_quote=None
        basis_kind=gate["source_basis_kind"]
    else:
        previous,basis_quote,basis_kind=latest_source_basis_for_replan(accepted)
    pending=basis_kind=="DECISION_ACTION_ONLY_OUTCOME_PENDING"
    source_review=previous["receipt"].get("source_causal_review_reason")
    require(type(seed_next_beat) is dict and
            set(seed_next_beat)==BEAT_FIELDS,
            "WF98_BAD_SEED_NEXT_BEAT")
    require(type(allowed_actor_names) in (tuple,list) and
            1<=len(allowed_actor_names)<=12 and
            all(_bounded(v,1,70) for v in allowed_actor_names),
            "WF98_INVALID_FROZEN_CAST")
    # 0.AV real DeepSeek RED: at t03 the former hardcoded t02/t01
    # JSON example contradicted the verified next beat t03 and parent t02.
    # Only IDs/parent are structural source coordinates. Every narrative
    # choice remains with the original writer, not with a host-written beat.
    source_parent_id=previous["beat_id"]
    next_turn_id=seed_next_beat["id"]
    # 0.AV actual B+ prose: t04 re-cut an already-cut signal because V98
    # only exposed t03 and a stale static beat, not t01's real switch
    # operation. Let the SAME writer actually reread bounded earlier prose.
    # No host summary, inferred holder, automatic chronology judgment or
    # fabricated event. Each visible earlier source MUST retain its signed
    # V96 prose receipt; a mismatched byte aborts before the next model call.
    recent_prior_literal=""
    if allow_g_prose_only and len(accepted)>1:
        source_parts=[]
        for original in accepted[-3:-1]:
            verified=g_source_replan_eligibility(
                (original,),allow_prose_only=True)
            require(verified["eligible"],
                    "WF98_PRIOR_LITERAL_PROSE_SOURCE_NOT_VERIFIED")
            source_parts.append(
                "\n【"+original["beat_id"]+" 实际已写正文 / SHA256 "+
                verified["source_sha256"]+"】\n"+
                original["prose"][-320:])
        recent_prior_literal=(
            "\n【更早两段的真实正文来源；顺序不等于因果，"
            "人物猜想不等于已知事实】"+
            "".join(source_parts))
    structural_example={
        "next_turn":{
            "id":next_turn_id,
            "kind":seed_next_beat["kind"],
            "actor":seed_next_beat["actor"],
            "goal":"下一小步真正要解决的问题与人物阻力",
            "causal_parent":source_parent_id,
            "craft_focus":seed_next_beat["craft_focus"],
        },
        "basis_effect_quote":(
            "从上面真实正文逐字选取唯一的6至96字引句"
            if allow_g_prose_only else basis_quote),
        "pressure_quote":None,
        "cost_quote":None,
        "unresolved_question":"尚未有人证实的关键事情是什么",
        "reason_for_shift":"前文实际写出的变化如何影响作者所选的新方向",
    }
    context=(
       "\n【刚刚真正写出的情节，而非计划中的情节】\n"
       +accepted[-1]["prose"][-760:]
       +("\n【上一段正文已保存，但它的动作/后果trace仅供复核】\n"
          "你可以依据真实文字自主重想下一步；原句只能证明书写来源，"
          "不能证明其中任何人物猜想、动作后果或物件状态。\n"
          if allow_g_prose_only else
          "\n【前一段确实写出的决定/尝试；后果尚未观察或尚未发生】\n"
          if pending else
          "\n【前一项仅被确认在正文中出现的引句（未证明由先前动作造成）】\n")
       +(basis_quote if basis_quote is not None else "")
       +("\n【旧字段兼容说明】本次 JSON 的 basis_effect_quote "
         "必须引用上面已写出的决定/行动原句，只是旧字段名；"
         "它不是 effect，不代表决定已产生结果。后果尚未发生时请继续保留未知。"
         if pending else "")
       +"\n【原来的下一事件建议，可根据实际变化改写，但不是已成立事实】\n"
       +json.dumps(seed_next_beat,ensure_ascii=False,separators=(",",":"))
       +recent_prior_literal
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
       "\n【本次真实来源顺序坐标】下一事件编号必须为 "
       +next_turn_id+"；上一段的来源父编号必须为 "+source_parent_id+
       "。这两个编号仅用于来源顺序定位，不代表已确认因果。"
       "\n只输出严格JSON；以下是当前编号的结构示例，不是要照搬的剧情、人物决策或已成立事实："
       +json.dumps(structural_example,ensure_ascii=False,separators=(",",":"))
       +"。kind、actor、goal、craft_focus 应由你自行决定，但actor限于已登场列表；"
       "id和causal_parent不能因剧情变化而改写。"
       "basis_effect_quote须为上一段原文中唯一出现的6至96字短引句；"
       "前文已观察的后果不是必须选择的文学重心，你可以引用其他真实细节，"
       "但不得把引句升级为已证因果；"
       +("前段trace未能证明动作或后果；请引用真实原文而不把它写作既成因果。"
         if allow_g_prose_only else
         "尚未观察结果的决定则只能引用已校验的真实决定/行动原句。")
       +"pressure_quote与cost_quote只能是上一段原文唯一短引句或JSON null；"
       "代价未明确写出就填null，不得为了过测试伪造。"
       "只建议新情节，不能声明模型理解已被审核，也不能更改先前正文。"
    )
    require(len(context)<=MAX_ROLLING_CONTEXT_CHARS,
            "WF98_REPLAN_INPUT_BUDGET")
    return context


def validate_replan(raw,*,accepted,accepted_beats,seed_next_beat,
                    allowed_actor_names,author_forbidden_phrases=(),
                    allow_g_prose_only=False):
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
    require(type(allow_g_prose_only) is bool,
            "WF98_SOURCE_ONLY_WRITER_MODE_INVALID")
    if allow_g_prose_only:
        gate=g_source_replan_eligibility(
            accepted,allow_prose_only=True)
        require(gate["eligible"] and gate["prose_only_unverified"],
                "WF98_NO_SIGNED_PROSE_ONLY_WRITER_BASIS")
        parent=accepted[-1]
        basis_quote=None
        basis_kind=gate["source_basis_kind"]
    else:
        parent,basis_quote,basis_kind=latest_source_basis_for_replan(accepted)
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
    # 0.AV REAL provider RED #40321793262. Only the optional, model-
    # generated craft_focus exceeded the original V96 two-tag vocabulary.
    # That is NOT a reason to discard the author's coherent character
    # choice or to pay for a newly hallucinated plan. Preserve the ORIGINAL
    # provider reply (caller writes it before validation), and record only
    # a bounded compatibility projection of optional craft metadata.
    # This never repairs source anchors, actor, goal, kind, id or parent.
    original_model_next_turn_sha256=digest(canonical(proposal))
    original_craft=proposal.get("craft_focus")
    removed_optional_craft_tags=[]
    if (type(original_craft) is list and len(original_craft)<=4 and
            all(type(tag) is str and _bounded(tag,1,32)
                for tag in original_craft)):
        cleaned=[]
        for tag in original_craft:
            if tag in CRAFT and tag not in cleaned and len(cleaned)<2:
                cleaned.append(tag)
            else:
                removed_optional_craft_tags.append(tag)
        if cleaned!=original_craft:
            proposal={**proposal,"craft_focus":cleaned}
    # 0.AV true DeepSeek author RED: the prior V96 "effect_quote"
    # identified the blackout, while the writer *correctly chose* a different
    # verbatim passage (countdown + missing hospital reading) as the pressure
    # driving the next choice. The old validator imposed its own choice of
    # literary focus and discarded the model's genuinely new next beat.
    #
    # V96 verifies only lexical positions, never that any particular quoted
    # effect is the best reason for the NEXT character decision. Permit the
    # AUTHOR to select another UNIQUE, BOUNDED, LITERAL passage in the SAME
    # signed prior prose. Mark it as unverified source, not effect/cause.
    # Pending-action cases remain strict: do not smuggle an outcome via an
    # unrelated quote when the old author's decision has no observed effect.
    writer_basis=doc["basis_effect_quote"]
    author_selected_other_basis=writer_basis!=basis_quote
    if basis_kind=="DECISION_ACTION_ONLY_OUTCOME_PENDING":
        require(not author_selected_other_basis,
                "WF98_REPLAN_NOT_ANCHORED_TO_ACTUAL_SOURCE_BASIS")
    elif author_selected_other_basis:
        require(_bounded(writer_basis,6,MAX_SHORT_QUOTE_CHARS) and
                len(_occurrences(parent["prose"],writer_basis))==1,
                "WF98_REPLAN_NOT_ANCHORED_TO_ACTUAL_EFFECT")
    basis=_anchor(parent["prose"],writer_basis,"BASIS")
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
    if allow_g_prose_only:
        review_reason=(
            "PREVIOUS_TRACE_REVIEW_ONLY" if
            basis_kind=="REVIEW_ONLY_PROSE_AUTHOR_ONLY" else
            "NO_VERIFIED_CAUSAL_SOURCE_IN_QUIET_PROSE")
    # Legacy receipts have no explicit source-relation classifier; do not
    # silently upgrade the older, purely lexical V96 evidence to fact.
    if "source_causal_review_required" not in parent_receipt:
        review_reason="LEGACY_SOURCE_ONLY_UNVERIFIED"
    if basis_kind=="DECISION_ACTION_ONLY_OUTCOME_PENDING":
        review_reason="DECISION_EFFECT_UNOBSERVED"
    candidate={
        "format":"wf.writing.rolling-proposal.v98",
        "beat_id":proposal["id"],
        "old_seed_beat_sha256":digest(canonical(seed_next_beat)),
        "proposed_beat_sha256":digest(canonical(proposal)),
        "original_model_next_turn_sha256":original_model_next_turn_sha256,
        "only_optional_model_craft_adjusted":bool(removed_optional_craft_tags),
        "removed_optional_craft_tags":removed_optional_craft_tags,
        "original_model_answer_must_be_preserved":True,
        "grounded_prior_beat_id":parent["beat_id"],
        "grounded_prior_prose_sha256":digest(parent["prose"].encode("utf8")),
        "source_parent_relation_review_required":(
            review_reason is not None or author_selected_other_basis or
            allow_g_prose_only),
        "source_parent_relation_review_reason":review_reason,
        "source_parent_causal_relation_verified":False,
        "source_basis_kind":(
            basis_kind if allow_g_prose_only else
            "AUTHOR_SELECTED_OTHER_LITERAL_SOURCE_ONLY"
            if author_selected_other_basis else basis_kind),
        "review_only_or_quiet_prose_writer_plan":allow_g_prose_only,
        "review_only_prose_never_promoted_to_action_or_effect":
            allow_g_prose_only,
        "source_basis_is_observed_effect":(
            basis_kind=="EFFECT_SOURCE_ONLY" and
            not author_selected_other_basis and not allow_g_prose_only),
        "author_selected_non_effect_literal_source_only":(
            author_selected_other_basis),
        "original_v96_source_basis_sha256":(
            digest(basis_quote.encode("utf8"))
            if basis_quote is not None else None),
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
