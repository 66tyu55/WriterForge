"""V122 source-only multi-actor/item ownership audit (NO model, NO canon).

The old preflight incorrectly hard-coded 唐蜃 and assumed the first fruit
was the only relevant prop. This bounded candidate audit instead reads all
actual structured prior item/holder cells and processes paragraphs in order.

Only explicitly named participants and actually narrated, precondition-valid
moves can change the in-memory view. Ambiguous 他/她/那枚果子 and unknown
handoff syntax trigger REVIEW, never an invented transfer, and no "unknown"
claim is certified as a continuity pass. State changes here DO NOT replace
the pinned MIT Novel Studio reducer; the audit is not a new story database.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

from .v116_state_delta import _segments, _present

FORMAT="wf.writing.v122.source-only-multi-item-preflight"
MAX_TEXT=20000
MAX_PRIOR_ITEMS=36
MAX_CAST=10
MAX_CLAUSES=256
MAX_EVENTS=48
MAX_REVIEW=24
MAX_FINDINGS=24
FRUIT_ENDINGS=("髓果","灵果","仙果")
POS=("左手心","右手心","齿间","手中","手里")
NON_NARRATED=("如果","假如","假设","若是","倘若","梦见","梦里",
              "想象","据说","传言","听说","可能","仿佛","似乎")
UNCERTAIN_PRONOUN=re.compile(
    r"(?:他|她|对方)(?:把|将|的(?:左手心|右手心|齿间|手中))"
    r"|(?:那枚|这枚|那颗|这颗)果子")
PLACES="|".join(POS)


class ItemProvenanceError(ValueError):
    pass


def _need(valid,code):
    if not valid:
        raise ItemProvenanceError(code)


def _digest(value):
    if type(value) is str:
        return sha256(value.encode("utf8")).hexdigest()
    return sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
                             separators=(",",":"),allow_nan=False)
                  .encode("utf8")).hexdigest()


def _decode_prior(previous_candidate_state):
    _need(type(previous_candidate_state) is dict and
          len(previous_candidate_state)<=36,
          "WF122_PRIOR_STATE_BOUNDS")
    old={}
    for raw,value in previous_candidate_state.items():
        if type(raw) is not str:
            continue
        try:
            cell=json.loads(raw)
        except (ValueError,TypeError):
            continue
        if (type(cell) is list and len(cell)==5 and
            cell[0]=="item" and cell[2]=="holder" and
            cell[3]=="author_plan" and
            type(cell[1]) is str and 1<=len(cell[1])<=36 and
            type(value) is str and 1<=len(value)<=100):
            old[cell[1]]=value
    _need(len(old)<=MAX_PRIOR_ITEMS,"WF122_TOO_MANY_ITEMS")
    return old


def _known_person(holder):
    if holder.startswith("已消耗"):
        return None
    for pos in POS:
        if holder.endswith(pos):
            return holder[:-len(pos)]
    return None


def _normalize_pos(pos):
    return "手中" if pos=="手里" else pos


def _is_consumed(holder):
    return holder.startswith("已消耗")


def _status_mismatch(item, old, new, *, unspecified_person=False):
    """Conservative aliases retain old V116 red-line codes where applicable."""
    if old==new:
        return None
    fruit=item.endswith(FRUIT_ENDINGS)
    if _is_consumed(old):
        return ("WF116_CONSUMED_FRUIT_RESURRECTED"
                if fruit else "WF122_CONSUMED_ITEM_REAPPEARED")
    if unspecified_person and new.endswith("齿间"):
        return ("WF116_FRUIT_TEETH_WITHOUT_REHANDOFF"
                if fruit else "WF122_ITEM_LOCATION_WITHOUT_TRANSFER")
    if unspecified_person:
        return "WF122_ITEM_LOCATION_WITHOUT_TRANSFER"
    if _is_consumed(new):
        return ("WF116_FRUIT_CONSUMPTION_WITHOUT_HANDOFF"
                if fruit else "WF122_ITEM_CONSUMPTION_SOURCE_UNPROVEN")
    owner_old=_known_person(old)
    owner_new=_known_person(new)
    if owner_old and owner_new and owner_old!=owner_new:
        return ("WF116_FRUIT_TELEPORT_TO_OTHER_ACTOR"
                if fruit else "WF122_ITEM_OWNER_CHANGE_WITHOUT_TRANSFER")
    if (new.endswith("齿间") or
        (unspecified_person and "齿间" in new)):
        return ("WF116_FRUIT_TEETH_WITHOUT_REHANDOFF"
                if fruit else "WF122_ITEM_LOCATION_WITHOUT_TRANSFER")
    return "WF122_ITEM_LOCATION_WITHOUT_TRANSFER"


def _mentions(clause,items):
    """Return item-specific offsets. A generic 果子 needs a unique old fruit."""
    found=[]
    for item in sorted(items,key=lambda x:(-len(x),x)):
        for match in re.finditer(re.escape(item),clause):
            if any(not (match.end()<=a or match.start()>=b)
                   for a,b,_ in found):
                continue
            found.append((match.start(),match.end(),item))
    fruit=[i for i in items if i.endswith(FRUIT_ENDINGS)]
    if "果子" in clause and len(fruit)==1:
        for match in re.finditer("果子",clause):
            found.append((match.start(),match.end(),fruit[0]))
    return sorted(found)


def _first_item(match,mentions):
    """Resolve action's explicit item, or unique old fruit alias."""
    a,b=match.span("object")
    return next((item for start,end,item in mentions
                 if start==a and end==b),None)


