"""V101: WF-owned narrative comprehension after a genuinely sealed reading.

Concepts adapted (not code copied) from StoryWeave's chapter reveal fence,
StoryWriter's event links, Story Engine's plot-residue counterfactual, and
WritingPreferenceBench's evidence-based prose preferences.

MODEL OUTPUT IS A CANDIDATE, NOT TRUTH. This module is pure/offline:
no external model, storage, self-grading, FactJournal KNOWN or WRITE access.
The V80 opt-in adapter owns the existing R2 PASS-A and billing boundaries.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,79}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
MODES = frozenset(("DIRECT_NARRATION","CHARACTER_SAYS","INFERENCE","UNCERTAIN"))
RELATIONS = frozenset(("PROTECTS","TRUSTS","SUSPECTS","OWES","OPPOSES",
                       "HELPS","BETRAYS","FAMILY_CLAIM","UNKNOWN"))
CRAFT = frozenset(("EFFECTIVE","WEAK","UNCERTAIN"))
SCHEMA = frozenset(("cast","relationships","plot","craft"))
ANCHOR = frozenset(("unit","quote"))
MAX_UNITS=80
MAX_SOURCE_CHARS=40000
MAX_MODEL_BYTES=21000
MAX_CAST=12
MAX_REL=16
MAX_PLOT=12
MAX_CRAFT=4
MAX_CONTEXT_CHARS=2300
MAX_HISTORY=12


class V101ReadingError(ValueError):
    pass


def require(ok,code):
    if not ok:
        raise V101ReadingError(code)


def packed(o):
    return json.dumps(o,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")


def digest(raw):
    return sha256(raw).hexdigest()


def _id(o):
    return type(o) is str and _ID.fullmatch(o) is not None


def _words(value,minimum=1,maximum=180):
    return (type(value) is str and minimum<=len(value.strip())<=maximum and
            "\ufffd" not in value and "\x00" not in value and
            all(ord(ch)>=32 for ch in value))


def _fields(item,fields,code):
    require(type(item) is dict and set(item)==set(fields),code)


def _narration(source_windows):
    require(type(source_windows) in (list,tuple) and
            1<=len(source_windows)<=MAX_UNITS and
            all(type(x) is str and x and "\ufffd" not in x
                and "\x00" not in x for x in source_windows) and
            sum(map(len,source_windows))<=MAX_SOURCE_CHARS,
            "WF101_SOURCE_WINDOWS_UNBOUNDED_OR_INVALID")


def _witness(windows,item):
    """WF finds its own offsets: model-supplied quotes are never a proof."""
    _fields(item,ANCHOR,"WF101_WITNESS_SCHEMA")
    unit=item["unit"]
    quote=item["quote"]
    require(type(unit) is int and 1<=unit<=len(windows)
            and _words(quote,6,120),"WF101_WITNESS_UNIT_OR_QUOTE_INVALID")
    source=windows[unit-1]
    offset=source.find(quote)
    require(offset>=0,"WF101_QUOTE_NOT_IN_ALREADY_READ_SOURCE")
    require(source.find(quote,offset+1)<0,
            "WF101_AMBIGUOUS_REPEATED_QUOTE")
    return {"unit":unit,"start":offset,"end":offset+len(quote),
            "source_unit_sha256":digest(source.encode("utf8")),
            "quote_sha256":digest(quote.encode("utf8"))}


def _before(a,b):
    return (a["unit"],a["end"]) <= (b["unit"],b["start"])


def _explanation(s,name):
    require(_words(s,6,200),"WF101_"+name.upper()+"_UNBOUNDED")
    return s.strip()


def _unpacked_model(output):
    if isinstance(output,str):
        require(len(output.encode("utf8"))<=MAX_MODEL_BYTES,
                "WF101_MODEL_OUTPUT_OVER_BUDGET")
        try:
            def unique_pairs(pairs):
                result={}
                for k,v in pairs:
                    if k in result:
                        raise ValueError("duplicate JSON field")
                    result[k]=v
                return result
            obj=json.loads(output,object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(
                              ValueError("nonfinite")))
        except (ValueError,UnicodeError,TypeError,OverflowError):
            raise V101ReadingError("WF101_MODEL_JSON_INVALID") from None
    else:
        obj=output
    try:
        require(len(packed(obj))<=MAX_MODEL_BYTES,
                "WF101_MODEL_OUTPUT_OVER_BUDGET")
    except (ValueError,UnicodeError,TypeError):
        raise V101ReadingError("WF101_MODEL_JSON_INVALID") from None
    _fields(obj,SCHEMA,"WF101_MODEL_SCHEMA")
    for name,limit in (("cast",MAX_CAST),("relationships",MAX_REL),
                       ("plot",MAX_PLOT),("craft",MAX_CRAFT)):
        require(type(obj[name]) is list and len(obj[name])<=limit,
                "WF101_"+name.upper()+"_LIST_BOUND")
    return obj


def _prior_event_index(history):
    result={}
    for old in history:
        for event in old.get("plot",[]):
            require(_id(event["event_id"]) and
                    event["event_id"] not in result,
                    "WF101_DUPLICATE_PRIOR_EVENT")
            result[event["event_id"]]=event
    return result


def validate_narrative(*,story_id,source_sha256,chapter,source_windows,
                       model_output,prior_history=()):
    """Validate visible source witnesses; preserve uncertainty and hypotheses.

    Public source order is not fictional time. Prior history must have passed
    check_history and only include previous chapters from THIS source.
    """
    require(_id(story_id) and type(source_sha256) is str and
            _SHA.fullmatch(source_sha256) is not None and
            type(chapter) is int and 1<=chapter<=10000000,
            "WF101_STORY_SOURCE_OR_CHAPTER_INVALID")
    _narration(source_windows)
    history=check_history(prior_history,story_id=story_id,
                          source_sha256=source_sha256,
                          before_chapter=chapter)
    obj=_unpacked_model(model_output)
    cast=[]
    active={}
    for member in obj["cast"]:
        _fields(member,("id","name","goal","knowledge_position",
                        "epistemic_mode","evidence"),"WF101_CAST_SCHEMA")
        who,name=member["id"],member["name"]
        require(_id(who) and who not in active and _words(name,1,32),
                "WF101_CAST_ID_OR_NAME_INVALID")
        w=_witness(source_windows,member["evidence"])
        # A pronoun or a repeated name is not automatically canonical ID.
        # Require direct name evidence; no automatic alias merging.
        require(name in member["evidence"]["quote"],
                "WF101_CAST_NAME_NOT_GROUNDED")
        require(member["epistemic_mode"] in MODES,
                "WF101_CAST_EPISTEMIC_MODE")
        cast.append({"id":who,"name":name,
                     "goal_hypothesis":_explanation(member["goal"],"GOAL"),
                     "knowledge_hypothesis":_explanation(
                         member["knowledge_position"],"KNOWLEDGE"),
                     "epistemic_mode":member["epistemic_mode"],
                     "source_anchor":w,
                     "character_identity_semantically_confirmed":False})
        active[who]=name
    all_prior=_prior_event_index(history)
    relationships=[]
    for member in obj["relationships"]:
        _fields(member,("from","to","kind","meaning","epistemic_mode",
                        "evidence","revises"),"WF101_RELATION_SCHEMA")
        lhs,rhs=member["from"],member["to"]
        require(lhs in active and rhs in active and lhs!=rhs and
                member["kind"] in RELATIONS and
                member["epistemic_mode"] in MODES,
                "WF101_RELATION_PARTICIPANTS_OR_DIRECTION_INVALID")
        witness=_witness(source_windows,member["evidence"])
        if member["revises"] is not None:
            require(_id(member["revises"]) and
                    any(member["revises"]==p["relation_id"] and
                        lhs==p["from"] and rhs==p["to"]
                        for old in history for p in old.get("relationships",[])),
                    "WF101_UNGROUNDED_RELATION_REVISION")
        relationships.append({
            "relation_id":f"r{chapter:06d}_{len(relationships)+1:02d}",
            "from":lhs,"to":rhs,"kind_hypothesis":member["kind"],
            "meaning_hypothesis":_explanation(member["meaning"],"RELATION"),
            "epistemic_mode":member["epistemic_mode"],
            "revises":member["revises"],"source_anchor":w,
            "relationship_truth_verified":False,
        })
    local={}
    plot=[]
    for item in obj["plot"]:
        _fields(item,("id","actor","want","obstacle","action","effect",
                      "cost","prior_event","why","alternative",
                      "unresolved_debt","resolves"),
                "WF101_PLOT_SCHEMA")
        event=item["id"]
        require(_id(event) and event not in local and
                item["actor"] in active,"WF101_PLOT_ACTOR_OR_ID")
        action=_witness(source_windows,item["action"])
        effect=(_witness(source_windows,item["effect"])
                if item["effect"] is not None else None)
        if effect is not None:
            require(_before(action,effect),
                    "WF101_EFFECT_BEFORE_VISIBLE_ACTION")
        cost=(_witness(source_windows,item["cost"])
              if item["cost"] is not None else None)
        parent=item["prior_event"]
        full_id=f"e{chapter:06d}_{event}"
        require(full_id not in all_prior,"WF101_DUPLICATE_EVENT")
        parent_rec=None
        if parent is not None:
            require(_id(parent) and
                    (parent in local or parent in all_prior),
                    "WF101_CAUSAL_PARENT_NOT_PREVIOUSLY_READ")
            parent_rec=local.get(parent,all_prior.get(parent))
            require(parent_rec["effect_anchor"] is not None,
                    "WF101_CAUSAL_PARENT_NO_OBSERVED_EFFECT")
            if parent in local:
                require(_before(parent_rec["effect_anchor"],action),
                        "WF101_CAUSE_NOT_BEFORE_NEW_ACTION")
        resolves=item["resolves"]
        if resolves is not None:
            require(_id(resolves) and resolves in all_prior and
                    all_prior[resolves]["unresolved_debt"] is not None,
                    "WF101_RESOLUTION_NOT_AN_OPEN_PRIOR_THREAD")
        require(item["unresolved_debt"] is None or
                _words(item["unresolved_debt"],6,160),
                "WF101_DEBT_INVALID")
        rec={
            "event_id":full_id,"actor":item["actor"],
            "want_hypothesis":_explanation(item["want"],"WANT"),
            "obstacle_hypothesis":_explanation(item["obstacle"],"OBSTACLE"),
            "action_anchor":action,"effect_anchor":effect,
            "cost_anchor":cost,
            "prior_event_id":(parent_rec["event_id"]
                              if parent_rec is not None else None),
            "causal_hypothesis":_explanation(item["why"],"WHY"),
            "alternative_explanation":_explanation(
                item["alternative"],"ALTERNATIVE"),
            "unresolved_debt":item["unresolved_debt"],
            "proposed_resolution_of":resolves,
            "causal_semantics_verified":False,
            "true_cost_semantics_verified":False,
        }
        local[event]=rec
        plot.append(rec)
    craftsmanship=[]
    for item in obj["craft"]:
        _fields(item,("quote","judgement","effect","reason",
                      "counterfactual","tradeoff","alternative_reading"),
                "WF101_CRAFT_SCHEMA")
        require(item["judgement"] in CRAFT,
                "WF101_CRAFT_NOT_A_VALID_HYPOTHESIS")
        craftsmanship.append({
            "source_anchor":_witness(source_windows,item["quote"]),
            "judgement_hypothesis":item["judgement"],
            "reader_effect_hypothesis":_explanation(item["effect"],"EFFECT"),
            "why_this_sentence":_explanation(item["reason"],"CRAFT_REASON"),
            "alternative_wording":_explanation(
                item["counterfactual"],"COUNTERFACTUAL"),
            "counterfactual_tradeoff":_explanation(
                item["tradeoff"],"TRADEOFF"),
            "alternative_interpretation":_explanation(
                item["alternative_reading"],"ALT_READING"),
            "good_or_bad_independently_judged":False,
        })
    receipt={
        "format":"wf.learn.narrative-comprehension.v101",
        "story_id":story_id,"source_sha256":source_sha256,
        "chapter":chapter,
        "unit_sha256s":[digest(s.encode("utf8")) for s in source_windows],
        "cast":cast,"relationships":relationships,"plot":plot,
        "craft":craftsmanship,
        "previous_reader_receipt_sha256":(
             digest(packed(history[-1])) if history else None),
        "source_quotes_are_anchors_not_semantic_proof":True,
        "characters_and_relations_independently_verified":False,
        "narrative_causality_verified":False,
        "sentence_quality_independently_verified":False,
        "reader_predictions_independently_calibrated":False,
        "literary_graduation":False,"new_canonical_facts":0,
        "model_weights_finetuned":False,
        "text_from_novel_not_in_receipt":True,
    }
    return receipt


def check_history(history,*,story_id,source_sha256,before_chapter):
    require(type(history) in (tuple,list) and len(history)<=MAX_HISTORY,
            "WF101_HISTORY_OVER_BUDGET")
    former=0
    # A bounded history may be a suffix of a longer immutable CAS chain.
    prior_sha=history[0].get("previous_reader_receipt_sha256") if history else None
    require(prior_sha is None or (type(prior_sha) is str and
            _SHA.fullmatch(prior_sha) is not None),
            "WF101_HISTORY_PARENT_CAS_INVALID")
    for rec in history:
        require(type(rec) is dict and
                rec.get("format")=="wf.learn.narrative-comprehension.v101"
                and rec.get("story_id")==story_id and
                rec.get("source_sha256")==source_sha256 and
                type(rec.get("chapter")) is int and
                former<rec["chapter"]<before_chapter and
                rec.get("previous_reader_receipt_sha256")==prior_sha
                and rec.get("literary_graduation") is False
                and rec.get("new_canonical_facts")==0
                and rec.get("narrative_causality_verified") is False
                and rec.get("sentence_quality_independently_verified") is False
                and rec.get("text_from_novel_not_in_receipt") is True,
                "WF101_HISTORY_SOURCE_FRONTIER_OR_CHAIN_INVALID")
        former=rec["chapter"]
        prior_sha=digest(packed(rec))
    return history


def reader_context(*,history,story_id,source_sha256,before_chapter):
    """Short derived PROJECTION of a private append-only history, not a DB."""
    check_history(history,story_id=story_id,
                  source_sha256=source_sha256,before_chapter=before_chapter)
    # Most recent observations first. This is marked as uncertain because
    # even a perfect quote match cannot prove relationship/quality semantics.
    heads=["【WF过去已读章节的候选理解，未经独立语义证实】"]
    budget=MAX_CONTEXT_CHARS-len(heads[0])
    seen_actor=set()
    seen_relation=set()
    seen_debt=set()
    for doc in reversed(history):
        c=doc["chapter"]
        candidates=[]
        for p in reversed(doc["cast"]):
            if p["id"] not in seen_actor:
                candidates.append((("actor",p["id"]),
                  f"第{c}章 人物{p['id']}：目的猜测{p['goal_hypothesis']}；知情/误判猜测{p['knowledge_hypothesis']}。"))
        for p in reversed(doc["relationships"]):
            pair=(p["from"],p["to"],p["kind_hypothesis"])
            if pair not in seen_relation:
                candidates.append((("relation",pair),
                  f"第{c}章 {p['from']}→{p['to']} 关系候选{p['kind_hypothesis']}：{p['meaning_hypothesis']}。"))
        for p in reversed(doc["plot"]):
            if p["unresolved_debt"] and p["event_id"] not in seen_debt:
                candidates.append((("debt",p["event_id"]),
                  f"第{c}章 未解决后果/问题{p['event_id']}：{p['unresolved_debt']}。"))
        for k,s in candidates:
            if len(s)>budget:
                continue
            heads.append(s)
            budget-=len(s)
            if k[0]=="actor":seen_actor.add(k[1])
            elif k[0]=="relation":seen_relation.add(k[1])
            else:seen_debt.add(k[1])
    notice="这些是待核对假说，不是角色已知真相；不能提前看后文，不可把关系标签当剧情。"
    # Always reserve the epistemic warning: it must never be truncated away.
    return ("\n".join(heads)[:MAX_CONTEXT_CHARS-len(notice)-1]
            +"\n"+notice)


SYSTEM=(
    "你是WriterForge自己的小说阅读理解模块。只读已经解锁的原文。"
    "理解人物想要什么、知道什么、误会什么；谁与谁关系怎样变化，"
    "哪件真实行动改变下一件事，付出了何种代价；分析句子好坏时必须"
    "解释读者效果并提出替换措辞的反事实比较。"
    "禁止抄写他人作品到新小说、禁止宣布自己文学进步。"
    "所有关系、因果、好坏仅是假说，模糊就少报或留空。"
    "只输出严格JSON对象，不带Markdown。"
)


def model_reading_prompt(*,source_windows,prior_context=""):
    _narration(source_windows)
    require(type(prior_context) is str and
            len(prior_context)<=MAX_CONTEXT_CHARS and
            "\ufffd" not in prior_context,
            "WF101_PRIOR_READER_CONTEXT_TOO_LARGE")
    src="\n".join("UNIT "+str(i)+" "+text
                  for i,text in enumerate(source_windows,1))
    # Model supplies precise text quotes, NEVER character offsets.
    return (
      "【过去的候选理解（禁止将猜测当已知事实）】\n"+prior_context+
      "\n【本章已经完成PASS A密封的连续原文，不含未来章节】\n"+src+
      "\n独立分析当前这一章，不要重复看不到的前章原文。"
      "只返回JSON：cast=[{id,name,goal,knowledge_position,"
      "epistemic_mode,evidence:{unit,quote}}]（人物名必须在引用内）；"
      "relationships=[{from,to,kind,meaning,epistemic_mode,"
      "evidence:{unit,quote},revises:null或旧关系id}]；"
      "plot=[{id,actor,want,obstacle,action:{unit,quote},"
      "effect:null或{unit,quote},cost:null或{unit,quote},"
      "prior_event:null或本章前序id/之前完整事件id,"
      "why,alternative,unresolved_debt:null或文字,"
      "resolves:null或以前未结事件完整id}]；"
      "craft=[{quote:{unit,quote},judgement:EFFECTIVE/WEAK/UNCERTAIN,"
      "effect,reason,counterfactual,tradeoff,alternative_reading}]。"
      "根对象只能有cast、relationships、plot、craft四个键。"
      "每一项6到120字的quote都必须只在所选原文单位出现一次。"
      "同一章最多12人物、16关系、12情节事件、4处句子。"
      "不能给人物自动取同义别名；关系有方向，人物撒谎不等于事实。"
      "因果没有真实可见后果时填null，不许猜不存在的句子。"
      "哪句话好应解释它因人物与情节具体有什么作用，"
      "不能只说'细腻生动'。"
    )
