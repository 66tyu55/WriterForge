"""V116: source-only temporal proposals and next-turn preflight.

Deterministic *narrow* Chinese evidence probes. These are candidate changes,
NOT a claim to understand arbitrary prose. No inference API, memory database,
automatic revision, canon writes or historical prose alteration.

The real semantic/expected-old-value decision belongs to the PINNED Novel
Studio MIT reducer, invoked by v114_external_story_state.py.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

from .v115_dynamic_entity_candidates import discover_candidates

MAX_PROSE = 20000
MAX_EVENTS = 16
MAX_ISSUES = 24
MAX_CAST = 10
BAD_NARRATIVE = ("梦里","梦见","做梦","想象","假如","若是","假若","听说","传言","据说")
CLAUSE = re.compile(r"[^。！？\n]*[。！？\n]|[^。！？\n]+$")
ITEM_SUFFIXES = ("髓果","灵果","仙果")
POSITION_VERBS = ("吐到","递给","交给","移入","收进","装进","放进","放到","吞下","吃掉")
ARM_ACTIONS = ("挥剑","持剑","拔剑","挥刀","出拳","抓住","攀上","攀爬","单手提起")
RECOVERY = ("恢复","痊愈","治好","复原","愈合","重新有力")
RECOVERY_CAUSE = ("丹药","疗伤","治愈","灵气","药液","医师","法术","重接经脉")
FMT = "wf.writing.sealed-temporal-deltas.v116"


def _sha(s):
    return sha256(s.encode("utf8")).hexdigest()


def _cell(domain, entity, predicate):
    return json.dumps([domain,entity,predicate,"author_plan",None],
                      ensure_ascii=False,separators=(",",":"))


def _prior(state, domain, entity, predicate):
    return state.get(_cell(domain,entity,predicate))


def _segments(prose):
    """Character offsets with nested Chinese dialogue punctuation respected.

    Sentence-final stops *inside* “speech” cannot cut off the closing quote,
    otherwise the following narrator sentence falsely inherits dialogue.
    A segment containing direct quotation is always non-event evidence.
    """
    start=0
    depth=0
    for index,ch in enumerate(prose):
        was_quoted=depth>0
        if ch in ("“","「"):
            depth+=1
        elif ch in ("”","」"):
            depth=max(0,depth-1)
        boundary=(depth==0 and (ch in "。！？\n" or
                  (ch in ("”","」") and was_quoted)))
        if boundary:
            fragment=prose[start:index+1]
            spoken=any(mark in fragment for mark in ("“","”","「","」"))
            yield start,index+1,fragment,spoken
            start=index+1
    if start<len(prose):
        fragment=prose[start:]
        spoken=(depth>0 or any(
            mark in fragment for mark in ("“","”","「","」")))
        yield start,len(prose),fragment,spoken


def _present(prose, start, end):
    if any(x in prose[start:end] for x in BAD_NARRATIVE):
        return False
    prefix=prose[:start]
    if prefix.count("“") > prefix.count("”"):
        return False
    frag=prose[start:end]
    # Even a dialogue line with a narrator speech-tag is not a source
    # assertion of the quoted action. No quoted action event.
    return not any(mark in frag for mark in ("“","”","「","」"))


def _actor(prose, start, cast, *, limit=220):
    """Prefer the current narrated sentence's explicit subject.

    The nearest name in PREVIOUS context can be an adversary ("唐蜃收诀了")
    while the actual next sentence opens "沈砚左手一撑...右臂...".
    In that case global nearest-name attribution causes invented injuries.
    Remaining pronoun cases are still ONLY hypotheses, never canonical.
    """
    leading=prose[start:start+25].lstrip()
    explicit=[name for name in cast if leading.startswith(name)]
    if len(explicit)==1:
        return explicit[0]
    choices=[]
    for name in cast:
        pos=prose.rfind(name,max(0,start-limit),start+1)
        if pos>=0 and _present(prose,pos,pos+len(name)):
            choices.append((pos,name))
    return max(choices)[1] if choices else None



def source_only_character_place_mentions(prose,*,cast=()):
    """V116 source-only timeline of EXPLICIT name + motion/place substrings.

    Unlike V114's guarded item/arm reducers, this is merely a literal
    read-only index for the SAME writing AI's later decision. Do not infer
    missing movement, reconcile locations, label an error, make a story
    fact, trigger an edit, or add another memory owner. Under-extraction
    is acceptable; a speculative / quoted movement must not become truth.
    """
    if (type(prose) is not str or not 1<=len(prose)<=MAX_PROSE or
        type(cast) is not tuple or not 1<=len(cast)<=MAX_CAST or
        any(type(name) is not str or not 1<=len(name)<=20
            for name in cast) or len(set(cast))!=len(cast)):
        raise ValueError("WF116_PLACE_SOURCE_INPUT_INVALID")
    results=[]
    verbs=(
        "坐进","坐在","蹲在","站在","留在","回到","走到",
        "跑到","移到","进入","跨上","登上","上了",
        "走进","走出",
    )
    for offset,end,fragment,spoken in _segments(prose):
        if spoken or any(flag in fragment for flag in BAD_NARRATIVE):
            continue
        for actor in cast:
            pattern=(
                rf"(?P<actor>{re.escape(actor)})"
                r"(?P<lead>[^。！？；，“”\n]{0,10}?)"
                r"(?P<verb>"+ "|".join(map(re.escape,verbs)) +r")"
                r"(?P<place>[\u3400-\u9fff]{1,6})(?=[，。！？；“”\n]|$)"
            )
            for match in re.finditer(pattern,fragment):
                lead=match.group("lead")
                # Negated/mixed-agent descriptions may be a guess, not an
                # observed move. Fail closed rather than assert a position.
                if (any(x in lead for x in ("不","没","未","若","想","梦")) or
                    any(name!=actor and name in lead for name in cast)):
                    continue
                start=offset+match.start()
                stop=offset+match.end()
                snippet=prose[start:stop]
                if snippet!=match.group(0):
                    raise ValueError("WF116_PLACE_SOURCE_SPAN_MISMATCH")
                results.append({
                    "actor":actor,
                    "start":start,"end":stop,
                    "source_quote":snippet,
                    "literal_verb":match.group("verb"),
                    "literal_place_phrase":match.group("place"),
                    "source_assertion_status":"LITERAL_MENTION_NOT_VERIFIED_FACT",
                })
    results.sort(key=lambda x:(x["start"],x["end"],x["actor"]))
    if len(results)>30:
        raise ValueError("WF116_PLACE_SOURCE_TOO_MANY_MENTIONS")
    payload={
        "format":"wf.writing.source-only-place-mentions.v116",
        "source_sha256":_sha(prose),
        "source_character_count":len(prose),
        "entries":results,
        "source_mentions_are_not_reducer_state":True,
        "unmatched_locations_unknown":True,
        "spatial_consistency_judged_by_model_not_host":True,
        "literary_error_detected_by_software":False,
        "automatically_request_revision":False,
        "model_calls":0,"canon_writes":0,
    }
    payload["receipt_sha256"]=sha256(json.dumps(
        payload,ensure_ascii=False,sort_keys=True,
        separators=(",",":")).encode("utf8")).hexdigest()
    return payload



def _fruit_name(report, prior_state, prose):
    found={r["term"] for r in report["mentions"] if
           r["kind"]=="resource" and
           r["term"].endswith(ITEM_SUFFIXES)}
    # Forward-scene fruit aliases may resolve only against ONE original
    # reducer cell from the PREVIOUS receipt, never a guessed character.
    prior=set()
    for key in prior_state:
        try: cell=json.loads(key)
        except (ValueError,TypeError):continue
        if (type(cell) is list and len(cell)==5 and cell[0]=="item" and
            cell[2]=="holder" and cell[3]=="author_plan" and
            type(cell[1]) is str and cell[1].endswith(ITEM_SUFFIXES)):
            prior.add(cell[1])
    if len(found)>1:return None
    if found:
        named=next(iter(found))
        # An explicitly named second fruit cannot steal a prior alias.
        return named
    if "果子" in prose and len(prior)==1:
        return next(iter(prior))
    return None


def extract_state_events(prose, *, cast=(), prior_state=None):
    if type(prose) is not str or not 0<len(prose)<=MAX_PROSE:
        raise ValueError("WF116_SOURCE_BOUNDS")
    if type(cast) not in (tuple,list) or len(cast)>MAX_CAST or any(
        type(x) is not str or not 1<=len(x)<=20 for x in cast):
        raise ValueError("WF116_CAST_BOUNDS")
    old=prior_state or {}
    if type(old) is not dict or len(old)>36:
        raise ValueError("WF116_PRIOR_STATE_BOUNDS")
    candidates=discover_candidates(prose)
    fruit=_fruit_name(candidates,old,prose)
    events=[]
    unresolved=[]
    working=dict(old)
    def issue(code,span=None):
        if len(unresolved)<MAX_ISSUES:
            unresolved.append({"code":code,"source_span":span})
    def put(quote, start, *, domain, entity, predicate, value, alias=None):
        end=start+len(quote)
        if (not 3<=len(quote)<=150 or prose[start:end]!=quote or
            prose.count(quote)!=1 or not _present(prose,start,end)):
            issue("WF116_ANCHOR_OR_NARRATIVE_UNRESOLVED",[start,end]);return
        if len(events)>=MAX_EVENTS:
            issue("WF116_EVENT_BUDGET_EXHAUSTED",[start,end]);return
        key=_cell(domain,entity,predicate)
        prior=working.get(key)
        if prior==value:return
        ev={
            "id":f"wf116_e{len(events)+1:02d}",
            "evidence":{"quote":quote,"start":start,"end":end,
                        "narrative":"present",
                        **({"entity_alias":alias} if alias else {})},
            "ops":[{"type":"set",
                    "cell":{"domain":domain,"entityId":entity,
                            "predicate":predicate,"scope":"author_plan"},
                    "expected":({"kind":"missing"} if key not in working else
                                {"kind":"value","value":prior}),
                    "value":value}],
        }
        events.append(ev)
        working[key]=value
    clauses=list(_segments(prose))
    for begin,end,clause,in_dialogue in clauses:
        if in_dialogue or not clause.strip():continue
        # Extract only a *narrated* hold, and only when one previously named
        # fruit permits unambiguous binding of the later word "果子".
        if fruit:
            aliases=(fruit,"果子")
            alias_regex="(?:"+ "|".join(map(re.escape,aliases)) +")"
            for m in re.finditer(
                r"把(?:那枚|这枚|一枚|那颗|这颗)?("+alias_regex+
                r")往齿间一咬",clause):
                start=begin+m.start()
                actor=_actor(prose,start,cast)
                if not actor:
                    issue("WF116_FRUIT_HOLDER_ACTOR_UNKNOWN",[start,begin+m.end()])
                    continue
                # Actor must be named in this clause, not guessed from a
                # preceding line of dialogue or a long-range subject.
                if actor not in clause[:m.end()]:
                    issue("WF116_FRUIT_HOLDER_PRONOUN_UNRESOLVED",[start,begin+m.end()])
                    continue
                alias=m.group(1)
                if alias!=fruit and prose.find(fruit)>=start:
                    issue("WF116_ALIAS_NOT_PREVIOUSLY_NAMED",[start,begin+m.end()])
                    continue
                put(clause.strip(),begin+len(clause)-len(clause.lstrip()),
                    domain="item",entity=fruit,predicate="holder",
                    value=actor+"齿间",alias=alias if alias!=fruit else None)
            for m in re.finditer(
                r"把(?:那枚|这枚)?("+alias_regex+
                r")从齿间吐到(左手心|右手心|掌心)",clause):
                start=begin+m.start()
                actor=_actor(prose,start,cast)
                if not actor or actor not in clause[:m.end()]:
                    issue("WF116_FRUIT_TRANSFER_ACTOR_UNKNOWN",[start,begin+m.end()])
                    continue
                alias=m.group(1)
                if alias!=fruit and prose.find(fruit)>=start:
                    issue("WF116_ALIAS_NOT_PREVIOUSLY_NAMED",[start,begin+m.end()])
                    continue
                key=_cell("item",fruit,"holder")
                expected=working.get(key)
                if expected!=actor+"齿间":
                    issue("WF116_MISSING_TEETH_TO_PALM_PRECONDITION",
                          [start,begin+m.end()])
                    continue
                pos=m.group(2)
                if pos=="掌心":pos="掌心(左右未明)"
                put(clause.strip(),begin+len(clause)-len(clause.lstrip()),
                    domain="item",entity=fruit,predicate="holder",
                    value=actor+pos,alias=alias if alias!=fruit else None)
            # A later real paragraph may explicitly hand over the item.
            # No named recipient, no known source palm, no event.
            recipients="|".join(map(re.escape,cast))
            for m in re.finditer(
                r"把(?:那枚|这枚)?("+alias_regex+
                r")从(左手心|右手心)(?:取出|拿起)?(?:递给|交给)("+recipients+r")",
                clause):
                actor=_actor(prose,begin+m.start(),cast)
                recipient=m.group(3)
                if not actor or actor not in clause[:m.end()] or actor==recipient:
                    issue("WF116_UNPROVEN_HANDOFF_ACTOR",[begin+m.start(),begin+m.end()])
                    continue
                oldholder=actor+m.group(2)
                if working.get(_cell("item",fruit,"holder"))!=oldholder:
                    issue("WF116_UNPROVEN_HANDOFF_SOURCE",[begin+m.start(),begin+m.end()])
                    continue
                put(clause.strip(),begin+len(clause)-len(clause.lstrip()),
                    domain="item",entity=fruit,predicate="holder",
                    value=recipient+"手中",
                    alias=m.group(1) if m.group(1)!=fruit else None)
            # Consuming a named fruit requires explicit intake from its
            # known location, not "咬着" or an inferred surge of mana.
            for m in re.finditer(
                r"把(?:那枚|这枚)?("+alias_regex+
                r")从(左手心|右手心)(?:拿起|取出)?送入口中"
                r".{0,15}(?:吞下|吞服|吃下)",clause):
                actor=_actor(prose,begin+m.start(),cast)
                if (not actor or actor not in clause[:m.end()] or
                    working.get(_cell("item",fruit,"holder"))!=actor+m.group(2)):
                    issue("WF116_UNPROVEN_FRUIT_CONSUMPTION",[begin+m.start(),begin+m.end()])
                    continue
                quote=clause.strip()
                offset=begin+len(clause)-len(clause.lstrip())
                alias=m.group(1) if m.group(1)!=fruit else None
                put(quote,offset,domain="item",entity=fruit,
                    predicate="holder",value="已消耗（"+actor+"吞服）",alias=alias)
                put(quote,offset,domain="item",entity=fruit,
                    predicate="consumption",value="明确吞服",alias=alias)
        # A source-narrated arm incapacity, not an adversary's "废了" speech.
        if ("右手" in clause and
            "锁脉诀" in clause and
            any(x in clause for x in ("发麻","不听使唤"))):
            actor=_actor(prose,begin,cast)
            if actor:
                put(clause.strip(),begin+len(clause)-len(clause.lstrip()),
                    domain="character",entity=actor,predicate="右臂可用性",
                    value="受限")
        # The actual V114B first disability spans TWO adjacent source
        # sentences; both must be contiguous and explicitly describe cause.
        if "灵力从肘弯往下被截断" in clause and "手指头瞬间不听使唤" in clause:
            prev=next(((b,e,s) for b,e,s,_ in clauses if e==begin),None)
            if prev and "右手" in prev[2] and "锁脉诀" in prev[2]:
                actor=_actor(prose,prev[0],cast)
                quote=prose[prev[0]:end].strip()
                if actor:
                    put(quote,prev[0],domain="character",entity=actor,
                        predicate="右臂可用性",value="受限")
                else:issue("WF116_ARM_SUBJECT_UNRESOLVED",[prev[0],end])
        if ("丹火" in clause and "右前臂" in clause and
            any(x in clause for x in ("舔上","烧到","灼到","灼伤"))):
            actor=_actor(prose,begin,cast)
            if actor:
                put(clause.strip(),begin+len(clause)-len(clause.lstrip()),
                    domain="character",entity=actor,predicate="右臂伤情",
                    value="丹火灼及右前臂")
            else:issue("WF116_BURN_SUBJECT_UNRESOLVED",[begin,end])
        if "右臂" in clause and (
            "甩在身后" in clause or "垂着" in clause or "抬不起来" in clause):
            actor=_actor(prose,begin,cast)
            if actor:
                put(clause.strip(),begin+len(clause)-len(clause.lstrip()),
                    domain="character",entity=actor,predicate="右臂可用性",
                    value="受限")
            else:issue("WF116_ARM_DISABILITY_SUBJECT_UNRESOLVED",[begin,end])
    events.sort(key=lambda e:e["evidence"]["start"])
    for i,e in enumerate(events,1):e["id"]=f"wf116_e{i:02d}"
    return {
        "format":FMT,"source_sha256":_sha(prose),
        "named_entity_candidates":candidates,
        "source_anchored_events":events[:MAX_EVENTS],
        "unresolved":unresolved[:MAX_ISSUES],
        "no_unanchored_fruit_consumption":True,
        "no_permanent_arm_diagnosis":True,
        "canonical_fact_writes":0,"model_calls":0,
        "semantic_truth_independently_proven":False,
    }



# V121 actor-bound physical continuity. A mere mention of "右手挥剑"
# cannot implicate every injured person from the previous checkpoint.
_ARM_USE=re.compile(r"右(?:手|臂)(?P<between>.{0,10}?)(?P<verb>"+
                    "|".join(map(re.escape,ARM_ACTIONS))+r")")
_ARM_PREDICATE_NEGATION=("没有","并未","不曾","未曾","无力","无法",
                         "不能","没能","未能","不敢","欲","想",
                         "试图","尝试","打算","准备","假装","刚要")
_ARM_RECOVERY=re.compile(r"右(?:手|臂).{0,18}(?:恢复|痊愈|治好|复原|愈合|重新有力)")
_ARM_PRIOR_CONDITION=re.compile(r"右(?:手|臂).{0,18}(?:受伤|受限|负伤|麻痹|不听使唤|抬不起来)")


def _limited_arm_actors(prior):
    """Interpret structured reducer cells, not substring-matched JSON keys."""
    names=set()
    for raw,value in prior.items():
        try:
            cell=json.loads(raw)
        except (TypeError,ValueError):
            continue
        if (type(cell) is list and len(cell)==5 and
            cell[0]=="character" and type(cell[1]) is str and
            1<=len(cell[1])<=70 and cell[2]=="右臂可用性" and
            cell[3]=="author_plan" and value=="受限"):
            names.add(cell[1])
    return names


def _direct_arm_actor(clause, match, limited, cast):
    """Return an explicitly bound subject, other subject, or unknown.

    Explicit names must be immediately linked to the right arm or be the
    opening subject of an already-injured-arm condition leading into action.
    Never resolve 他/她 by proximity or carry the previous sentence's actor.
    """
    pre=clause[:match.start()]
    # Directly named actor next to the limb (or after a comma).
    names=set(cast)|set(limited)
    positions=[]
    for name in names:
        if re.search(re.escape(name)+r"(?:的)?$",pre):
            positions.append(name)
    if positions:
        # A distinct longer name wins if character names overlap. The
        # preceding words may be "看着唐蜃"; the immediate arm subject
        # is 唐蜃, not the earlier narrator subject 沈砚.
        longest=max(len(n) for n in positions)
        choices=[n for n in positions if len(n)==longest]
        return (choices[0],"DIRECT") if len(choices)==1 else (
            None,"AMBIGUOUS_DIRECT")
    # The arm-action clause omits a subject only after an explicit opening
    # narrator subject and a separate previous arm limitation in this clause.
    for who in limited:
        lead=re.fullmatch(
            r"\s*"+re.escape(who)+r"(?P<condition>右(?:手|臂).{0,30}?)[，,]\s*",
            pre)
        if lead and _ARM_PRIOR_CONDITION.search(lead["condition"]):
            if not any(other!=who and other in pre for other in names):
                return who,"SAME_CLAUSE_INJURY_SUBJECT"
    return None,"UNKNOWN_ACTOR"


def _arm_recovery_before(source, before_offset, actor, cast):
    """Return causal claim class only for this actor, before the action."""
    windows=[]
    for start,end,fragment,spoken in _segments(source):
        if start>=before_offset:
            break
        if spoken or not _present(source,start,end):
            continue
        candidate=fragment[:max(0,before_offset-start)]
        if not candidate:
            continue
        # A recovered enemy in the same sentence does NOT heal our actor.
        if _ARM_RECOVERY.search(candidate):
            heal=_ARM_RECOVERY.search(candidate)
            names=set(cast)|{actor}
            subject=_direct_arm_actor(candidate,heal,{actor},names)[0]
            if subject!=actor:
                continue
            windows.append((start,end,candidate,heal))
    if not windows:
        return "NO_SOURCE_RECOVERY"
    start,end,clause,healing=windows[-1]
    before=source[max(0,start-120):start]+clause[:healing.end()]
    # A source/medicine in a different person's clause is insufficient.
    if any(x in clause[:healing.end()] for x in RECOVERY_CAUSE):
        return "HEALING_SOURCE_REQUIRES_REVIEW"
    # Adjacent earlier clause must name the SAME actor for a source.
    prev=source[max(0,start-120):start]
    tail=prev.split("。")[-1]
    if actor in tail and any(x in tail for x in RECOVERY_CAUSE):
        return "HEALING_SOURCE_REQUIRES_REVIEW"
    return "HEALING_WITHOUT_SOURCE"


def _check_arm_action_source(prose, prior, cast=()):
    limited=_limited_arm_actors(prior)
    if not limited:
        return [],[]
    hard=[]
    uncertain=[]
    for start,end,clause,spoken in _segments(prose):
        if spoken or not _present(prose,start,end):
            continue
        for match in _ARM_USE.finditer(clause):
            between=match["between"]
            if any(x in between for x in _ARM_PREDICATE_NEGATION):
                continue
            actor,binding=_direct_arm_actor(clause,match,limited,cast)
            if actor not in limited:
                if actor is None:
                    # The arm use may belong to an injured actor, but the
                    # text has not actually grounded who acted.
                    uncertain.append("WF121_RIGHT_ARM_ACTION_ACTOR_UNRESOLVED")
                continue
            recovery=_arm_recovery_before(prose,start+match.start(),actor,cast)
            if recovery=="NO_SOURCE_RECOVERY":
                hard.append("WF116_ARM_USED_WITHOUT_RECOVERY")
            elif recovery=="HEALING_WITHOUT_SOURCE":
                hard.append("WF116_ARM_RECOVERY_WITHOUT_SOURCE")
            else:
                uncertain.append("WF116_ARM_RECOVERY_CLAIM_NEEDS_REVIEW")
    return list(dict.fromkeys(hard)),list(dict.fromkeys(uncertain))


def preflight_next_prose(next_prose, *, previous_candidate_state,
                         previous_risks=(), cast=(),
                         previous_relation_receipt=None):
    """Reject demonstrable state jumps *before accepting* a generated turn.

    Called AFTER one model response, BEFORE accepted_turns.append. Never
    triggers a retry, rewrites prose, or promotes a candidate to truth.
    """
    if type(next_prose) is not str or len(next_prose)>MAX_PROSE:
        raise ValueError("WF116_NEXT_PROSE_BOUNDS")
    if type(previous_candidate_state) is not dict or len(previous_candidate_state)>36:
        raise ValueError("WF116_PREVIOUS_STATE_BOUNDS")
    if type(cast) not in (tuple,list) or len(cast)>MAX_CAST or any(
            type(x) is not str or not 1<=len(x)<=70 for x in cast):
        raise ValueError("WF121_SOURCE_CAST_INVALID")
    findings,review_findings=_check_arm_action_source(
        next_prose,previous_candidate_state,cast)
    # V122: all structured item/holder cells, not an arbitrary first fruit.
    # Avoid a circular import: V122 reuses V116's source segmentation but
    # is invoked only when this preflight is called after module load.
    from .v122_item_provenance import audit_item_provenance
    item_audit=audit_item_provenance(
        prose=next_prose,
        previous_candidate_state=previous_candidate_state,
        cast=cast)
    findings.extend(item_audit["hard_findings"])
    review_findings.extend(item_audit["review_findings"])
    # V122's physical attachment evidence is only a bounded, source-SHA
    # review projection. A rope tied to a post is not a holder transfer.
    from .v122_item_provenance import audit_physical_relation_sources
    relations=audit_physical_relation_sources(
        prose=next_prose,
        previous_relation_receipt=previous_relation_receipt)
    if relations["current_source_needs_review"]:
        review_findings.insert(0,"NEEDS_SOURCE_RELATION_REVIEW")
    if relations["previous_source_unresolved_review_count"]:
        review_findings.insert(0,"PRIOR_SOURCE_RELATION_STILL_UNRESOLVED")
    # Remain conservative about unexplained mana recovery until a separately
    # anchored energy-state reducer exists. This was an older red-line.
    has_old_fruit=False
    for key,holder in previous_candidate_state.items():
        try:cell=json.loads(key)
        except (TypeError,ValueError):continue
        if (type(cell) is list and len(cell)==5 and cell[0]=="item"
            and cell[2]=="holder" and cell[3]=="author_plan"
            and type(cell[1]) is str and
            cell[1].endswith(("髓果","灵果","仙果"))):
            has_old_fruit=True
            break
    if has_old_fruit and (
        ("法力" in next_prose or "灵力" in next_prose) and
        re.search(r"(?:恢复|回涨|补满|充盈|暴涨)",next_prose) and
        not any(x in next_prose for x in (
            "吞下","吞服","吃下","丹药","运转功法","吸收","丹火","灵阵"))):
        findings.append("WF116_ENERGY_RECOVERY_WITHOUT_SOURCE")
    # Old V113 sword-tassel case stays unsettled: a new scene cannot
    # silently declare an already-disputed move a trusted prior fact.
    risks=list(previous_risks)[:16]
    if any(x.get("kind") in ("UNPROVEN_ITEM_TRANSFER",
                              "ITEM_OWNER_CHANGE_WITHOUT_TRANSFER")
           for x in risks) and re.search(r"(?:旧剑穗|剑穗).{0,24}(?:一直|早已|本来就在|自然就在)(?:索钩|钩尖)",next_prose):
        findings.append("WF116_SWORD_TASSEL_UNRESOLVED_RETCON")
    return {
        "format":"wf.writing.preflight.v116",
        "next_prose_sha256":_sha(next_prose),
        "blocked":bool(findings),
        "findings":findings[:12],
        "needs_review":bool(review_findings),
        "review_findings":list(dict.fromkeys(review_findings))[:12],
        "physical_relation_receipt_sha256":relations["receipt_sha256"],
        "physical_relation_review_pairs":relations["review_pairs"],
        "physical_relation_current_review_needed":(
            relations["current_source_needs_review"]),
        "physical_relation_prior_review_unresolved_count":(
            relations["previous_source_unresolved_review_count"]),
        "physical_relation_cannot_promote_to_holder_or_canon":True,
        "physical_relation_review_is_not_literary_error":True,
        "arm_actor_scope":"EXPLICIT_SOURCE_SUBJECT_ONLY",
        "v122_item_state_audit_sha256":item_audit["receipt_sha256"],
        "v122_item_actor_scope":"EXPLICIT_NARRATED_SOURCE_ONLY",
        "v122_source_events_count":len(item_audit["candidate_source_events"]),
        "v122_candidate_state_not_promoted_to_reducer":True,
        "model_calls":0,"literary_truth_proven":False,
        "automatic_rewrite":False,"new_model_retries":0,
    }


def compact_verified_delta_context(report, reducer):
    """Bounded *existing* temporal state for the next writer prompt."""
    if report.get("format")!=FMT:raise ValueError("WF116_BAD_SOURCE_REPORT")
    if reducer.get("format")!="wf.fallback.novel-studio.result.v114":
        raise ValueError("WF116_BAD_REDUCER_REPORT")
    state=reducer.get("candidate_state",{})
    lines=["【原文动作事件的候选状态，非正典；下一段须交代状态变化】"]
    for key,value in sorted(state.items()):
        try: domain,entity,predicate,scope,_=json.loads(key)
        except (TypeError,ValueError):continue
        if scope!="author_plan":continue
        if domain=="item" and predicate=="holder":
            lines.append(f"{entity}：上一段最后有证据的位置为{value}；转移需写出交接动作。")
        if domain=="character" and predicate in ("右臂可用性","右臂伤情"):
            lines.append(f"{entity}{predicate}：{value}；受伤未自动痊愈，"
                         "继续打斗不能凭空恢复右臂动作。")
    for risk in reducer.get("risks",[])[:4]:
        lines.append("未决变化："+risk["kind"]+"；不自动改写或接受。")
    for risk in report.get("unresolved",[])[:3]:
        lines.append("不确定证据："+risk["code"])
    lines.append("咬住灵果不等于吞服，未看到资源补充就不能推定法力恢复；"
                 "保持正常小说节奏，不要解释成清单。")
    return "\n".join(lines)[:1150]