def _trace_provenance(prose,old,cast):
    state=dict(old)
    findings=[]
    review=[]
    events=[]
    uncertain_items=set()
    characters=set(cast)
    characters.update(person for person in map(_known_person,old.values())
                      if person)
    character_pattern="|".join(map(re.escape, sorted(
        characters,key=lambda x:(-len(x),x))))
    item_pattern="|".join(map(re.escape, sorted(
        old,key=lambda x:(-len(x),x))))
    fruit=[name for name in old if name.endswith(FRUIT_ENDINGS)]
    alias="|果子" if len(fruit)==1 else ""
    objects=r"(?P<object>(?:"+item_pattern+alias+r"))" if item_pattern else None

    def warn(code,*,hard):
        arr=findings if hard else review
        cap=MAX_FINDINGS if hard else MAX_REVIEW
        if code not in arr and len(arr)<cap:
            arr.append(code)

    def anchor(start,clause,item,op,old_holder,new_holder):
        quote=clause.strip()
        offset=start+len(clause)-len(clause.lstrip())
        # The original must contain this exact unique narrated statement.
        if (not 3<=len(quote)<=150 or prose.count(quote)!=1 or
            not _present(prose,offset,offset+len(quote))):
            warn("WF122_EVENT_SOURCE_ANCHOR_UNPROVEN",hard=False)
            return False
        if len(events)>=MAX_EVENTS:
            warn("WF122_EVENT_BUDGET_EXHAUSTED",hard=False)
            return False
        events.append({"kind":op,"item":item,
                       "before_holder":old_holder,"after_holder":new_holder,
                       "source_start":offset,"source_end":offset+len(quote),
                       "source_quote_sha256":_digest(quote),
                       "candidate_state_only":True})
        return True

    clauses=list(_segments(prose))
    if len(clauses)>MAX_CLAUSES:
        warn("WF122_CLAUSE_BUDGET_EXCEEDED",hard=False)
        # Never certify that later, uninspected text has no continuity defect.
        clauses=clauses[:MAX_CLAUSES]
    if not objects:
        return findings,review,events,state

    giver=r"(?P<giver>(?:"+character_pattern+r"))" if character_pattern else None
    receiver=r"(?P<receiver>(?:"+character_pattern+r"))" if character_pattern else None

    def moves(name_clause,mentions):
        if not giver:
            return []
        moves_here=[]
        # Only clear actions with an old-value check are candidate moves.
        transfer=re.compile(
            giver+r"(?:把|将)(?:那枚|这枚|那颗|这颗|一枚)?"+objects+
            r"从(?P<loc>左手心|右手心|手中|齿间)"
            r"(?:取出|拿起)?(?:递给|交给)"+receiver)
        spit=re.compile(
            giver+r"(?:把|将)(?:那枚|这枚|那颗|这颗|一枚)?"+objects+
            r"从齿间吐到(?P<target>左手心|右手心)")
        take=re.compile(
            giver+r"(?:把|将)(?:那枚|这枚|那颗|这颗|一枚)?"+objects+
            r"从(?P<loc>左手心|右手心)(?:拿起|取出)?送入口中"
            r".{0,15}?(?:吞下|吞服|吃下)")
        bite=re.compile(
            giver+r"(?:把|将)(?:那枚|这枚|那颗|这颗|一枚)?"+objects+
            r"往齿间一咬")
        for kind,rx in (("HANDOFF",transfer),("TEETH_TO_PALM",spit),
                        ("CONSUME",take),("BITE",bite)):
            for m in rx.finditer(name_clause):
                item=_first_item(m,mentions)
                if item is None:
                    continue
                if kind=="HANDOFF":
                    new=m["receiver"]+"手中"
                    expected=m["giver"]+_normalize_pos(m["loc"])
                    if m["giver"]==m["receiver"]:
                        warn("WF122_SELF_HANDOFF_UNRESOLVED",hard=False)
                        continue
                elif kind=="TEETH_TO_PALM":
                    new=m["giver"]+m["target"]
                    expected=m["giver"]+"齿间"
                elif kind=="CONSUME":
                    new="已消耗（"+m["giver"]+"吞服）"
                    expected=m["giver"]+m["loc"]
                else:
                    new=m["giver"]+"齿间"
                    expected=None
                moves_here.append((m.start(),m.end(),item,kind,
                                   expected,new,m["giver"]))
        return sorted(moves_here)

    for start,end,clause,in_speech in clauses:
        if in_speech or not _present(prose,start,end) or \
           any(term in clause for term in NON_NARRATED):
            continue
        mentions=_mentions(clause,state)
        if not mentions and "果子" not in clause:
            continue
        if "果子" in clause and len(fruit)>1 and \
           not any(item.endswith(FRUIT_ENDINGS) for _,_,item in mentions):
            warn("WF122_AMBIGUOUS_FRUIT_ALIAS",hard=False)
            continue
        if UNCERTAIN_PRONOUN.search(clause):
            # A pronoun does not overrule an explicit named acting subject:
            # "沈砚把那枚果子..." is safely resolved with unique fruit.
            if not re.search(
                    r"(?:把|将)(?:那枚|这枚|那颗|这颗)果子",clause) or \
               len(fruit)!=1:
                warn("WF122_PRONOUN_OR_DEMONSTRATIVE_UNRESOLVED",hard=False)
        recognized=moves(clause,mentions)
        completed=[]
        for a,b,item,kind,expected,new,actor in recognized:
            before=state[item]
            if expected is None:
                if _is_consumed(before) or \
                   (_known_person(before) not in (None,actor)):
                    warn("WF122_BITE_PRIOR_HOLDER_CONFLICT",hard=True)
                    continue
            elif before!=expected:
                # A transparent text conflict with a known source checkpoint
                # is a hard precondition failure, not invented handover.
                code=("WF116_FRUIT_CONSUMPTION_WITHOUT_HANDOFF"
                      if kind=="CONSUME" and item.endswith(FRUIT_ENDINGS)
                      else "WF122_HANDOFF_SOURCE_PRECONDITION_FAILED")
                warn(code,hard=True)
                continue
            if anchor(start,clause,item,kind,before,new):
                state[item]=new
                completed.append((a,b,item))
        # A source claim of holder/position needs an explicit name (or a
        # unique item and location without a named character). Never infer
        # a character from a paragraph's earlier sentence.
        people="|".join(map(re.escape,sorted(
            characters,key=lambda x:(-len(x),x))))
        claim_patterns=[]
        if people:
            claim_patterns.extend([
                re.compile(objects+r"(?:仍|还|又|再度|再次|依然|早已|已经|就)?"
                           r"(?:在|落在|留在|握在|攥在|含在)"
                           r"(?P<owner>"+people+r")(?:的)?(?P<pos>"+
                           PLACES+r")"),
                re.compile(r"(?P<owner>"+people+r")(?:的)?(?P<pos>"+
                           PLACES+r")(?:里|中)?(?:还|仍|正|一直|已)?"
                           r"(?:握着|攥着|捏着|托着|含着|咬着|有着)"+
                           r"(?:那枚|这枚|那颗|这颗)?"+objects),
                re.compile(r"(?P<owner>"+people+r")(?:仍|还|正|已)?"
                           r"(?:握着|攥着|捏着|托着|含着|咬着)"+
                           r"(?:那枚|这枚|那颗|这颗)?"+objects),
            ])
        # "果子还在齿间" proves a *location*, but not who holds it.
        claim_patterns.append(re.compile(
            objects+r"(?:仍|还|依然|早已|已经)?(?:在|留在|含在)"
            r"(?P<pos>齿间|左手心|右手心)"))
        claim_patterns.append(re.compile(
            r"(?P<owner>"+people+r")(?P<pos>齿间|左手心|右手心)"
            r"(?:还|仍|正|已)?(?:含着|咬着|握着|托着)"+objects)
            if people else re.compile(r"(?!x)x"))
        for rx in claim_patterns:
            for match in rx.finditer(clause):
                item=_first_item(match,mentions)
                if item is None:
                    continue
                if any(a<=match.start()<b and i==item
                       for a,b,i in completed):
                    continue
                # If the sentence has a potential but unverified transfer,
                # a later ownership claim must not be over-blocked as teleport.
                owner=match.groupdict().get("owner")
                pos=match.groupdict().get("pos")
                if owner:
                    claim=owner+(_normalize_pos(pos) if pos else "手中")
                else:
                    claim=None
                before=state[item]
                if owner is None:
                    if pos and before.endswith(pos):
                        continue
                    if pos:
                        # Item is shown in a different location than recorded.
                        err=_status_mismatch(
                            item,before,"UNKNOWN"+_normalize_pos(pos),
                            unspecified_person=True)
                    else:
                        continue
                else:
                    err=_status_mismatch(item,before,claim)
                    if pos is None and _known_person(before)==owner and \
                       not _is_consumed(before):
                        err=None
                if not err:
                    continue
                if item in uncertain_items or \
                   re.search(r"(?:递给|交给|扔给|送给|给了|夺走|抢走)",clause):
                    warn("WF122_TRANSFER_CLAIM_NEEDS_REVIEW",hard=False)
                else:
                    warn(err,hard=True)
        if any(x in clause for x in ("果子","髓果","灵果","仙果",
                                    "剑穗","法剑","符箓","法宝")) and \
           UNCERTAIN_PRONOUN.search(clause):
            for _,_,item in mentions:
                uncertain_items.add(item)
        # Any unsupported explicit transfer should be marked as such, and
        # suppress later hard claims until a source-anchored handoff is seen.
        if any(x in clause for x in ("递给","交给","扔给","送给",
                                    "给了","夺走","抢走")) and \
           not recognized and mentions:
            for _,_,item in mentions:
                uncertain_items.add(item)
            warn("WF122_TRANSFER_ACTION_NOT_SOURCE_VERIFIED",
                 hard=False)
        # Once one explicit, verified transfer is observed, the item's
        # earlier ambiguous state no longer blocks future direct claims.
        for _,_,item in completed:
            uncertain_items.discard(item)
    return findings,review,events,state


