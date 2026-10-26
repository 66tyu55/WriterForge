"""V96 opt-in scene-turn causal draft boundary, never a literary judge.

The LLM keeps freedom to write the prose; a small rolling event plan selects
WHAT to attempt, never mandates an eight-beat formula. Host only checks
provable constraints: ordered existing turn IDs, explicitly authorized
knowledge exclusions, literal observable anchors in actual generated prose,
and trace links to an earlier already-generated effect. No model can make
its own narrative proposition a permanently KNOWN fact merely by quoting it.

A matching quote is source-existence evidence, NOT proof of literary
motivation/causation. All results stay unaccepted candidate drafts, never
write to FactJournal, R2, experience review, or model weights.
"""
from __future__ import annotations
from hashlib import sha256
import json
import re

MAX_TURNS=12
MIN_TURNS=2
MAX_PLAN_JSON_BYTES=14000
MAX_TURN_JSON_BYTES=15000
MIN_PROSE_CHARS=80
MAX_PROSE_CHARS=950
# V96 legacy remains strict; opt-in unified writer accepts only small overage.
CONTINUITY_MAX_PROSE_CHARS=1024
MIN_QUOTE_CHARS=6
MAX_QUOTE_CHARS=96
MAX_CONTEXT_CHARS=3500
MAX_APPROVED_EXCLUSIONS=16
CAUSAL_KINDS=frozenset(("action","decision","reversal"))
KINDS=CAUSAL_KINDS | {"setup","dialogue","quiet","aftermath","transition"}
CRAFT=frozenset((
    "dialogue","detail","interiority","pacing","restraint","contrast",
    "action","none",
))
BEAT_FIELDS=frozenset((
    "id","kind","actor","goal","causal_parent","craft_focus",
))
TRACE_FIELDS=frozenset((
    "action_quote","effect_quote","parent_effect_quote",
))
TURN_FIELDS=frozenset(("prose","trace"))


class V96CausalDraftError(ValueError):
    pass


def need(condition, code):
    if not condition:
        raise V96CausalDraftError(code)


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")


def digest(raw):
    return sha256(raw).hexdigest()


def _strict_json(raw,max_size):
    need(type(raw) is str,"WF96_JSON_INPUT_NOT_STRING")
    try:
        raw_bytes=raw.encode("utf8","strict")
    except UnicodeError:
        raise V96CausalDraftError("WF96_JSON_BAD_UNICODE") from None
    need(2<=len(raw_bytes)<=max_size,"WF96_JSON_INPUT_BOUND")
    try:
        def pairs(items):
            data={}
            for key,value in items:
                if key in data:
                    raise ValueError("duplicate field")
                data[key]=value
            return data
        obj=json.loads(raw,object_pairs_hook=pairs,
                       parse_constant=lambda _:(_ for _ in ()).throw(
                           ValueError("nonfinite")))
        canonical(obj)
    except (ValueError,TypeError,UnicodeError,OverflowError):
        raise V96CausalDraftError("WF96_JSON_INVALID_OR_DUPLICATE_KEYS") from None
    need(type(obj) is dict,"WF96_JSON_NOT_OBJECT")
    return obj


def _text(value,low=1,high=240):
    if type(value) is not str or not low<=len(value.strip())<=high:
        return False
    if "\ufffd" in value or "\x00" in value:
        return False
    try:
        return value.encode("utf8","strict").decode("utf8","strict")==value
    except UnicodeError:
        return False


