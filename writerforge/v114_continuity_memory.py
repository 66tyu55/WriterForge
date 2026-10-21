"""V114 narrow, zero-model literary CONTINUITY probes over actual generated prose.

Never trust a model-authored 'this is consistent' flag. Track *observable*
item holders, explicit transfers and weapon availability with exact offsets.
Inferences are candidates, not narrative truths or FactJournal KNOWN.
No model calls or novel-rewriting. Deliberately leave unsupported Chinese
constructions UNKNOWN; this is a calibrated risk detector, not semantics.

The same immutable episode/memory receipt feeds the NEXT V96 writer turn,
not just an after-the-fact report. If a detector cannot keep up, V114's
approved fallback is a pinned MIT Novel Studio temporal state reducer,
not a parallel book database.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

MAX_PROSE=20000
MAX_ITEMS=22
MAX_OBSERVATIONS=55
MAX_PRIOR=12
MAX_CONTEXT=1400
TRACKED=("剑穗","飞剑","骨符","锁魂索","法剑","佩剑","残符",
         "灵果","丹药","火丹","血刀","阵旗","灵石","短剑")
# Deliberately STRICT: a metaphor like "一剑心头" isn't inventory.
DISCLOSED_TRANSFER=("取下","摘下","扯下","撕下","拽下","割下","钩断",
                    "勾下","勾走","卷走","交给","递给","绑到","挂到",
                    "系到","甩到","掷到","落到","坠到","从腰间")
SOFT_NARRATION=("梦见","梦中","以为","仿佛","似乎","听说","传言","若是",
                "想象","回忆","想起","猜测","或许","可能","说那")
CLAIMED_HOLDERS=("腰间","钩尖","索钩","手中","剑柄","怀中","山壁")
CAUSES_REVIEW=("ITEM_OWNER_CHANGE_WITHOUT_TRANSFER",
               "WEAPON_USED_BEFORE_RETURN","LATE_POWER_SOURCE_UNESTABLISHED")

class V114ContinuityError(ValueError):
    pass

def require(ok,code):
    if not ok:raise V114ContinuityError(code)

def hashb(data):
    return sha256(data).hexdigest()

def packed(x):
    return json.dumps(x,ensure_ascii=False,separators=(",",":"),
                      sort_keys=True,allow_nan=False).encode("utf8")

def _span(body,needle,start,end):
    quote=body[start:end]
    return {
        "start":start,"end":end,"quote_sha256":hashb(quote.encode("utf8")),
        "source_sha256":hashb(body.encode("utf8")),
        "source_verified":True,
    }

def _contexts(body):
    """Offsets of textual clauses; don't ascribe hypotheses as narrator facts."""
    start=0
    for match in re.finditer(r"[。！？；\n]",body):
        end=match.end()
        if end>start:
            yield start,end,body[start:end]
        start=end
    if start<len(body):yield start,len(body),body[start:]

def _holder_clause(segment,item,cast,nearby_before=""):
    if any(x in segment for x in SOFT_NARRATION):return None
    if item not in segment:return None
    # Explicit human carrier and a named item. The item need not be
    # adjacent to the name (old emotional props often carry a description).
    for actor in cast:
        pattern=re.escape(actor)+r".{0,9}(?:腰间|怀中|手中).{0,36}"+re.escape(item)
        if re.search(pattern,segment):
            return actor
    # Only a LOW-CONFIDENCE narrative proposal: "他腰间" without the
    # character name inside this sentence can refer to the most recently
    # explicitly named on-stage actor. Do not upgrade this to KNOWLEDGE.
    if re.search(r"他(?:的)?腰间.{0,28}"+re.escape(item),segment):
        named=[(nearby_before.rfind(actor),actor) for actor in cast
               if actor in nearby_before]
        if named:
            return max(named)[1]
    if re.search(r"(?:索头|锁魂索|钩尖|索钩).{0,36}"+re.escape(item),segment):
        if re.search(r"(?:钩尖上|索钩上|索头(?:上)?).{0,18}(?:挂|系|缠|带着)",segment):
            return "索钩"
    if re.search(r"(?:山壁|石壁).{0,18}"+re.escape(item),segment) and any(
            x in segment for x in ("钉进","插在","嵌在")):
        return "山壁"
    return None