def supplemental_reducer_events(*, prose, audit, earlier_events=()):
    """Convert only proven source actions to the pinned V114 reducer schema.

    Existing native/V116 operations win exact duplicates. Upstream reducer
    still enforces expected-old-value transitions atomically; this function
    can never claim a canonical fact or repair the original paragraph.
    """
    _need(type(audit) is dict and audit.get("format")==FORMAT and
          audit.get("source_prose_sha256")==_digest(prose) and
          type(earlier_events) in (list,tuple) and len(earlier_events)<=30,
          "WF122_REDUCER_ADAPTER_SOURCE_OR_INPUT_INVALID")
    known=set()
    for ev in earlier_events:
        if type(ev) is not dict:continue
        src=ev.get("evidence",{})
        for op in ev.get("ops",[]):
            cell=op.get("cell",{})
            if cell.get("domain")!="item" or \
               cell.get("predicate")!="holder" or \
               cell.get("scope")!="author_plan":
                continue
            known.add((src.get("start"),src.get("end"),
                       cell.get("entityId"),op.get("value")))
    extra=[]
    for event in audit["candidate_source_events"]:
        start,end=event["source_start"],event["source_end"]
        item=event["item"]
        before,after=event["before_holder"],event["after_holder"]
        _need(type(start) is int and type(end) is int and
              0<=start<end<=len(prose) and end-start<=150 and
              type(item) is str and 1<=len(item)<=36 and
              type(before) is str and type(after) is str,
              "WF122_REDUCER_ADAPTER_EVENT_SCHEMA_INVALID")
        quote=prose[start:end]
        _need(_digest(quote)==event["source_quote_sha256"] and
              prose.count(quote)==1 and _present(prose,start,end),
              "WF122_REDUCER_ADAPTER_EVENT_SOURCE_UNPROVEN")
        identity=(start,end,item,after)
        if identity in known or before==after:
            continue
        known.add(identity)
        alias=("果子" if item not in quote and "果子" in quote
               and item.endswith(FRUIT_ENDINGS) else None)
        evidence={"quote":quote,"start":start,"end":end,
                  "narrative":"present"}
        if alias:
            evidence["entity_alias"]=alias
        extra.append({
            "id":f"wf122_e{len(extra)+1:02d}",
            "evidence":evidence,
            "ops":[{
                "type":"set",
                "cell":{"domain":"item","entityId":item,
                        "predicate":"holder","scope":"author_plan"},
                "expected":{"kind":"value","value":before},
                "value":after,
            }],
        })
    _need(len(extra)<=30,"WF122_REDUCER_ADAPTER_EVENT_BUDGET")
    return extra


def audit_item_provenance(*, prose,previous_candidate_state,cast=()):
    _need(type(prose) is str and 0<len(prose)<=MAX_TEXT,
          "WF122_SOURCE_TEXT_BOUNDS")
    _need(type(cast) in (tuple,list) and len(cast)<=MAX_CAST and
          all(type(name) is str and 1<=len(name)<=70 for name in cast)
          and len(set(cast))==len(cast),
          "WF122_CAST_INVALID")
    old=_decode_prior(previous_candidate_state)
    findings,review,events,state=_trace_provenance(prose,old,cast)
    payload={
        "format":FORMAT,
        "source_prose_sha256":_digest(prose),
        "prior_state_sha256":_digest(previous_candidate_state),
        "cast_sha256":_digest(list(cast)),
        "checked_item_count":len(old),
        "hard_findings":findings[:MAX_FINDINGS],
        "review_findings":review[:MAX_REVIEW],
        "candidate_source_events":events[:MAX_EVENTS],
        "remaining_holders_candidate_only":state,
        "source_item_coverage_not_universal":True,
        "pronouns_unknown_until_explicitly_grounded":True,
        "model_justification_never_source_evidence":True,
        "new_model_calls":0,"R2_writes":0,"canon_writes":0,
        "candidate_state_not_promoted_to_reducer":True,
        "original_prose_not_modified":True,
        "contains_raw_prose":False,
    }
    payload["receipt_sha256"]=_digest(payload)
    return payload