def parse_turn_outline(raw):
    """Only provisional scene directions; not confirmed plot/canon."""
    obj=_strict_json(raw,MAX_PLAN_JSON_BYTES)
    need(set(obj)=={"turns"} and type(obj["turns"]) is list and
         MIN_TURNS<=len(obj["turns"])<=MAX_TURNS,
         "WF96_OUTLINE_TURN_COUNT_OR_SCHEMA_INVALID")
    prior={}
    approved=[]
    for idx,beat in enumerate(obj["turns"],1):
        need(type(beat) is dict and set(beat)==BEAT_FIELDS and
             beat["id"]==f"t{idx:02d}" and
             type(beat["kind"]) is str and beat["kind"] in KINDS and
             _text(beat["actor"],1,70) and
             _text(beat["goal"],8,220) and
             type(beat["craft_focus"]) is list and
             0<=len(beat["craft_focus"])<=2 and
             all(type(c) is str and c in CRAFT for c in beat["craft_focus"]) and
             len(set(beat["craft_focus"]))==len(beat["craft_focus"]),
             "WF96_TURN_PLAN_FIELDS_ID_OR_CRAFT_INVALID")
        parent=beat["causal_parent"]
        # A model's provisional dependency plan is NOT an observed cause.
        # Dialogue may provoke a decision, and a quiet passage may only be
        # a temporal handoff. Check the ACTUAL prior prose when authored;
        # never infer causality from this link alone.
        need(parent is None or (
             type(parent) is str and parent in prior),
             "WF96_CAUSAL_PARENT_NOT_PRIOR_TURN")
        prior[beat["id"]]=beat["kind"]
        approved.append(beat)
    need(len(canonical(obj))<=MAX_PLAN_JSON_BYTES,
         "WF96_TURN_PLAN_CANONICAL_BUDGET")
    return tuple(approved)


def _occurrences(haystack,needle):
    found=[]
    cursor=0
    while True:
        position=haystack.find(needle,cursor)
        if position<0:
            return found
        found.append(position)
        if len(found)>1:
            return found
        cursor=position+1  # detects overlapping duplicate occurrences


def _quote_anchor(prose,quote,name):
    need(_text(quote,MIN_QUOTE_CHARS,MAX_QUOTE_CHARS),
         "WF96_"+name+"_QUOTE_NOT_BOUNDED")
    found=_occurrences(prose,quote)
    need(len(found)==1,"WF96_"+name+"_NOT_UNIQUE_IN_ACTUAL_PROSE")
    start=found[0]
    # Conservative suspicion, not a natural-language theorem: refusing a
    # suspected negated assertion is preferable to recording a fake event.
    prefix=prose[max(0,start-5):start]
    need(not re.search(r"(?:没有|并非|未曾|从未|不曾|未|没|不)[^。！？；\n]{0,2}$",
                       prefix),
         "WF96_POLARITY_UNCERTAIN_NEEDS_REVIEW")
    return {"start":start,"end":start+len(quote),
            "quote_sha256":digest(quote.encode("utf8"))}


def _verified_noncausal_temporal_parent(prior):
    """Verify a non-causal turn's actual source for temporal handoff ONLY.

    Valid dialogue/quiet/setup/transition/aftermath prose may have no effect
    quote. This permits later prose to FOLLOW it, but never to cite a made-up
    result or mark the predecessor as a proven cause. No prose is rewritten.
    """
    need(type(prior) is dict and type(prior.get("prose")) is str,
         "WF96_NONCAUSAL_PARENT_SOURCE_INVALID")
    prose=prior["prose"]
    receipt=prior.get("receipt")
    need(type(receipt) is dict and
         receipt.get("kind") in
             ("setup","dialogue","quiet","aftermath","transition") and
         receipt.get("causal_check")=="EXACT_OBSERVABLE_ANCHORS_ONLY" and
         receipt.get("turn_id")==prior.get("beat_id") and
         receipt.get("prose_sha256")==digest(prose.encode("utf8")) and
         receipt.get("receipt_sha256")==digest(canonical({
             k:v for k,v in receipt.items() if k!="receipt_sha256"})) and
         prior.get("effect_quote") is None and
         receipt.get("action_anchor") is None and
         receipt.get("effect_anchor") is None and
         receipt.get("causal_relation_verified") is False and
         receipt.get("eligible_for_factjournal_KNOWN") is False and
         receipt.get("candidate_requires_author_acceptance") is True,
         "WF96_NONCAUSAL_PARENT_SOURCE_INVALID")
    return receipt["prose_sha256"]


