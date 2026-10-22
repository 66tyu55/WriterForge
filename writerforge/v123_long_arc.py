"""V123: durable AUTHOR-CONFIRMED long-term character goals, not LLM memory.

A model's chapter outline or prose self-explanation cannot create, change,
settle or erase an accepted revenge goal. We preserve one compact SHA-linked
OPEN arc in the existing V117 story resume checkpoint, across independent
writing jobs and unrelated intervening chapters.

Only author-registered, original-source-anchored material can initialize this
candidate continuity lane; an unreviewed settlement claim becomes REVIEW,
not an automatic canon change. This module does not understand all literary
motives, identify real murderers or certify a scene's artistic quality.
"""
from __future__ import annotations
from hashlib import sha256
import json
import re

from .v116_state_delta import _segments, _present

FMT="wf.writing.v123.author-anchored-long-character-arc"
MAX_PROSE=20000
MAX_CHECKPOINT_BYTES=3000
MAX_TEXT=130
MAX_CHAPTER=1000000
MAX_CLAIMS=48
SHA=re.compile(r"[a-f0-9]{64}\Z")
NAME=re.compile(r"[\w\u3400-\u9fff-]{1,70}\Z")
ID=re.compile(r"[A-Za-z][A-Za-z0-9_-]{1,63}\Z")
CLOSE=re.compile(r"(?:大仇得报|报了仇|血仇已报|复仇成功|复仇已经完成|"
                 r"仇终于报了|已经报了仇|终于报仇|杀父之仇已报|亲手报仇)")
UNREAL=("如果","假如","梦见","做梦","想象","若是","传言",
        "据说","听说","仿佛","似乎")
TRIGGERS=("复仇","报仇","血债","旧仇","仇人","仇恨","杀父",
          "血仇","讨债")


class LongArcError(ValueError):
    pass


def _need(ok,code):
    if not ok:
        raise LongArcError(code)


def _digest(x):
    if type(x) is str:
        data=x.encode("utf8")
    else:
        data=json.dumps(x,sort_keys=True,ensure_ascii=False,
                        separators=(",",":"),allow_nan=False).encode("utf8")
    return sha256(data).hexdigest()


def _validate(value,*,project_id,scene_id):
    _need(type(value) is dict and value.get("format")==FMT and
          value.get("project_id")==project_id and
          value.get("scene_id")==scene_id and
          value.get("kind")=="REVENGE" and
          value.get("status")=="OPEN_AUTHOR_CONFIRMED" and
          value.get("author_confirmed") is True and
          value.get("canon_writes")==0 and
          value.get("model_calls")==0 and
          value.get("author_confirmation_is_not_semantic_proof") is True and
          value.get("automatic_resolution_count")==0,
          "WF123_ARC_SCOPE_OR_AUTHORITY_INVALID")
    _need(type(value.get("arc_id")) is str and ID.fullmatch(value["arc_id"])
          and type(value.get("actor")) is str and NAME.fullmatch(value["actor"])
          and type(value.get("target")) is str and NAME.fullmatch(value["target"])
          and value["actor"]!=value["target"] and
          type(value.get("motive")) is str and
          3<=len(value["motive"])<=MAX_TEXT and
          value.get("truth_scope") in ("AUTHOR_ASSERTED","CHARACTER_BELIEF"),
          "WF123_ARC_FIELDS_INVALID")
    _need(type(value.get("origin_chapter")) is int and
          0<=value["origin_chapter"]<=MAX_CHAPTER and
          type(value.get("last_chapter")) is int and
          value["origin_chapter"]<=value["last_chapter"]<=MAX_CHAPTER and
          type(value.get("chapter_advances")) is int and
          value["chapter_advances"]==
              value["last_chapter"]-value["origin_chapter"] and
          type(value.get("settlement_claim_count")) is int and
          0<=value["settlement_claim_count"]<=MAX_CLAIMS,
          "WF123_ARC_CHAPTER_LINEAGE_INVALID")
    for field in ("origin_source_sha256","origin_quote_sha256",
                  "last_chapter_prose_sha256"):
        _need(type(value.get(field)) is str and SHA.fullmatch(value[field]),
              "WF123_ARC_SOURCE_HASH_INVALID")
    _need(value.get("parent_arc_sha256") is None or
          (type(value["parent_arc_sha256"]) is str and
           SHA.fullmatch(value["parent_arc_sha256"])),
          "WF123_ARC_PARENT_HASH_INVALID")
    _need((value["last_chapter"]==value["origin_chapter"]
           and value["parent_arc_sha256"] is None) or
          (value["last_chapter"]>value["origin_chapter"]
           and value["parent_arc_sha256"] is not None),
          "WF123_ARC_PARENT_SEQUENCE_INVALID")
    _need(type(value.get("last_settlement_claim_prose_sha256")) in
          (str,type(None)), "WF123_LAST_CLAIM_HASH_TYPE")
    if value["last_settlement_claim_prose_sha256"] is not None:
        _need(SHA.fullmatch(value["last_settlement_claim_prose_sha256"]),
              "WF123_LAST_CLAIM_HASH_INVALID")
    _need(value.get("no_model_statement_as_fact") is True and
          value.get("source_quote_not_stored") is True and
          type(value.get("receipt_sha256")) is str and
          SHA.fullmatch(value["receipt_sha256"]) and
          value["receipt_sha256"]==_digest({
              k:v for k,v in value.items() if k!="receipt_sha256"}) and
          len(json.dumps(value,ensure_ascii=False).encode("utf8"))
              <=MAX_CHECKPOINT_BYTES,
          "WF123_ARC_RECEIPT_TAMPERED_OR_UNBOUNDED")
    return value


