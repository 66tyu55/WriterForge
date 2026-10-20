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
        need(parent is None or (
             type(parent) is str and parent in prior and
             prior[parent] in CAUSAL_KINDS),
             "WF96_CAUSAL_PARENT_NOT_PRIOR_EXPLICIT_ACTION")
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


def _approved_exclusions(phrases):
    need(type(phrases) in (list,tuple) and
         len(phrases)<=MAX_APPROVED_EXCLUSIONS and
         all(_text(x,3,90) for x in phrases) and
         len(set(phrases))==len(phrases),
         "WF96_AUTHOR_GUARD_LIST_INVALID")
    return tuple(phrases)


def check_turn(raw,beat, *, mode, accepted=(),
               author_confirmed_forbidden_phrases=()):
    """Return a provisional prose and metadata-only receipt.

    B (split_only): segmentation without evidence gate; C (causal_guard):
    same JSON response format but strict anchors/parent/evidence checks.
    WriterForge only has a verified quote, not independent literary truth.
    """
    need(mode in ("split_only","causal_guard"),
         "WF96_UNKNOWN_EXPERIMENTAL_DRAFT_MODE")
    need(type(beat) is dict and set(beat)==BEAT_FIELDS,
         "WF96_TURN_BEAT_NOT_FROZEN")
    guards=_approved_exclusions(author_confirmed_forbidden_phrases)
    doc=_strict_json(raw,MAX_TURN_JSON_BYTES)
    need(set(doc)==TURN_FIELDS and
         _text(doc["prose"],MIN_PROSE_CHARS,MAX_PROSE_CHARS) and
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
        "kind":beat["kind"],
        "parent_turn_id":beat["causal_parent"],
        "causal_check":"SPLIT_ONLY_UNVERIFIED",
        "action_anchor":None,"effect_anchor":None,
        "parent_effect_sha256":None,
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
            required=old[parent].get("effect_quote")
            need(type(required) is str and required and
                 trace["parent_effect_quote"]==required and
                 len(_occurrences(old[parent]["prose"],required))==1,
                 "WF96_PARENT_CAUSE_NOT_ANCHORED_IN_PREVIOUS_PROSE")
            recorded["parent_effect_sha256"]=digest(
                required.encode("utf8"))
        if beat["kind"] in CAUSAL_KINDS:
            need(action is not None and effect_quote is not None,
                 "WF96_ACTION_NEEDS_ACTUAL_ACTION_AND_EFFECT")
        if action is None or effect_quote is None:
            need(action is None and effect_quote is None,
                 "WF96_PARTIAL_ACTION_EFFECT_NOT_ALLOWED")
        else:
            a=_quote_anchor(prose,action,"ACTION")
            b=_quote_anchor(prose,effect_quote,"EFFECT")
            need(a["end"]<=b["start"],
                 "WF96_ACTION_EFFECT_OVERLAP_OR_REVERSED")
            recorded["action_anchor"]=a
            recorded["effect_anchor"]=b
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
    )
    if mode=="causal_guard":
        note+=(
            "\n【仅用于候选层的程序核验】"
            "实际文字需体现当前事件的选择/阻力/变化；若前因未出现，"
            "请承认不确定，不得凭空宣布已造成后果。"
            "你对人物动机的判断尚未证明，不能输出已验证事实状态。"
        )
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