def _source_causal_relation_review(prose, action, effect, action_quote,
                                   effect_quote):
    """Conservative *review cues*, never a host verdict on literary causality.

    Citation order cannot prove that an action caused the quoted outcome.
    Explicit unrelatedness, a localized subjective guess, or coincidence
    wording requires *source-relation review*, not rejection of valid prose.
    A missing cue never means CAUSAL_TRUE. Keep original characters intact.
    """
    between=prose[action["end"]:effect["start"]]
    if re.search(
        r"(?:与|和|跟)[^。！？；\n]{0,24}(?:毫无关系|完全无关|无关|没有关系)"
        r"|(?:与此无关|只是巧合|并非由)",between
    ):
        return "EXPLICITLY_DISCONNECTED"
    # Only the immediately preceding clause, not an earlier person's
    # unrelated thoughts. A belief is an observation of the BELIEF, not
    # proof that the imagined event happened behind the door.
    prefix=prose[max(0,action["start"]-24):action["start"]]
    clause=re.split(r"[。！？；，：:\n]",prefix)[-1]
    if re.search(
        r"(?:猜|猜想|猜测|以为|怀疑|听说|据说|假设|如果|假如|"
        r"也许|可能|似乎|仿佛|好像)$",clause
    ):
        return "POV_UNOBSERVED"
    # A coincidence marker is NOT proof of noncausation. Flag uncertainty
    # without hard-blocking a true cause that happens to use this wording.
    if re.search(r"(?:正好|恰好|刚巧|碰巧|凑巧|纯属巧合)",
                 effect_quote):
        return "POSSIBLE_COINCIDENCE"
    return None


def _approved_exclusions(phrases):
    need(type(phrases) in (list,tuple) and
         len(phrases)<=MAX_APPROVED_EXCLUSIONS and
         all(_text(x,3,90) for x in phrases) and
         len(set(phrases))==len(phrases),
         "WF96_AUTHOR_GUARD_LIST_INVALID")
    return tuple(phrases)