def register_revenge(*,project_id:str,scene_id:str,
                     origin_chapter:int,source_prose:str,source_quote:str,
                     arc_id:str,actor:str,target:str,motive:str,
                     truth_scope:str,author_confirmed:bool) -> dict:
    """Only explicit author-confirmed prior manuscript can register an arc.

    CHARACTER_BELIEF is essential when the target may be wrongly accused:
    the model may not promote a character's belief to objective truth.
    """
    _need(author_confirmed is True,
          "WF123_AUTHOR_REVIEW_REQUIRED_FOR_LONG_ARC")
    _need(type(project_id) is str and 1<=len(project_id)<=128 and
          type(scene_id) is str and 1<=len(scene_id)<=128 and
          type(origin_chapter) is int and
          0<=origin_chapter<=MAX_CHAPTER and
          type(source_prose) is str and
          1<=len(source_prose)<=MAX_PROSE and
          type(source_quote) is str and 6<=len(source_quote)<=150
          and source_prose.count(source_quote)==1,
          "WF123_ARC_SOURCE_NOT_UNIQUE_OR_BOUNDED")
    start=source_prose.index(source_quote)
    _need(_present(source_prose,start,start+len(source_quote))
          or truth_scope=="CHARACTER_BELIEF",
          "WF123_ASSERTED_FACT_MUST_BE_NARRATED")
    _need(type(actor) is str and actor in source_quote and
          type(target) is str and target in source_quote,
          "WF123_ORIGIN_QUOTE_DOES_NOT_BIND_BOTH_CHARACTERS")
    row={
        "format":FMT,"project_id":project_id,"scene_id":scene_id,
        "arc_id":arc_id,"kind":"REVENGE",
        "actor":actor,"target":target,"motive":motive,
        "truth_scope":truth_scope,
        "status":"OPEN_AUTHOR_CONFIRMED",
        "author_confirmed":True,
        "author_confirmation_is_not_semantic_proof":True,
        "origin_chapter":origin_chapter,
        "last_chapter":origin_chapter,
        "chapter_advances":0,
        "origin_source_sha256":_digest(source_prose),
        "origin_quote_sha256":_digest(source_quote),
        "last_chapter_prose_sha256":_digest(source_prose),
        "last_settlement_claim_prose_sha256":None,
        "settlement_claim_count":0,
        "parent_arc_sha256":None,
        "automatic_resolution_count":0,
        "no_model_statement_as_fact":True,
        "source_quote_not_stored":True,
        "model_calls":0,"canon_writes":0,
    }
    row["receipt_sha256"]=_digest(row)
    return _validate(row,project_id=project_id,scene_id=scene_id)


def _find_claims(prose,actor):
    """Source-anchored narrator assertions only; not proof of an outcome."""
    result=[]
    for start,end,clause,is_dialogue in _segments(prose):
        if is_dialogue or not _present(prose,start,end):
            continue
        if any(word in clause for word in UNREAL):
            continue
        m=CLOSE.search(clause)
        if not m:
            continue
        if actor not in clause:
            result.append("WF123_REVENGE_CLAIM_ACTOR_UNRESOLVED")
        else:
            result.append("WF123_REVENGE_CLOSURE_CLAIM_NEEDS_AUTHOR_REVIEW")
    return list(dict.fromkeys(result))


