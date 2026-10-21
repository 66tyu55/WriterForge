"""V102: emotion -> cause -> cost -> consequence in existing WF rolling drafts.
Provenance constraints, not a semantic judge. Zero additional model calls.
All results are UNACCEPTED local candidate evidence, not canon or skills.
"""
from __future__ import annotations
from hashlib import sha256
import json
from .v96_causal_turns import (
    _strict_json,_occurrences,check_turn,canonical,
    MAX_TURN_JSON_BYTES,V96CausalDraftError,
)

MODE="emotion_rolling"
AFFECT_FIELDS=frozenset((
    "actor","before","after","trigger_quote","response_quote",
    "cost_quote","consequence_quote","open_pressure","choice_shift",
))
MAX_CONTEXT=1300
MAX_IN_MEMORY=16

class V102EmotionalCausalityError(ValueError):
    pass

def require(ok,code):
    if not ok:raise V102EmotionalCausalityError(code)

def digest(raw):
    return sha256(raw).hexdigest()

def bounded(value,low=1,high=150):
    return (type(value) is str and low<=len(value.strip())<=high and
            "\ufffd" not in value and "\x00" not in value and
            all(ord(ch)>=32 for ch in value))

def source_quote(prose,text,label):
    require(bounded(text,6,96),"WF102_"+label+"_QUOTE_BOUNDS")
    locs=_occurrences(prose,text)
    require(len(locs)==1,"WF102_"+label+"_NOT_UNIQUE_IN_REAL_PROSE")
    i=locs[0]
    return {"start":i,"end":i+len(text),
            "quote_sha256":digest(text.encode("utf8"))}

def verified_receipt(turn):
    rec=turn.get("affect_receipt") if type(turn) is dict else None
    require(type(rec) is dict and type(turn.get("prose")) is str and
            rec.get("prose_sha256")==digest(turn["prose"].encode("utf8")) and
            rec.get("receipt_sha256")==digest(canonical({
                k:v for k,v in rec.items() if k!="receipt_sha256"})),
            "WF102_PRIOR_EMOTION_RECEIPT_CORRUPT")
    require(rec.get("turn_id")==turn.get("beat_id") and
            rec.get("emotion_semantics_verified") is False and
            rec.get("cost_semantics_verified") is False and
            rec.get("confirmed_story_facts_written")==0,
            "WF102_PRIOR_EMOTION_TRUTH_FORGED")
    return rec

def check_emotional_turn(raw,beat,*,accepted=(),previous_chapter=(),
                         author_confirmed_forbidden_phrases=()):
    """Validate existing V96 result first; affect may be null on quiet scenes."""
    try:doc=_strict_json(raw,MAX_TURN_JSON_BYTES)
    except V96CausalDraftError as exc:
        raise V102EmotionalCausalityError(str(exc)) from None
    require(type(doc) is dict and set(doc)=={"prose","trace","affect"},
            "WF102_TURN_SCHEMA_INVALID")
    require(type(beat) is dict and type(beat.get("actor")) is str,
            "WF102_BEAT_INVALID")
    for t in accepted:verified_receipt(t)
    require(type(previous_chapter) in (tuple,list) and
            len(previous_chapter)<=MAX_IN_MEMORY,
            "WF102_PREVIOUS_CHAPTER_BOUND")
    for t in previous_chapter:verified_receipt(t)
    legacy=json.dumps({"prose":doc["prose"],"trace":doc["trace"]},
                      ensure_ascii=False,separators=(",",":"))
    old=check_turn(legacy,beat,mode="causal_guard",accepted=accepted,
                   author_confirmed_forbidden_phrases=author_confirmed_forbidden_phrases)
    prose=old["prose"]
    affect=doc["affect"]
    result={
        "format":"wf.writing.emotional-observation.v102",
        "turn_id":beat["id"],"prose_sha256":digest(prose.encode("utf8")),
        "actor":beat["actor"],"affect_state":"NOT_OBSERVED",
        "before_hypothesis":None,"after_hypothesis":None,
        "trigger_anchor":None,"response_anchor":None,"cost_anchor":None,
        "consequence_anchor":None,"open_pressure":None,
        "choice_shift_hypothesis":None,
        "emotion_semantics_verified":False,
        "cost_semantics_verified":False,
        "consequence_semantics_verified":False,
        "confirmed_story_facts_written":0,
    }
    if affect is not None:
        require(type(affect) is dict and set(affect)==AFFECT_FIELDS and
                affect["actor"]==beat["actor"],
                "WF102_AFFECT_ACTOR_OR_SCHEMA")
        for field in ("before","after"):
            require(bounded(affect[field],2,100),
                    "WF102_AFFECT_"+field.upper()+"_BOUNDS")
        for field in ("open_pressure","choice_shift"):
            require(affect[field] is None or bounded(affect[field],6,150),
                    "WF102_"+field.upper()+"_BOUNDS")
        trigger=source_quote(prose,affect["trigger_quote"],"TRIGGER")
        response=source_quote(prose,affect["response_quote"],"RESPONSE")
        require(trigger["end"]<=response["start"],
                "WF102_RESPONSE_PRECEDES_EMOTIONAL_TRIGGER")
        cost=(source_quote(prose,affect["cost_quote"],"COST")
              if affect["cost_quote"] is not None else None)
        consequence=(source_quote(prose,affect["consequence_quote"],"CONSEQUENCE")
                     if affect["consequence_quote"] is not None else None)
        if old["effect_quote"] is None:
            require(consequence is None,
                    "WF102_UNOBSERVED_EFFECT_ASSERTED")
        else:
            require(affect["consequence_quote"]==old["effect_quote"],
                    "WF102_EFFECT_NOT_SAME_AS_V96_VISIBLE_CONSEQUENCE")
        if cost is not None:
            act=old["receipt"]["action_anchor"]
            require(act is not None and cost["start"]>=act["end"],
                    "WF102_COST_BEFORE_ACTION_OR_NOT_AN_ACTION")
        last=None
        for previous in reversed(tuple(previous_chapter)+tuple(accepted)):
            prior=verified_receipt(previous)
            if (prior["actor"]==beat["actor"] and
                prior["affect_state"]=="QUOTED_EMOTIONAL_HYPOTHESIS"):
                last=prior["after_hypothesis"]
                break
        if last is not None:
            require(affect["before"] in (last,"未知","不确定"),
                    "WF102_ACTOR_EMOTION_UNEXPLAINED_RESET")
        result.update({
            "affect_state":"QUOTED_EMOTIONAL_HYPOTHESIS",
            "before_hypothesis":affect["before"],
            "after_hypothesis":affect["after"],
            "trigger_anchor":trigger,"response_anchor":response,
            "cost_anchor":cost,"consequence_anchor":consequence,
            "open_pressure":affect["open_pressure"],
            "choice_shift_hypothesis":affect["choice_shift"],
        })
    result["receipt_sha256"]=digest(canonical(result))
    return {**old,"affect_receipt":result}