def check_turn(raw,beat, *, mode, accepted=(),
               author_confirmed_forbidden_phrases=(),
               max_prose_chars=MAX_PROSE_CHARS):
    """Return a provisional prose and metadata-only receipt.

    B (split_only): segmentation without evidence gate; C (causal_guard):
    same JSON response format but strict anchors/parent/evidence checks.
    WriterForge only has a verified quote, not independent literary truth.
    """
    need(mode in ("split_only","causal_guard"),
         "WF96_UNKNOWN_EXPERIMENTAL_DRAFT_MODE")
    need(type(beat) is dict and set(beat)==BEAT_FIELDS,
         "WF96_TURN_BEAT_NOT_FROZEN")
    need(type(max_prose_chars) is int and max_prose_chars in
         (MAX_PROSE_CHARS,CONTINUITY_MAX_PROSE_CHARS),
         "WF96_UNTRUSTED_TURN_PROSE_LIMIT")
    guards=_approved_exclusions(author_confirmed_forbidden_phrases)
    doc=_strict_json(raw,MAX_TURN_JSON_BYTES)
    need(set(doc)==TURN_FIELDS and
         _text(doc["prose"],MIN_PROSE_CHARS,max_prose_chars) and
         type(doc["trace"]) is dict and
         set(doc["trace"])==TRACE_FIELDS,
         "WF96_TURN_PROSE_OR_TRACE_SCHEMA_INVALID")
    prose=doc["prose"].strip()
    need(len(canonical(doc))<=MAX_TURN_JSON_BYTES,
         "WF96_TURN_OUTPUT_EXCEEDS_BYTE_LIMIT")
    recorded={
        "format":"wf.writing.candidate-turn.v96",
        "turn_id":beat["id"],
        "prose_sha256":digest(prose.encode("utf8")),
        "prose_chars":len(prose),
        "source_turn_exceeds_legacy_v96_chars":len(prose)>MAX_PROSE_CHARS,
        "source_turn_requires_length_review":len(prose)>MAX_PROSE_CHARS,
        "prose_not_silently_truncated":True,
        "kind":beat["kind"],
        "parent_turn_id":beat["causal_parent"],
        "causal_check":"SPLIT_ONLY_UNVERIFIED",
        "source_causal_review_reason":None,
        "source_causal_review_required":False,
        "causal_relation_verified":False,
        "outcome_pending_source_only":False,
        "action_anchor":None,"effect_anchor":None,
        "parent_effect_sha256":None,
        "parent_outcome_pending":False,
        "parent_source_action_sha256":None,
        "parent_temporal_link_unverified":False,
        "parent_temporal_source_sha256":None,
        "inherited_canon_facts_written":False,
        "literary_causality_independently_verified":False,
        "eligible_for_factjournal_KNOWN":False,
        "eligible_for_experience_promotion":False,
        "candidate_requires_author_acceptance":True,
        "source_novel_text_in_receipt":False,
        "model_calls_for_validation":0,
    }
    effect=None
    if mode=="causal_guard":
        for forbidden in guards:
            need(forbidden not in prose,
                 "WF96_AUTHOR_CONFIRMED_KNOWLEDGE_BOUNDARY_VIOLATION")
        trace=doc["trace"]
        action,effect_quote=trace["action_quote"],trace["effect_quote"]
        parent=beat["causal_parent"]
        old={r["beat_id"]:r for r in accepted}
        need(parent is None or parent in old,
             "WF96_CAUSAL_PARENT_NOT_YET_WRITTEN")
        if parent is None:
            need(trace["parent_effect_quote"] is None,
                 "WF96_UNDECLARED_PREVIOUS_CAUSE")
        else:
            prior=old[parent]
            required=prior.get("effect_quote")
            if type(required) is str and required:
                need(trace["parent_effect_quote"]==required and
                     len(_occurrences(prior["prose"],required))==1,
                     "WF96_PARENT_CAUSE_NOT_ANCHORED_IN_PREVIOUS_PROSE")
                recorded["parent_effect_sha256"]=digest(
                    required.encode("utf8"))
            elif (type(prior.get("receipt")) is dict and
                  prior["receipt"].get("outcome_pending_source_only") is True):
                # An actual authored decision may not have an observed
                # consequence yet. The later turn can follow the literal
                # decision as an UNRESOLVED candidate, never as a proved
                # result. The previous source and anchor MUST still match
                # its self-contained integrity receipt.
                old_receipt=prior.get("receipt")
                old_prose=prior.get("prose")
                prior_anchor=(old_receipt.get("action_anchor")
                              if type(old_receipt) is dict else None)
                valid_source=(
                    type(old_prose) is str and type(old_receipt) is dict and
                    old_receipt.get("kind")=="decision" and
                    old_receipt.get("outcome_pending_source_only") is True and
                    old_receipt.get("source_causal_review_reason")==
                        "DECISION_EFFECT_UNOBSERVED" and
                    old_receipt.get("turn_id")==prior.get("beat_id") and
                    old_receipt.get("prose_sha256")==
                        digest(old_prose.encode("utf8")) and
                    old_receipt.get("receipt_sha256")==
                        digest(canonical({k:v for k,v in old_receipt.items()
                                          if k!="receipt_sha256"})) and
                    type(prior_anchor) is dict and
                    type(prior_anchor.get("start")) is int and
                    type(prior_anchor.get("end")) is int and
                    0<=prior_anchor["start"]<prior_anchor["end"]<=len(old_prose)
                )
                need(valid_source,
                     "WF96_PARENT_PENDING_DECISION_SOURCE_INVALID")
                parent_action=old_prose[
                    prior_anchor["start"]:prior_anchor["end"]]
                need(digest(parent_action.encode("utf8"))==
                        prior_anchor.get("quote_sha256") and
                     len(_occurrences(old_prose,parent_action))==1,
                     "WF96_PARENT_PENDING_ACTION_ANCHOR_INVALID")
                need(trace["parent_effect_quote"] is None,
                     "WF96_PARENT_PENDING_MUST_NOT_CLAIM_EFFECT")
                recorded["parent_outcome_pending"]=True
                recorded["parent_source_action_sha256"]=(
                    prior_anchor["quote_sha256"])
            else:
                # A quiet or dialogue turn without an actual quoted effect
                # may still be a legitimate temporal predecessor. Verify
                # its signed literal prose and keep this as REVIEW only.
                # Parent effects stay null; this is NEVER a proved cause.
                temporal_source=_verified_noncausal_temporal_parent(prior)
                need(trace["parent_effect_quote"] is None,
                     "WF96_NONCAUSAL_PARENT_EFFECT_MUST_BE_NULL")
                recorded["parent_temporal_source_sha256"]=temporal_source
                recorded["parent_temporal_link_unverified"]=True
                recorded["source_causal_review_reason"]=(
                    "PARENT_UNOBSERVED_TEMPORAL_LINK")
                recorded["source_causal_review_required"]=True
        # A decision can be genuinely made without an OBSERVED effect in
        # this paragraph. Force the action to exist in the original prose,
        # but do not force a later unrelated event into effect_quote.
        # This is a SOURCE-only pending candidate, never source-certified
        # literary causation or world-state promotion.
        decision_pending=(beat["kind"]=="decision" and
                          action is not None and effect_quote is None)
        if beat["kind"] in CAUSAL_KINDS:
            need(action is not None and
                 (effect_quote is not None or decision_pending),
                 "WF96_ACTION_NEEDS_ACTUAL_ACTION_AND_EFFECT")
        if decision_pending:
            recorded["action_anchor"]=_quote_anchor(prose,action,"ACTION")
            recorded["source_causal_review_reason"]=(
                "DECISION_EFFECT_UNOBSERVED")
            recorded["source_causal_review_required"]=True
            recorded["outcome_pending_source_only"]=True
        elif action is None or effect_quote is None:
            need(action is None and effect_quote is None,
                 "WF96_PARTIAL_ACTION_EFFECT_NOT_ALLOWED")
        else:
            a=_quote_anchor(prose,action,"ACTION")
            b=_quote_anchor(prose,effect_quote,"EFFECT")
            need(a["end"]<=b["start"],
                 "WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED")
            recorded["action_anchor"]=a
            recorded["effect_anchor"]=b
            reason=_source_causal_relation_review(
                prose,a,b,action,effect_quote)
            recorded["source_causal_review_reason"]=reason
            recorded["source_causal_review_required"]=reason is not None
            # The trace remains a valid candidate SOURCE citation when a
            # review cue appears; it is never a certified event cause.
            effect=effect_quote
        recorded["causal_check"]="EXACT_OBSERVABLE_ANCHORS_ONLY"
    recorded["receipt_sha256"]=digest(canonical(recorded))
    return {
        "beat_id":beat["id"],"prose":prose,
        "effect_quote":effect,
        "receipt":recorded,
    }