# Source-bound physical attachment evidence is a PROJECTION of the existing
# V122/V114 provisional event boundary. It is not a second story memory owner.
# It never writes the Novel Studio reducer's "holder" cell, since attachment
# of a rope end to a post is not possession of the entire rope.
_PHYSICAL_SPLIT=re.compile(r"[，,；;。！？\n]")
_PHYSICAL_DISCOURSE=("只是","然而","但是","不过","但","却","可","而","原来")
_PHYSICAL_TEMPORAL=("随后","后来","接着","然后","过了","片刻后","此后",
                    "第二天","次日","先","再","之后","不久后")
_PHYSICAL_NONFACT=("猜","以为","觉得","听说","据说","可能","似乎","仿佛",
                   "如果","若是","梦见","想象","不确定","未必","不知道",
                   "听见","说过")
_PHYSICAL_BOUND=re.compile(
    r"^(?P<item>[\u3400-\u9fff]{1,12}?)"
    r"(?P<aspect>仍然|依然|一直|尚|仍|还|正|已经|已)?"
    r"(?P<verb>系|绑|拴|栓|挂|锁|扣)(?:在|着|于)"
    r"(?P<site>[\u3400-\u9fff]{1,12})$")
_PHYSICAL_PASSIVE_FREE=re.compile(
    r"^(?P<item>[\u3400-\u9fff]{1,14}?)(?:已经|早已|已)?"
    r"被[\u3400-\u9fff]{1,8}?从"
    r"(?P<site>[\u3400-\u9fff]{1,12}?)"
    r"(?:解下|解开|拆下|卸下|摘下|取下|松开)(?:来|去)?$")
_PHYSICAL_DIRECT_FREE=re.compile(
    r"^(?:[\u3400-\u9fff]{1,8}?(?:把|将))?"
    r"(?P<item>[\u3400-\u9fff]{1,14}?)从"
    r"(?P<site>[\u3400-\u9fff]{1,12}?)"
    r"(?:解下|解开|拆下|卸下|摘下|取下|松开)(?:来|去)?$")
_PHYSICAL_ACTION_BIND=re.compile(
    r"^(?:[\u3400-\u9fff]{1,10}?(?:把|将))?"
    r"(?P<item>[\u3400-\u9fff]{1,14}?)"
    r"(?:系|绑|拴|栓|挂|锁|扣)(?:在|到|于)"
    r"(?P<site>[\u3400-\u9fff]{1,12})$")
_PHYSICAL_COLORS=("红","蓝","黑","白","青","黄","绿","紫","金","银")
_PHYSICAL_NUMBERS=("第一","第二","第三","两根","另一根","左边","右边","左侧","右侧")
_PHYSICAL_PARTS=("自由端","另一端","绳头","锁扣的一侧","末端")
# The container case shares EXACTLY the existing V122/V114 relation receipt,
# not a second memory channel. Narrow forms only: object-in-container and
# directly observed removal/placement; these are NOT ownership statements.
_PHYSICAL_CONTAINED=re.compile(
    r"^(?P<item>[\u3400-\u9fff]{1,14}?)"
    r"(?P<aspect>仍然|依然|一直|尚|仍|还|正|已经|已)?"
    r"(?:在|放在|藏在|留在)"
    r"(?P<site>[\u3400-\u9fff]{1,12}?)"
    r"(?:里面|里|之中|中|内)$")
_PHYSICAL_PASSIVE_TAKE=re.compile(
    r"^(?P<item>[\u3400-\u9fff]{1,14}?)(?:已经|早已|已)?"
    r"被[\u3400-\u9fff]{1,8}?从"
    r"(?P<site>[\u3400-\u9fff]{1,12}?)"
    r"(?:里面|里|之中|中|内)"
    r"(?:取出|拿出|掏出|取走|搬出|移出)(?:来|去)?$")
_PHYSICAL_DIRECT_TAKE=re.compile(
    r"^(?:[\u3400-\u9fff]{1,8}?(?:把|将))?"
    r"(?P<item>[\u3400-\u9fff]{1,14}?)从"
    r"(?P<site>[\u3400-\u9fff]{1,12}?)"
    r"(?:里面|里|之中|中|内)"
    r"(?:取出|拿出|掏出|取走|搬出|移出)(?:来|去)?$")
_PHYSICAL_PLACE=re.compile(
    r"^(?:[\u3400-\u9fff]{1,8}?(?:把|将))?"
    r"(?P<item>[\u3400-\u9fff]{1,14}?)"
    r"(?:放入|放进|装进|收进|藏进|送进)"
    r"(?P<site>[\u3400-\u9fff]{1,12}?)"
    r"(?:里面|里|之中|中|内)?$")
MAX_OPEN_PHYSICAL_RELATIONS=8

def _physical_site_label(value):
    # Retain the original text as evidence. This heuristic is for *possible*
    # contact targets, never an identity assertion or novel-world state cell.
    raw=value
    for suffix in ("上面","上头","之上","顶端","里面","之中","上","头","边","旁","处","里","中","内"):
        if raw.endswith(suffix) and len(raw)>len(suffix):
            return raw[:-len(suffix)]
    return raw

def _physical_identity(a,b, *,site=False):
    """EXACT or POSSIBLE_ALIAS only; different modifiers cannot be conflated."""
    if a==b:
        return "EXACT_LITERAL"
    if any(x in a or x in b for x in _PHYSICAL_NUMBERS):
        return None
    if any(a.startswith(x) and b.startswith(y) and x!=y
           for x in _PHYSICAL_COLORS for y in _PHYSICAL_COLORS):
        return None
    if site:
        x,y=_physical_site_label(a),_physical_site_label(b)
        if x==y:
            return "POSSIBLE_CONTACT_AREA_ALIAS"
        if min(len(x),len(y))>=1 and (x.endswith(y) or y.endswith(x)):
            return "POSSIBLE_CONTACT_AREA_ALIAS"
        return None
    # A knot is part of a rope and "the rope" may refer to another rope:
    # their lexical similarity is REVIEW evidence, never established sameness.
    ends=("结","子","身","段")
    x,y=a,b
    for suffix in ends:
        if x.endswith(suffix) and len(x)>len(suffix):
            x=x[:-len(suffix)]
        if y.endswith(suffix) and len(y)>len(suffix):
            y=y[:-len(suffix)]
    if x==y:
        return "POSSIBLE_PART_OR_REFERENT_ALIAS"
    if len(x)>=1 and len(y)>=1 and (x.endswith(y) or y.endswith(x)):
        return "POSSIBLE_PART_OR_REFERENT_ALIAS"
    return None

