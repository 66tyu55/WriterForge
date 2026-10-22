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
                re.compile(objects+r"(?:仍|还|依然|早已|已经|就)?"
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