def make_turn_instructions(beat,*,mode,accepted=(),
                           author_confirmed_forbidden_phrases=()):
    need(mode in ("split_only","causal_guard"),
         "WF96_DRAFT_MODE_NOT_OPT_IN")
    guards=_approved_exclusions(author_confirmed_forbidden_phrases)
    previous=accepted[-1]["prose"][-620:] if accepted else ""
    effects=[r["effect_quote"] for r in accepted[-3:]
             if r.get("effect_quote")]
    note=(
        "请自由地写一个自然完整的原创叙事片段，约250到650汉字；"
        "允许留白、倒叙、对话和安静铺垫，不要求每段惊天反转。"
        "不要解释写作技巧，不直接讲道理。"
        "仅输出严格JSON："
        '{"prose":"实际正文","trace":{"action_quote":null或正文原句,'
        '"effect_quote":null或正文原句,'
        '"parent_effect_quote":null或先前真实后果短句}}。'
        "所有引用必须与实际正文完全一致；action先于effect；"
        "action/effect各6到96字。对安静场景可全部为null。"
        "【决策可合法未完成】decision 场景若正文确实写出决定或尝试，"
        "但后果尚未观察或尚未发生，必须引用真实 action_quote，"
        "effect_quote 可填 JSON null，不能为了填满引用而编造结果。"
    )
    if mode=="causal_guard":
        note+=(
            "\n【仅用于候选层的程序核验】"
            "实际文字需体现当前事件的选择/阻力/变化；若前因未出现，"
            "请承认不确定，不得凭空宣布已造成后果。"
            "引句先后不证明因果；若只是巧合或人物猜测，"
            "仍保持未知，不得当作已验证因果。"
            "你对人物动机的判断尚未证明，不能输出已验证事实状态。"
        )
    if mode=="causal_guard":
        if beat["causal_parent"] is None:
            # The model must not confuse a planned objective with an ACTUAL
            # preceding event. This is a JSON provenance rule, not a
            # writer-supplied motivation or narrative plot answer.
            note+=("\n【第一事件的前因字段】此事件没有前一段已写正文；"
                   'trace.parent_effect_quote 必须是JSON null。'
                   "不可把规划里的目标、章节概括或未发生的选择当作引用。")
        else:
            predecessor=next((v for v in accepted
                if type(v) is dict and v.get("beat_id")==beat["causal_parent"]),None)
            if (type(predecessor) is dict and
                type(predecessor.get("receipt")) is dict and
                predecessor["receipt"].get("outcome_pending_source_only") is True):
                note+=("\n【承接一个尚未产生可证后果的决定】"
                       "前文 action 真实写出但没有 effect；"
                       "trace.parent_effect_quote 必须为 JSON null。"
                       "下一场可调查、等待或推进，不可宣称已经发生未写出的结果。")
            elif (type(predecessor) is dict and
                  predecessor.get("effect_quote") is None and
                  type(predecessor.get("receipt")) is dict and
                  predecessor["receipt"].get("kind") in
                     ("setup","dialogue","quiet","aftermath","transition")):
                note+=("\n【只承接前文已写的叙事顺序，因果仍未证实】"
                       "前一场没有可引用的实际后果。"
                       "trace.parent_effect_quote 必须是 JSON null。"
                       "允许安静观察后自然续写，但不能编造前因或结果。")
            else:
                note+=("\n【承接真实已写前因】trace.parent_effect_quote"
                       "必须逐字引用前文已实际出现的后果，"
                       "不能凭计划概括、虚构或自行改写。")
    output=(
        "\n【滚动场景目标（候选大纲，不是已知事实）】"
        +json.dumps(beat,ensure_ascii=False,separators=(",",":"))
        +"\n【上一段实际候选正文结尾】"+previous
        +"\n【前几个场景实际引句所见后果，仍未文学审核】"
        +json.dumps(effects,ensure_ascii=False)
        +("\n【作者明确排除的知识/词组】"+
           json.dumps(guards,ensure_ascii=False) if guards else "")
        +"\n"+note
    )
    need(len(output)<=MAX_CONTEXT_CHARS,
         "WF96_SCENE_TURN_CONTEXT_BUDGET_EXCEEDED")
    return output