def _physical_relation_clause(prose,start,end,clause,spoken):
    """Parse narrowly observed attachment claims; never infer actions."""
    if spoken or not _present(prose,start,end):
        return None
    raw=clause.strip()
    if not 7<=len(raw)<=150:
        return None
    offset=start+len(clause)-len(clause.lstrip())
    # A quote may occur twice in the manuscript. Its SHA *and exact
    # source position* still identify each original occurrence. Dropping
    # all duplicated phrases made a real conflicting relation invisible.
    if prose[offset:offset+len(raw)]!=raw:
        return None
    inner=raw
    for lead in _PHYSICAL_DISCOURSE+_PHYSICAL_TEMPORAL:
        if inner.startswith(lead):
            inner=inner[len(lead):]
            break
    if not inner or any(t in inner for t in _PHYSICAL_NONFACT):
        return None
    # No semantic overclaim when a pronoun, partial end, or explicitly
    # qualified speculation could reverse which object is actually tied.
    status=None
    for kind,rx in (
        ("ATTACHED_STATE",_PHYSICAL_BOUND),
        ("DETACH_ACTION",_PHYSICAL_PASSIVE_FREE),
        ("DETACH_ACTION",_PHYSICAL_DIRECT_FREE),
        ("ATTACH_ACTION",_PHYSICAL_ACTION_BIND),
        ("CONTAINED_STATE",_PHYSICAL_CONTAINED),
        ("REMOVE_ACTION",_PHYSICAL_PASSIVE_TAKE),
        ("REMOVE_ACTION",_PHYSICAL_DIRECT_TAKE),
        ("PLACE_ACTION",_PHYSICAL_PLACE),
    ):
        m=rx.fullmatch(inner)
        if m:
            status,mapping=kind,m.groupdict()
            break
    if status is None:
        return None
    item,site=mapping["item"],mapping["site"]
    if (not 1<=len(item)<=14 or not 1<=len(site)<=12 or
        any(p in item for p in _PHYSICAL_PARTS) or
        any(p in site for p in _PHYSICAL_PARTS) or
        item.startswith(("他","她","它","他们","她们")) or
        item in ("人","他人","某人","有人") or
        "没" in inner or "不曾" in inner or "没有" in inner):
        return None
    return {
        "source_start":offset,"source_end":offset+len(raw),
        "source_quote":raw,"source_quote_sha256":_digest(raw),
        "item_literal":item,"contact_literal":site,
        "relation":(
            "CONTAINED" if status in ("CONTAINED_STATE","PLACE_ACTION") else
            "REMOVED" if status=="REMOVE_ACTION" else
            "ATTACHED" if status.startswith("ATTACH") else "DETACHED"),
        "relation_family":(
            "CONTAINMENT" if status in (
                "CONTAINED_STATE","REMOVE_ACTION","PLACE_ACTION")
            else "ATTACHMENT"),
        "source_form":status,
        "continuing_state_words":bool(mapping.get("aspect") in
                                     ("仍然","依然","一直","尚","仍","还")),
        "narrator_claim_not_semantically_verified":True,
        "candidate_not_item_holder_or_canon":True,
    }

def _candidate_physical_source_question(prose,one,two,*,
                                       adjacent_sentences):
    """One SOURCE-ONLY uncertain state relationship across literary genres.

    Never pronounce contradiction, assign a new owner, infer the invisible
    action, or demand that an author reveal a suspenseful cause. Exactly
    adjacent narrated sentences can supply conflicting SOURCE evidence,
    but they do not prove simultaneity.
    """
    if (one["relation_family"]!=two["relation_family"] or
        one["relation"]==two["relation"]):
        return None
    if (one["source_form"],two["source_form"]) in (
        ("ATTACH_ACTION","DETACH_ACTION"),
        ("PLACE_ACTION","REMOVE_ACTION")):
        return None
    if not (one["continuing_state_words"] or
            two["continuing_state_words"]):
        return None
    between=prose[one["source_end"]:two["source_start"]]
    if adjacent_sentences:
        if (two["sentence_source_index"]!=
                one["sentence_source_index"]+1 or
            re.fullmatch(r"[。！？][ \t]*",between) is None):
            return None
    elif one["sentence_source_index"]!=two["sentence_source_index"]:
        return None
    # Word '后来' at the beginning of a clause is a narratively
    # sufficient explicit ordering; leave it alone. No keyword blacklist
    # for object types or genres.
    if (any(x in between for x in _PHYSICAL_TEMPORAL) or
        two["source_quote"].startswith(_PHYSICAL_TEMPORAL)):
        return None
    item_match=_physical_identity(
        one["item_literal"],two["item_literal"])
    contact_match=_physical_identity(
        one["contact_literal"],two["contact_literal"],site=True)
    if item_match is None or contact_match is None:
        return None
    return {
        "reason_code":"NEEDS_SOURCE_RELATION_REVIEW",
        "first_source_start":one["source_start"],
        "first_source_quote":one["source_quote"],
        "first_source_quote_sha256":one["source_quote_sha256"],
        "second_source_start":two["source_start"],
        "second_source_quote":two["source_quote"],
        "second_source_quote_sha256":two["source_quote_sha256"],
        "item_identity_evidence":item_match,
        "contact_identity_evidence":contact_match,
        "first_item_literal":one["item_literal"],
        "second_item_literal":two["item_literal"],
        "relation_family":one["relation_family"],
        "first_contact_literal":one["contact_literal"],
        "second_contact_literal":two["contact_literal"],
        "unresolved_question":"SAME_REFERENT_AND_CONTACT_STATUS_NOT_PROVEN",
        "unknown_actor_may_remain_unknown":True,
        "literary_ellipsis_not_a_physical_state_proof":True,
        "writer_must_choose_whether_and_where_to_edit":True,
        "adjacent_sentence_not_proven_same_time":adjacent_sentences,
    }