def _independent_transfer(body,before,after,item):
    """Real *intervening* language must ground a carrier change."""
    text=body[before:after]
    if len(text)>650:
        # Cannot establish evidence across huge unseen spans safely.
        return False
    if item not in text:return False
    return any(verb in text for verb in DISCLOSED_TRANSFER)

def literal_item_continuity(prose,*,cast=(),tracked=TRACKED,prior_report=None):
    """Detect source-anchored continuity risks, NOT a semantic correction."""
    require(type(prose) is str and 0<len(prose)<=MAX_PROSE,
            "WF114_PROSE_BOUNDS")
    require(type(cast) in (list,tuple) and len(cast)<=10 and
            all(type(x) is str and 1<=len(x)<=16 for x in cast),
            "WF114_CAST_BOUNDS")
    require(type(tracked) in (tuple,list) and len(tracked)<=MAX_ITEMS and
            all(type(x) is str and 1<=len(x)<=16 for x in tracked),
            "WF114_ITEM_KEY_BOUNDS")
    candidates=[]
    risks=[]
    seen={}
    if prior_report is not None:
        require(type(prior_report) is dict and
                prior_report.get("format")==
                    "wf.writing.candidate-literal-continuity.v114",
                "WF114_PRIOR_REPORT_NOT_CANDIDATE")
        previous_active=prior_report.get(
            "active_state",prior_report.get("observations",[]))
        require(type(previous_active) is list and
                len(previous_active)<=MAX_ITEMS,
                "WF114_PRIOR_ACTIVE_STATE_UNBOUNDED")
        for e in previous_active:
            seen[e["item"]]={
                "item":e["item"],"holder_hypothesis":e["holder_hypothesis"],
                "anchor":e["anchor"],"event_end":0}
    clauses=list(_contexts(prose))
    for beginning,end,segment in clauses:
        for item in tracked:
            if item not in segment:continue
            holder=_holder_clause(segment,item,cast,
                                  nearby_before=prose[max(0,beginning-100):beginning])
            if holder is None:continue
            idx=segment.rfind(item)
            start=beginning+idx
            event={"item":item,"holder_hypothesis":holder,
                   "anchor":_span(prose,item,start,start+len(item)),
                   "event_end":end,
                   "narrator_fact_semantically_verified":False}
            if item in seen:
                prior=seen[item]
                if prior["holder_hypothesis"]!=holder and not _independent_transfer(
                        prose,prior["event_end"],beginning,item):
                    risks.append({
                        "kind":"ITEM_OWNER_CHANGE_WITHOUT_TRANSFER",
                        "item":item,
                        "before_holder":prior["holder_hypothesis"],
                        "after_claimed_holder":holder,
                        "before_anchor":prior["anchor"],
                        "after_anchor":event["anchor"],
                        "candidate_needs_source_review":True,
                        "not_proven_impossible_in_fiction":True,
                    })
            candidates.append(event)
            seen[item]=event
            require(len(candidates)<=MAX_OBSERVATIONS,
                    "WF114_MAX_ITEM_OBSERVATIONS_NO_SILENT_EVICTION")
    # A weapon thrown away, lodged in rock, then used before a pickup or
    # explicit remotely-controlled maneuver is suspicious, not hard wrong.
    free_at=None
    for beginning,end,segment in clauses:
        if "飞剑" in segment and any(x in segment for x in (
                "脱手","掷出","钉进","插在山壁","嵌入山壁")):
            free_at=beginning
        if free_at is not None:
            if re.search(r"(?:拔出|召回|招回|御剑|隔空取回|收回|重新握住|再拾起).{0,18}(?:飞剑|剑)",segment):
                free_at=None
            elif re.search(r"(?:反身一剑|挥剑|持剑|执剑|举剑)",segment):
                risks.append({
                    "kind":"WEAPON_USED_BEFORE_RETURN",
                    "item":"飞剑",
                    "prior_disposal_start":free_at,
                    "suspect_action_anchor":_span(prose,"",beginning,end),
                    "candidate_needs_source_review":True,
                    "remote_sword_technique_not_ruled_out":True,
                })
                # avoid repeated duplicate warnings from subsequent clauses
                free_at=None
    for idx,(start,end,segment) in enumerate(clauses):
        if ("丹田" in segment and any(x in segment for x in ("空得","枯竭","耗尽"))
                and idx+1<len(clauses)):
            later=prose[end:end+250]
            if ("灵果" in later or "青果" in later) and any(x in later for x in (
                    "法力回涨","灵气回涨","恢复","补足","回涨")):
                risks.append({
                    "kind":"LATE_POWER_SOURCE_UNESTABLISHED",
                    "resource":"法力",
                    "loss_anchor":_span(prose,"",start,end),
                    "later_source_previously_known":False,
                    "candidate_needs_source_review":True,
                    "source_could_have_been_foreshadowed_elsewhere":True,
                })
                break
    return {
        "format":"wf.writing.candidate-literal-continuity.v114",
        "prose_sha256":hashb(prose.encode("utf8")),
        "items_seen":len(candidates),
        "observations":candidates,
        "active_state":[seen[k] for k in sorted(seen)],
        "risks":risks,
        "no_silent_transfer_or_resource_creation":True,
        "mechanical_coverage_limited_to_observable_phrases":True,
        "semantic_literary_continuity_verified":False,
        "model_calls_for_validation":0,
        "no_authoritative_fact_writes":True,
    }