def normalize_model_source_citations(raw,beat,accepted=()):
    """Fix *citation spelling* only; never alter original generated prose.

    The model sometimes quotes '他把信...' when the actual text says
    '沈砚把信...': the full predicate is an unambiguous literal substring.
    It also quotes just the first source-backed sentence of a previous
    effect. The strict citation checker continues to validate the
    normalized references. All semantic errors and unclear matches remain.
    """
    if type(raw) is not str or type(beat) is not dict:
        return raw,None
    try:
        doc=_strict_json(raw,MAX_TURN_JSON_BYTES)
        need(set(doc)==TURN_FIELDS and
             _text(doc.get("prose"),MIN_PROSE_CHARS,MAX_PROSE_CHARS) and
             type(doc.get("trace")) is dict and
             set(doc["trace"])==TRACE_FIELDS,
             "WF96_RECOVERY_NOT_A_VALID_PROSE_ENVELOPE")
    except V96CausalDraftError:
        return raw,None
    source=doc["prose"].strip()
    trace=doc["trace"]
    changed=[]
    for label in ("action_quote","effect_quote"):
        quote=trace[label]
        if type(quote) is not str or len(quote)<13 or len(quote)>MAX_QUOTE_CHARS:
            continue
        if _occurrences(source,quote):
            continue
        possible=[]
        # Only drop a SINGLE demonstrably mismatched personal pronoun.
        # Never trim negation ("不", "没") or an event's substantive words.
        if quote[0] in "他她它" and len(quote)>=13:
            possible.append(("STRIP_SOURCE_MISMATCHED_PRONOUN",quote[1:]))
        # Omitting the very last punctuation is a citation normalization,
        # not a new fictional event. No lexical/semantic guesswork.
        if quote[-1] in "，；。！？" and len(quote)>=13:
            possible.append(("STRIP_CITATION_END_PUNCTUATION",quote[:-1]))
        for operation,candidate in possible:
            if (len(_occurrences(source,candidate))==1 and
                12<=len(candidate)<=MAX_QUOTE_CHARS):
                try:
                    _quote_anchor(source,candidate,label.upper().replace("_QUOTE",""))
                except V96CausalDraftError:
                    continue
                trace[label]=candidate
                changed.append({
                    "field":label,"repair_kind":operation,
                    "actual_quote_sha256":digest(candidate.encode("utf8")),
                    "original_quote_sha256":digest(quote.encode("utf8")),
                })
                break
    parent=beat.get("causal_parent")
    prior={x["beat_id"]:x for x in accepted if type(x) is dict and
           type(x.get("beat_id")) is str}
    required=prior.get(parent,{}).get("effect_quote") if parent else None
    supplied=trace["parent_effect_quote"]
    if (type(required) is str and type(supplied) is str and
        supplied!=required and len(supplied)>=16 and
        required.startswith(supplied) and
        len(_occurrences(prior[parent]["prose"],required))==1):
        trace["parent_effect_quote"]=required
        changed.append({
            "field":"parent_effect_quote",
            "repair_kind":"EXPAND_EXACT_PREVIOUS_EFFECT_PREFIX",
            "actual_quote_sha256":digest(required.encode("utf8")),
            "original_quote_sha256":digest(supplied.encode("utf8")),
        })
    if not changed:
        return raw,None
    result=json.dumps(doc,ensure_ascii=False,separators=(",",":"))
    need(len(result.encode("utf8"))<=MAX_TURN_JSON_BYTES,
         "WF96_SOURCE_CITATION_NORMALIZED_OUTPUT_TOO_LARGE")
    return result,{
        "format":"wf.writing.source-citation-spelling-only.v1",
        "original_model_response_sha256":digest(raw.encode("utf8")),
        "normalized_response_sha256":digest(result.encode("utf8")),
        "prose_sha256":digest(source.encode("utf8")),
        "model_prose_unchanged":True,
        "no_causal_meaning_or_literary_quality_inferred":True,
        "source_quote_replacements":changed,
        "extra_model_calls":0,"canon_writes":0,
    }