# Portable-document custody is a SOURCE-ONLY subprojection of the EXISTING
# signed V122/V114 relation receipt, not a new item database or literary
# critic. It records a possible missing transition across turns, never
# declares two noun phrases the same physical object or writes a holder cell.
# The recognition vocabulary limits coverage; absence of an alert is NOT
# evidence of a verified transfer chain.
_DOC_CUSTODY_LIMIT=8
_DOC_ACTOR=r"(?P<actor>[\u3400-\u9fff]{2,6})"
_DOC_ITEM=r"(?P<item>[\u3400-\u9fff]{0,6}(?:册子|文书|卷宗|账簿|密函|药箱|钥匙|信封|账册|经卷|令牌))"
_DOC_LEAVE=re.compile(
    _DOC_ACTOR+r"把"+_DOC_ITEM+
    r"(?:揣进|收进|塞进|装进|收入)[^。！？；\n]{0,38}?"
    r"(?:出去|离开|走出)")
_DOC_REHANDLE_MIXED=re.compile(
    _DOC_ACTOR+r"把[^。！？；\n]{0,30}?[，,]与"+
    _DOC_ITEM+r"一并(?:纳入|收进|装进|封入|放进|收入)")
_DOC_REHANDLE_DIRECT=re.compile(
    _DOC_ACTOR+r"(?:把|将)"+_DOC_ITEM+
    r"(?:放进|装进|封进|纳入|收入)")
_DOC_RETURN=re.compile(
    r"(?P<giver>[\u3400-\u9fff]{2,6})"
    r"(?:回来|折返|回到案前|回到屋里)(?:把|将)"
    +_DOC_ITEM+r"(?:交还|还给|递还|交给)"
    r"(?P<receiver>[\u3400-\u9fff]{2,6})")
_DOC_DISTINCT=("另一本","另一册","另外一","第二","第三","副本",
               "抄本","备份","复写","新的一本","两本","两册")
_DOC_NONCURRENT=("回忆","回想","想起","梦见","假如","如果","曾经回想",
                 "那时","旧日","当初那一幕")


def _document_identity_source_scope(before,after):
    if any(word in before or word in after for word in _DOC_DISTINCT):
        return None
    if before==after:
        return "EXACT_DOCUMENT_LITERAL"
    if (min(len(before),len(after))>=2 and
        (before.endswith(after) or after.endswith(before))):
        return "POSSIBLE_DOCUMENT_ALIAS"
    return None


def _bounded_document_custody_projection(prose,previous_relation_receipt):
    """A small, source-locked custody QUESTION, never semantic ownership.

    One original narrated handoff carried away by a named participant may
    conflict with another named participant handling possibly the same
    object later, if a return is not shown. Off-page returns, different
    copies, or narrative flashbacks remain legitimate possibilities.
    """
    inherited=(previous_relation_receipt or {}).get(
        "document_custody_open_sources",[])
    _need(type(inherited) is list and len(inherited)<=_DOC_CUSTODY_LIMIT,
          "WF122_DOCUMENT_CUSTODY_PRIOR_BOUNDS")
    active=[]
    for old in inherited:
        _need(type(old) is dict and all(
            type(old.get(k)) is str and old[k] for k in (
                "item_literal","holder_literal","source_quote",
                "source_quote_sha256","origin_source_sha256")) and
            old["source_quote_sha256"]==_digest(old["source_quote"]) and
            re.fullmatch(r"[0-9a-f]{64}",old["origin_source_sha256"]) is not None,
            "WF122_DOCUMENT_CUSTODY_PRIOR_SOURCE_INVALID")
        active.append(dict(old))
    observations=[]
    fresh=[]
    for begin,end,sentence,spoken in _segments(prose):
        if spoken or any(word in sentence for word in _DOC_NONCURRENT):
            # A retrospective claim cannot silently overwrite current custody.
            continue
        matches=[]
        for kind,rx in (
            ("RETURN",_DOC_RETURN),
            ("CARRY_AWAY",_DOC_LEAVE),
            ("LOCAL_HANDLE",_DOC_REHANDLE_MIXED),
            ("LOCAL_HANDLE",_DOC_REHANDLE_DIRECT),
        ):
            for m in rx.finditer(sentence):
                quote=m.group()
                if any(x in quote for x in _DOC_DISTINCT):
                    continue
                at=begin+m.start()
                if (not 7<=len(quote)<=150 or prose[at:at+len(quote)]!=quote
                    or not _present(prose,at,at+len(quote))):
                    continue
                actor=(m.groupdict().get("actor") or
                       m.groupdict().get("giver"))
                receiver=m.groupdict().get("receiver")
                item=m.group("item")
                matches.append({
                    "kind":kind,"actor_literal":actor,
                    "receiver_literal":receiver,
                    "item_literal":item,
                    "source_start":at,"source_end":at+len(quote),
                    "source_quote":quote,
                    "source_quote_sha256":_digest(quote),
                    "source_sha256":_digest(prose),
                    "source_narration_not_semantic_identity_proof":True,
                })
        matches.sort(key=lambda x:x["source_start"])
        for ev in matches:
            if len(observations)>=_DOC_CUSTODY_LIMIT:
                _need(False,"WF122_DOCUMENT_CUSTODY_SCAN_BUDGET_EXCEEDED")
            observations.append(ev)
            same=[(i,entry,_document_identity_source_scope(
                entry["item_literal"],ev["item_literal"]))
                for i,entry in enumerate(active)]
            same=[x for x in same if x[2] is not None]
            if ev["kind"]=="RETURN":
                # Only an explicitly narrated return by the recorded source
                # holder can transition the candidate to the recipient.
                for i,previous,identity in same:
                    if previous["holder_literal"]!=ev["actor_literal"]:
                        continue
                    active[i]={
                        "item_literal":previous["item_literal"],
                        "holder_literal":ev["receiver_literal"],
                        "source_quote":ev["source_quote"],
                        "source_quote_sha256":ev["source_quote_sha256"],
                        "origin_source_sha256":ev["source_sha256"],
                        "evidence_class":"NARRATED_RETURN_SOURCE_ONLY",
                    }
                    break
            elif ev["kind"]=="CARRY_AWAY":
                candidate={
                    "item_literal":ev["item_literal"],
                    "holder_literal":ev["actor_literal"],
                    "source_quote":ev["source_quote"],
                    "source_quote_sha256":ev["source_quote_sha256"],
                    "origin_source_sha256":ev["source_sha256"],
                    "evidence_class":"NARRATED_CARRY_AWAY_SOURCE_ONLY",
                }
                if same and same[0][1]["holder_literal"]==ev["actor_literal"]:
                    active[same[0][0]]=candidate
                elif not same:
                    _need(len(active)<_DOC_CUSTODY_LIMIT,
                          "WF122_DOCUMENT_CUSTODY_OPEN_SOURCE_LIMIT")
                    active.append(candidate)
                # A different holder may be an alias or offstage handoff;
                # this narrow projection does NOT invent the transition.
            else:
                for i,previous,identity in same:
                    if previous["holder_literal"]==ev["actor_literal"]:
                        break
                    _need(len(fresh)<_DOC_CUSTODY_LIMIT,
                          "WF122_DOCUMENT_CUSTODY_REVIEW_BOUNDS")
                    fresh.append({
                        "earlier_holder_literal":previous["holder_literal"],
                        "later_holder_literal":ev["actor_literal"],
                        "earlier_item_literal":previous["item_literal"],
                        "later_item_literal":ev["item_literal"],
                        "earlier_source_sha256":previous["origin_source_sha256"],
                        "later_source_sha256":ev["source_sha256"],
                        "earlier_source_quote":previous["source_quote"],
                        "later_source_quote":ev["source_quote"],
                        "earlier_source_quote_sha256":
                            previous["source_quote_sha256"],
                        "later_source_quote_sha256":ev["source_quote_sha256"],
                        "later_source_start":ev["source_start"],
                        "item_identity_scope":(
                            "POSSIBLE_DOCUMENT_ALIAS" if identity!=
                                "EXACT_DOCUMENT_LITERAL" else
                            "EXACT_SOURCE_LITERAL_NOT_PROVEN_ONE_OBJECT"),
                        "omitted_return_or_distinct_copy_may_explain":True,
                        "literary_error_proven":False,
                        "real_world_transfer_verified":False,
                        "writer_rewrite_not_performed":True,
                    })
                    break
    _need(len(active)<=_DOC_CUSTODY_LIMIT,
          "WF122_DOCUMENT_CUSTODY_OPEN_LIMIT")
    return active,observations,fresh