def audit_revenge_prose(arc,*,project_id:str,scene_id:str,prose:str) -> dict:
    _validate(arc,project_id=project_id,scene_id=scene_id)
    _need(type(prose) is str and 1<=len(prose)<=MAX_PROSE,
          "WF123_AUDIT_PROSE_BOUNDS")
    warnings=_find_claims(prose,arc["actor"])
    return {
        "format":"wf.writing.v123.arc-statement-preflight",
        "arc_checkpoint_sha256":arc["receipt_sha256"],
        "prose_sha256":_digest(prose),
        "review_findings":warnings,
        "needs_review":bool(warnings),
        "blocked":False,
        "automatic_settlement_allowed":False,
        "text_does_not_update_author_confirmed_goal":True,
        "model_claim_does_not_close_revenge":True,
        "story_goal_literary_semantics_proven":False,
        "model_calls":0,"canon_writes":0,
    }


def advance_open_revenge(arc,*,project_id:str,scene_id:str,
                        chapter_index:int,prose:str) -> dict:
    """Return new immutable hashed candidate arc checkpoint for one chapter."""
    _validate(arc,project_id=project_id,scene_id=scene_id)
    _need(type(chapter_index) is int and
          chapter_index==arc["last_chapter"]+1 and
          chapter_index<=MAX_CHAPTER,
          "WF123_CHAPTER_GAP_REPLAY_OR_WRONG_ORDER")
    report=audit_revenge_prose(
        arc,project_id=project_id,scene_id=scene_id,prose=prose)
    new_count=arc["settlement_claim_count"]+int(report["needs_review"])
    _need(new_count<=MAX_CLAIMS,
          "WF123_REVENGE_REVIEW_QUOTA_REFUSE_FORGET")
    row={k:v for k,v in arc.items() if k!="receipt_sha256"}
    row.update({
        "last_chapter":chapter_index,
        "chapter_advances":arc["chapter_advances"]+1,
        "last_chapter_prose_sha256":_digest(prose),
        "parent_arc_sha256":arc["receipt_sha256"],
        "settlement_claim_count":new_count,
        "last_settlement_claim_prose_sha256":(
            _digest(prose) if report["needs_review"]
            else arc["last_settlement_claim_prose_sha256"]),
    })
    row["receipt_sha256"]=_digest(row)
    return _validate(row,project_id=project_id,scene_id=scene_id)


def relevant_revenge_hint(arc,*,project_id:str,scene_id:str,
                          beat:dict|None=None,goal:str|None=None) -> str:
    """A 20-chapter-old confirmed open goal resurfaces ONLY if relevant."""
    _validate(arc,project_id=project_id,scene_id=scene_id)
    if beat is not None:
        _need(type(beat) is dict and type(beat.get("goal")) is str
              and type(beat.get("kind")) is str,
              "WF123_LAMP_BEAT_INVALID")
        if beat["kind"] in ("quiet","transition","setup"):
            return ""
        goal=beat["goal"]
    _need(type(goal) is str and len(goal)<=600,
          "WF123_LAMP_GOAL_INVALID")
    if arc["target"] not in goal and not (
        arc["actor"] in goal and any(w in goal for w in TRIGGERS)):
        return ""
    policy=("作者确认的故事前提" if arc["truth_scope"]=="AUTHOR_ASSERTED"
            else "人物当前信念，真相尚未得到确证")
    msg=(
        "【长期人物目标·仅在相关场景提示】"
        f"{policy}：{arc['actor']}因「{arc['motive']}」"
        f"将{arc['target']}视为复仇对象；"
        f"截至第{arc['last_chapter']}章，旧目标仍是OPEN、尚未由作者确认结束。"
        "人物可以迟疑、求证、和解或改变方向；"
        "但不能仅凭下一段的模型解释把复仇目标当作已完成，"
        "转折需有实际情节及作者复核。")
    _need(len(msg)<=420,"WF123_ARC_CONTEXT_TOO_LONG")
    return msg


def read_long_arc_from_resume(resume,*,project_id,scene_id):
    """Verify V117 parent receipt first, then separately verify V123 lineage."""
    from .v117_continuity_trace import read_resume
    read_resume(resume,project_id=project_id,scene_id=scene_id)
    arc=resume.get("v123_open_character_arc")
    if arc is None:
        return None
    _validate(arc,project_id=project_id,scene_id=scene_id)
    _need(arc["last_chapter"]==resume["chapter_index"],
          "WF123_RESUME_CHAPTER_BINDING_INVALID")
    return arc


def verify_long_arc(value,*,project_id,scene_id):
    """Verify a caller-supplied checkpoint before a new generation call."""
    return _validate(value,project_id=project_id,scene_id=scene_id)