TRACE_ONLY_REVIEW_ERRORS=frozenset((
    "WF96_ACTION_NOT_UNIQUE_IN_ACTUAL_PROSE",
    "WF96_EFFECT_NOT_UNIQUE_IN_ACTUAL_PROSE",
    "WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED",
    "WF96_PARENT_CAUSE_NOT_ANCHORED_IN_PREVIOUS_PROSE",
    "WF96_ACTION_NEEDS_ACTUAL_ACTION_AND_EFFECT",
    "WF96_PARTIAL_ACTION_EFFECT_NOT_ALLOWED",
    "WF96_POLARITY_UNCERTAIN_NEEDS_REVIEW",
    "WF96_ACTION_QUOTE_NOT_BOUNDED",
    "WF96_EFFECT_QUOTE_NOT_BOUNDED",
))


def trace_failure_reviewable(failure_code):
    """Only wrong self-citation is reviewable; never malformed real prose."""
    return failure_code in TRACE_ONLY_REVIEW_ERRORS


def review_only_model_turn(raw,beat,*,failure_code,accepted=(),
                           author_confirmed_forbidden_phrases=(),
                           max_prose_chars=MAX_PROSE_CHARS):
    """Salvage a source-valid literary DRAFT, not a proven causal turn.

    Optional model trace mistakes (overlapping/self-contradictory citations,
    omitted/incorrect earlier effect) must not destroy real prose. Strict
    original validation has already run and refused that trace. Missing or
    malformed prose, author exclusions and declared parent IDs remain hard.
    Nothing from this draft is eligible for canon/knowledge promotion.
    """
    need(trace_failure_reviewable(failure_code),
         "WF96_TRACE_RECOVERY_NOT_AN_OPTIONAL_CITATION_FAILURE")
    need(type(max_prose_chars) is int and max_prose_chars in
         (MAX_PROSE_CHARS,CONTINUITY_MAX_PROSE_CHARS),
         "WF96_UNTRUSTED_TURN_PROSE_LIMIT")
    doc=_strict_json(raw,MAX_TURN_JSON_BYTES)
    need(type(beat) is dict and set(beat)==BEAT_FIELDS and
         set(doc)==TURN_FIELDS and
         _text(doc.get("prose"),MIN_PROSE_CHARS,max_prose_chars) and
         type(doc.get("trace")) is dict and
         set(doc["trace"])==TRACE_FIELDS,
         "WF96_TRACE_RECOVERY_UNSAFE_PROSE_OR_SCHEMA")
    prose=doc["prose"].strip()
    need(len(canonical(doc))<=MAX_TURN_JSON_BYTES,
         "WF96_TRACE_RECOVERY_EXCEEDS_BOUNDS")
    parent=beat.get("causal_parent")
    need(parent is None or
         parent in {row.get("beat_id") for row in accepted},
         "WF96_TRACE_RECOVERY_PARENT_NOT_WRITTEN")
    for excluded in _approved_exclusions(author_confirmed_forbidden_phrases):
        need(excluded not in prose,
             "WF96_AUTHOR_CONFIRMED_KNOWLEDGE_BOUNDARY_VIOLATION")
    receipt={
        "format":"wf.writing.candidate-turn.v96",
        "turn_id":beat["id"],
        "prose_sha256":digest(prose.encode("utf8")),
        "prose_chars":len(prose),
        "source_turn_exceeds_legacy_v96_chars":len(prose)>MAX_PROSE_CHARS,
        "source_turn_requires_length_review":len(prose)>MAX_PROSE_CHARS,
        "prose_not_silently_truncated":True,
        "kind":beat["kind"],
        "parent_turn_id":parent,
        "causal_check":"TRACE_REJECTED_SOURCE_PROSE_REVIEW_ONLY",
        "source_causal_review_reason":"TRACE_REJECTED",
        "source_causal_review_required":True,
        "causal_relation_verified":False,
        "action_anchor":None,"effect_anchor":None,
        "parent_effect_sha256":None,
        "model_trace_failure_code":failure_code,
        "model_trace_not_proof_of_causality":True,
        "inherited_canon_facts_written":False,
        "literary_causality_independently_verified":False,
        "eligible_for_factjournal_KNOWN":False,
        "eligible_for_experience_promotion":False,
        "candidate_requires_author_acceptance":True,
        "source_novel_text_in_receipt":False,
        "model_calls_for_validation":0,
    }
    receipt["receipt_sha256"]=digest(canonical(receipt))
    return {"beat_id":beat["id"],"prose":prose,
            "effect_quote":None,"receipt":receipt}


def assemble_prose(turns):
    need(type(turns) in (tuple,list) and
         MIN_TURNS<=len(turns)<=MAX_TURNS and
         all(type(t) is dict and type(t.get("prose")) is str for t in turns),
         "WF96_CHAPTER_TURNS_MISSING")
    body="\n\n".join(t["prose"] for t in turns)
    need(100<=len(body)<=16000,
         "WF96_CHAPTER_TOTAL_LENGTH_INVALID")
    return body


def receipts_only(turns,*,mode,outline_sha):
    need(mode in ("split_only","causal_guard") and
         type(outline_sha) is str and len(outline_sha)==64,
         "WF96_CANDIDATE_EVIDENCE_EXPORT_INVALID")
    doc={
        "format":"wf.writing.segmented-candidate-evidence.v96",
        "mode":mode,
        "turn_outline_sha256":outline_sha,
        "turn_count":len(turns),
        "turn_receipts":[t["receipt"] for t in turns],
        "raw_novel_and_model_output_not_embedded":True,
        "canonical_fact_write_count":0,
        "independent_literary_quality_verified":False,
        "all_drafts_pending_author_acceptance":True,
    }
    doc["manifest_sha256"]=digest(canonical(doc))
    return doc