def audit_physical_relation_sources(*,prose,previous_relation_receipt=None):
    """Bounded evidence-first relation review within V122; zero model calls.

    Only narrow unresolved SAME-SENTENCE attached/detached OR
    contained/removed source pairs may become review candidates, and
    even then an object/anchor may be an
    alias, a partial end, or a narration choice. Never call it a proven
    contradiction. Explicit sequential acts and different items are allowed.
    """
    _need(type(prose) is str and 0<len(prose)<=MAX_TEXT,
          "WF122_PHYSICAL_SOURCE_BOUNDS")
    if previous_relation_receipt is not None:
        r=previous_relation_receipt
        _need(type(r) is dict and
              r.get("format")=="wf.v122.source-physical-relation-review.v1"
              and r.get("receipt_sha256")==_digest({
                  k:v for k,v in r.items() if k!="receipt_sha256"}) and
              type(r.get("source_sha256")) is str and
              len(r.get("claims",()))<=20 and
              len(r.get("review_pairs",()))<=8 and
              type(r.get("open_relation_reviews",[])) is list and
              len(r.get("open_relation_reviews",[]))<=MAX_OPEN_PHYSICAL_RELATIONS,
              "WF122_PREVIOUS_RELATION_RECEIPT_UNTRUSTED")
    claims=[]
    reviews=[]
    max_scan=512
    fragments_examined=0
    for sentence_id, (sstart,send,sentence,spoken) in enumerate(_segments(prose)):
        _need(sentence_id<max_scan,
              "WF122_PHYSICAL_SCAN_COVERAGE_BUDGET_EXCEEDED")
        if spoken:
            continue
        offset=sstart
        sentence_claims=[]
        for frag in _PHYSICAL_SPLIT.split(sentence):
            if not frag:
                offset+=0
                # Punctuation positions are located by searching the original
                # sentence after each fragment, never by invented text.
                continue
            start=prose.find(frag,offset,send)
            if start<offset:
                break
            end=start+len(frag)
            offset=end
            fragments_examined+=1
            candidate=_physical_relation_clause(prose,start,end,frag,False)
            if candidate is not None:
                _need(len(claims)<20,
                      "WF122_PHYSICAL_SOURCE_CLAIM_BUDGET_EXCEEDED")
                candidate["sentence_source_index"]=sentence_id
                candidate["same_narrated_sentence_not_story_time"]=True
                claims.append(candidate)
                sentence_claims.append(candidate)
        for i,one in enumerate(sentence_claims):
            for two in sentence_claims[i+1:]:
                review=_candidate_physical_source_question(
                    prose,one,two,adjacent_sentences=False)
                if review is None:
                    continue
                _need(len(reviews)<MAX_OPEN_PHYSICAL_RELATIONS,
                      "WF122_PHYSICAL_CONFLICT_SOURCE_BUDGET_EXCEEDED")
                reviews.append(review)
    # Distinct genres show the same source bug: a continuing state in one
    # sentence and its unexplained contrary status in the NEXT sentence.
    # We do not equate different paragraphs, dialogue or a visible
    # intervening action/time lapse with an unambiguous same-time event.
    for one,two in zip(claims,claims[1:]):
        review=_candidate_physical_source_question(
            prose,one,two,adjacent_sentences=True)
        if review is None:
            continue
        _need(len(reviews)<MAX_OPEN_PHYSICAL_RELATIONS,
              "WF122_PHYSICAL_CONFLICT_SOURCE_BUDGET_EXCEEDED")
        reviews.append(review)
    # Provenance debt is carried INSIDE the existing signed V114 receipt
    # through QUIET chapters. Otherwise a 3-chapter story would lose the
    # original question as soon as a chapter did not mention the object.
    # Never silently truncate or auto-settle an old unresolved claim.
    old_open=[]
    if previous_relation_receipt is not None:
        older=previous_relation_receipt.get("open_relation_reviews")
        if older is None:  # compatible with old (pre-0.W) V122 receipts
            older=[{**p,"origin_source_sha256":
                    previous_relation_receipt["source_sha256"]}
                   for p in previous_relation_receipt["review_pairs"]]
        for p in older:
            _need(type(p) is dict and type(p.get("origin_source_sha256")) is str
                  and re.fullmatch(r"[0-9a-f]{64}",p["origin_source_sha256"])
                  and all(type(p.get(k)) is str for k in (
                      "first_source_quote","second_source_quote",
                      "first_source_quote_sha256",
                      "second_source_quote_sha256",
                      "first_item_literal","first_contact_literal"))
                  and all(_digest(p[k+"_source_quote"])==
                          p[k+"_source_quote_sha256"]
                          for k in ("first","second")),
                  "WF122_OLD_OPEN_RELATION_CITATION_NOT_VALID")
            old_open.append(p)
    open_debts=list(old_open)
    seen={(p["origin_source_sha256"],
           p["first_source_quote_sha256"],p["second_source_quote_sha256"])
          for p in open_debts}
    for p in reviews:
        key=(_digest(prose),p["first_source_quote_sha256"],
             p["second_source_quote_sha256"])
        if key not in seen:
            open_debts.append({**p,"origin_source_sha256":_digest(prose)})
            seen.add(key)
    # The existing single-V114-candidate budget wins over silent evidence
    # eviction. Overflow is a SOURCE HOLD, not a green continuity result.
    _need(len(open_debts)<=MAX_OPEN_PHYSICAL_RELATIONS,
          "WF122_OPEN_RELATION_DEBT_BUDGET_EXCEEDED")
    old_unresolved=len(old_open)
    source_dependents=[]
    if old_unresolved:
        # An unresolved older physical relation cannot become the necessary
        # premise of a new unqualified statement. Unrelated story events
        # remain free to proceed; do NOT block a whole book on old questions.
        for now in claims:
            if (now["source_form"] not in (
                    "ATTACHED_STATE","DETACH_ACTION",
                    "CONTAINED_STATE","REMOVE_ACTION")
                or len(source_dependents)>=8):
                continue
            for former in old_open:
                if (former.get("relation_family") or "ATTACHMENT")!=now["relation_family"]:
                    continue
                prior_item=former.get("first_item_literal")
                prior_site=former.get("first_contact_literal")
                if (type(prior_item) is not str or type(prior_site) is not str):
                    continue  # old signed reports need not contain new fields
                if (_physical_identity(now["item_literal"],prior_item) and
                    _physical_identity(now["contact_literal"],prior_site,site=True)):
                    source_dependents.append({
                        "reason_code":"PRIOR_SOURCE_RELATION_CLAIM_NEEDS_REVIEW",
                        "current_source_quote":now["source_quote"],
                        "current_source_start":now["source_start"],
                        "current_source_quote_sha256":now["source_quote_sha256"],
                        "prior_source_quote":former["first_source_quote"],
                        "prior_source_quote_sha256":former["first_source_quote_sha256"],
                        "prior_relation_source_sha256":(
                            former["origin_source_sha256"]),
                        "prior_relation_claim_not_a_confirmed_world_fact":True,
                        "writer_can_continue_unrelated_scenes":True,
                    })
                    break
    document_sources,document_observations,document_reviews=(
        _bounded_document_custody_projection(
            prose,previous_relation_receipt))
    payload={
        "format":"wf.v122.source-physical-relation-review.v1",
        "source_sha256":_digest(prose),
        "previous_source_sha256":(
            previous_relation_receipt["source_sha256"]
            if previous_relation_receipt is not None else None),
        "claims":claims,
        "review_pairs":reviews,
        # No second ledger: bounded source projection INSIDE the existing
        # signed V122/V114 candidate relation receipt only.
        "document_custody_open_sources":document_sources,
        "document_custody_source_observations":document_observations,
        "document_custody_current_review_pairs":document_reviews,
        "document_custody_current_needs_review":bool(document_reviews),
        "document_custody_authoritative_holder_written":False,
        "document_custody_literary_error_verified":False,
        "open_relation_reviews":open_debts,
        "open_relations_forwarded_from_signed_prior":old_unresolved,
        "open_relation_debts_are_source_only_not_state_cells":True,
        "open_relation_debt_budget":MAX_OPEN_PHYSICAL_RELATIONS,
        "dependent_on_unresolved_previous_relation":source_dependents,
        "current_source_needs_review":bool(reviews),
        "previous_source_unresolved_review_count":old_unresolved,
        "previous_source_uncertainty_cannot_become_new_fact":True,
        "review_status":("NEEDS_SOURCE_RELATION_REVIEW" if reviews else
                         "NO_SAME_SENTENCE_RELATION_CONFLICT_DETECTED"),
        "parsed_fragments":fragments_examined,
        "source_coverage_is_partial_not_universal":True,
        "identified_referents_are_hypotheses_not_state_cells":True,
        "derived_from_existing_v122_source_without_new_memory_owner":True,
        "actor_unknown_is_not_literary_error":True,
        "model_calls":0,"R2_writes":0,"canon_writes":0,
    }
    payload["receipt_sha256"]=_digest(payload)
    return payload