def pressure_context(accepted):
    """Bonds unresolved costs and emotions to NEXT written scene, not canon."""
    require(type(accepted) in (tuple,list) and
            len(accepted)<=MAX_IN_MEMORY,"WF102_HISTORY_BOUND")
    for x in accepted:verified_receipt(x)
    lines=["【已有正文的情感与后果候选推断，不是已确认的人物真相】"]
    debts=[]
    emotions={}
    for x in accepted:
        r=x["affect_receipt"]
        if r["affect_state"]=="QUOTED_EMOTIONAL_HYPOTHESIS":
            emotions[r["actor"]]=r["after_hypothesis"]
            if r["cost_anchor"] is not None or r["open_pressure"]:
                debts.append((r["turn_id"],r["open_pressure"],
                              r["cost_anchor"] is not None))
    for who,state in sorted(emotions.items()):
        lines.append(f"人物{who}当前感受的候选：{state}。")
    for turn,pressure,has_quote in debts[-5:]:
        lines.append(f"{turn}仍有压力：{pressure or '尚未解释的可见损失'}"+
                     ("（代价原句存在）" if has_quote else "（代价尚未核实）"))
    notice="不要让前文压力无故消失；人物可冷静、含蓄或误判，没有可信情感时允许留白。"
    text="\n".join(lines)
    return text[:MAX_CONTEXT-len(notice)-1]+"\n"+notice

def emotion_turn_instructions(accepted):
    return (
        "\n【V102情感—因果—代价—后果，仅限当前作者选择的实验模式】\n"+
        pressure_context(accepted)+
        '\n本次仅输出JSON，根字段恰好为prose、trace、affect。'
        '其中prose和trace严格沿用V96原动作、后果及父事件引句。'
        'affect可为null（不强迫每一幕都有情感反转），或为'
        '{"actor":"本幕人物","before":"此前感受或未知",'
        '"after":"受刺激后感受",'
        '"trigger_quote":"本幕真实刺激原句",'
        '"response_quote":"刺激之后实际言语举止原句",'
        '"cost_quote":null或行动之后真实损失原句,'
        '"consequence_quote":null或与trace.effect_quote完全相同的原句,'
        '"open_pressure":null或尚未解决的局面压力,'
        '"choice_shift":null或这次变化如何影响人物下一步选择}。'
        '所有短引句在实际prose中必须唯一出现，情感触发早于人物反应。'
        '之前的情绪、损失并非绝对真相；不得写技巧说明书、为过门槛硬加悲惨代价。'
    )

def export_candidate_emotions(accepted):
    require(type(accepted) in (tuple,list) and
            2<=len(accepted)<=MAX_IN_MEMORY,"WF102_EXPORT_BOUND")
    records=[verified_receipt(x) for x in accepted]
    result={
        "format":"wf.writing.emotion-causality-candidate.v102",
        "turns":records,"source_is_actual_generated_candidate":True,
        "emotion_and_causality_independently_verified":False,
        "actual_cost_semantics_independently_verified":False,
        "author_accepted":False,"canon_or_factjournal_writes":0,
        "original_novel_text_not_embedded":True,
    }
    result["manifest_sha256"]=digest(canonical(result))
    return result
