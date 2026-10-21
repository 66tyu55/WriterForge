"""V107 offline diagnostics of the ORIGINAL model's V96 two-beat JSON.

This is NEVER a validator replacement, retry request, AI editor, or literary
judge. It reports field-level reasons without changing or exposing text.
The authoritative V96 parser still decides acceptance, unchanged.
"""
from __future__ import annotations
from hashlib import sha256
import json
from .v96_causal_turns import (
    BEAT_FIELDS,KINDS,CAUSAL_KINDS,CRAFT,_text,parse_turn_outline,
    V96CausalDraftError,canonical,
)
MAX_FIELD_ERRORS=20


def _hash(v):
    try:
        return sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,
            separators=(",",":"),allow_nan=False).encode("utf8")).hexdigest()
    except (ValueError,TypeError,UnicodeError):
        return None


def observe_shared_two_turns(candidate):
    """Explain errors, keep original completely immutable and unaccepted."""
    deviations=[]
    def add(path,code,value=None):
        if len(deviations)<MAX_FIELD_ERRORS:
            deviations.append({
                "path":path,"failure_kind":code,
                "observed_type":type(value).__name__,
                "original_value_sha256":_hash(value),
            })
    if type(candidate) is not dict:
        add("$","ROOT_NOT_OBJECT",candidate)
    else:
        if set(candidate)!={"turns"}:
            add("$","TOP_FIELDS_NOT_EXACT",sorted(candidate))
        turns=candidate.get("turns")
        if type(turns) is not list or len(turns)!=2:
            add("turns","NOT_EXACT_TWO_TURNS",turns)
        if type(turns) is list:
            prev={}
            for i,beat in enumerate(turns[:3],1):
                origin=f"turns[{i-1}]"
                if type(beat) is not dict:
                    add(origin,"TURN_NOT_OBJECT",beat)
                    continue
                if set(beat)!=BEAT_FIELDS:
                    add(origin,"TURN_FIELDS_NOT_EXACT",sorted(beat))
                if beat.get("id")!=f"t{i:02d}":
                    add(origin+".id","ID_NOT_CANONICAL",beat.get("id"))
                kind=beat.get("kind")
                if type(kind) is not str or kind not in KINDS:
                    add(origin+".kind","INVALID_EVENT_KIND",kind)
                if not _text(beat.get("actor"),1,70):
                    add(origin+".actor","INVALID_ACTOR_NAME",beat.get("actor"))
                if not _text(beat.get("goal"),8,220):
                    add(origin+".goal","GOAL_LENGTH_OR_UNICODE",beat.get("goal"))
                craft=beat.get("craft_focus")
                if (type(craft) is not list or len(craft)>2 or
                        any(type(x) is not str or x not in CRAFT
                            for x in craft) or len(set(craft))!=len(craft)):
                    add(origin+".craft_focus","INVALID_CRAFT_FOCUS",craft)
                parent=beat.get("causal_parent")
                if parent is not None and (
                        type(parent) is not str or parent not in prev or
                        prev[parent] not in CAUSAL_KINDS):
                    add(origin+".causal_parent",
                        "PARENT_MISSING_NOT_PRIOR_ACTION",parent)
                if type(beat.get("id")) is str and type(kind) is str:
                    prev[beat["id"]]=kind
    try:
        parse_turn_outline(json.dumps(candidate,ensure_ascii=False,
                                      separators=(",",":"),allow_nan=False))
        v96_valid=True
    except (V96CausalDraftError,TypeError,ValueError,UnicodeError):
        v96_valid=False
    if v96_valid and type(candidate) is dict:
        turns=candidate.get("turns")
        if type(turns) is list and len(turns)!=2:
            add("turns","NOT_EXACT_TWO_TURNS",turns)
            v96_valid=False
    return {
        "format":"wf.exam.v107.unmodified-original-two-beat-diagnostic",
        "raw_decoded_model_json_sha256":_hash(candidate),
        "exact_v96_valid":v96_valid,
        "exact_two_turns_required":True,
        "violations":deviations,
        "no_student_fields_edited":True,
        "no_raw_novel_or_model_replies_in_receipt":True,
        "semantic_story_quality_checked":False,
        "model_calls_for_diagnostics":0,
        "auto_retry_permitted":False,
    }