def compact_status(report):
    require(type(report) is dict and report.get("format")==
            "wf.writing.candidate-literal-continuity.v114",
            "WF114_REPORT_NOT_VALIDATED")
    # Only grounded, observed claims in *previous* actual prose.
    latest={}
    for e in report.get("active_state",report["observations"]):
        latest[e["item"]]=e["holder_hypothesis"]
    parts=["【前段真实正文的候选物件状态（不能把预测或修辞当成正典）】"]
    for item,holder in sorted(latest.items()):
        parts.append(f"{item}最后明确出现在{holder}。改变位置必须写出可信动作；"
                     "若无证据，保留未知。")
    for issue in report["risks"][-6:]:
        parts.append("前文有待复核连续性风险："+issue["kind"]+" "+
                     str(issue.get("item",issue.get("resource",""))))
    parts.append("不要为补丁凭空新增法器、后续法力或人物移动；"
                 "不强迫每一幕都牺牲，情感与物件动作必须自然。")
    return "\n".join(parts)[:MAX_CONTEXT]

def validated_checkpoint(*,prose,cast=(),previous=None):
    """Signed candidate chain; no notebook/canon promotion or model retry."""
    prior=None
    n=1
    prior_report=None
    if previous is not None:
        require(type(previous) is dict and
                previous.get("format")=="wf.writing.continuity-checkpoint.v114" and
                previous.get("receipt_sha256")==hashb(packed({
                    k:v for k,v in previous.items() if k!="receipt_sha256"})),
                "WF114_OLD_CONTINUITY_CHECKPOINT_UNTRUSTED")
        prior=previous["receipt_sha256"]
        n=previous["sequence"]+1
        prior_report=previous["report"]
    result=literal_item_continuity(prose,cast=cast,
                                   prior_report=prior_report)
    snapshot={
        "format":"wf.writing.continuity-checkpoint.v114",
        "sequence":n,"previous_checkpoint_sha256":prior,
        "actual_source_sha256":result["prose_sha256"],
        "report":result,
        "literary_semantics_verified":False,
        "canon_state_writes":0,
        "model_calls":0,
    }
    snapshot["receipt_sha256"]=hashb(packed(snapshot))
    return snapshot