def physical_relation_issue_keys(source_audit):
    """Bounded MULTISET of particular unresolved source relationships.

    Comparing a code such as NEEDS_SOURCE_RELATION_REVIEW alone is unsound:
    one erroneous object can be replaced by a DIFFERENT erroneous object
    without changing the list of issue codes. Relation identity is anchored
    to the literal items/contact locations and family; it is NOT a literary
    grade or a claim that these referents truly match.
    """
    _need(type(source_audit) is dict and
          source_audit.get("format")==
              "wf.v122.source-physical-relation-review.v1" and
          source_audit.get("receipt_sha256")==_digest({
              k:v for k,v in source_audit.items()
              if k!="receipt_sha256"}),
          "WF122_PHYSICAL_ISSUE_SOURCE_RECEIPT_NOT_VERIFIED")
    pairs=source_audit.get("review_pairs")
    _need(type(pairs) is list and len(pairs)<=MAX_OPEN_PHYSICAL_RELATIONS,
          "WF122_PHYSICAL_ISSUE_LIST_BOUNDS")
    keys=[]
    for p in pairs:
        _need(type(p) is dict and all(
            type(p.get(field)) is str and p[field] for field in (
                "first_item_literal","second_item_literal",
                "first_contact_literal","second_contact_literal",
                "item_identity_evidence","contact_identity_evidence",
                "relation_family")),
            "WF122_PHYSICAL_ISSUE_IDENTITY_NOT_SOURCE_BACKED")
        identity={
            "family":p["relation_family"],
            "item_literals":[p["first_item_literal"],
                             p["second_item_literal"]],
            "contact_literals":[p["first_contact_literal"],
                                p["second_contact_literal"]],
            "item_identity_scope":p["item_identity_evidence"],
            "contact_identity_scope":p["contact_identity_evidence"],
        }
        # Never turn equal numeric issue codes into equal source events.
        keys.append(_digest(identity))
    return sorted(keys)
