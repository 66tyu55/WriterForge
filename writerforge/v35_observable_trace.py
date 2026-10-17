"""V35 observable literary *decision records*, not hidden model chain of thought.

WF deliberately writes bounded pre-commit choices, alternatives, and evidence
before drafting. The returned records are explicit model outputs, NEVER
assumed to be a full transcript of unobservable internal reasoning.
"""
from __future__ import annotations
import json,re
from hashlib import sha256
from .v35_xiyouji_exam import task

ANGLES={"goal","knowledge","causality","scene","sensory","dialogue",
        "foreshadowing","emotion"}
class TraceContractError(ValueError):pass

def sha(value:str|bytes)->str:
    return sha256(value.encode("utf-8") if isinstance(value,str) else value).hexdigest()

def canonical(value)->bytes:
    return json.dumps(value,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf-8")

def _note(x,lo=12,hi=230):
    return isinstance(x,str) and lo<=len(x.strip())<=hi

def _compact(x):
    return "".join(x.split())

def validate_read(response:dict,windows:dict)->dict:
    if not isinstance(response,dict) or set(response)!={"observations"}:
        raise TraceContractError("READ_NOT_STRUCTURED")
    rows=response["observations"]
    if not isinstance(rows,list) or not 2<=len(rows)<=4:
        raise TraceContractError("READ_COUNT_INVALID")
    seen=set();valid=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!={
            "chapter","source_quote","narrative_function","character_knowledge",
            "possible_alternative_reading"}:
            raise TraceContractError("READ_FIELDS_INVALID")
        ch=row["chapter"];q=row["source_quote"]
        if (type(ch) is not int or ch not in (1,2) or
            not isinstance(q,str) or not 8<=len(_compact(q))<=55 or
            _compact(q) not in _compact(windows[ch])):
            raise TraceContractError("READ_QUOTED_TEXT_NOT_FOUND")
        if any(not _note(row[k],14,240) for k in (
            "narrative_function","character_knowledge",
            "possible_alternative_reading")):
            raise TraceContractError("READ_EXPLANATION_INVALID")
        valid.append(row);seen.add(ch)
    if seen!={1,2}:
        raise TraceContractError("READ_DID_NOT_OBSERVE_BOTH_CHAPTERS")
    return {"observations":valid,"exact_source_quotes_verified":True,
            "source_seen_by_reader_not_writer":True,
            "independent_semantic_correctness_verified":False}

def validate_lessons(resp:dict,n_observations:int)->dict:
    if not isinstance(resp,dict) or set(resp)!={"lessons"}:
        raise TraceContractError("LESSON_SCHEMA_INVALID")
    lessons=resp["lessons"]
    if not isinstance(lessons,list) or not 1<=len(lessons)<=2:
        raise TraceContractError("LESSON_COUNT_INVALID")
    out=[]
    for i,row in enumerate(lessons):
        if not isinstance(row,dict) or set(row)!={
            "source_observation_index","technique","why",
            "use_when","avoid_when","verification_question"}:
            raise TraceContractError("LESSON_FIELDS_INVALID")
        if (type(row["source_observation_index"]) is not int or
            not 0<=row["source_observation_index"]<n_observations):
            raise TraceContractError("LESSON_SOURCE_LINK_INVALID")
        if any(not _note(row[k],12,230) for k in (
            "technique","why","use_when","avoid_when","verification_question")):
            raise TraceContractError("LESSON_EXPLANATION_UNBOUNDED")
        out.append({"id":f"L{i+1}",**row})
    return {"lessons":out,"human_reviewed":False,
            "eligible_for_official_skill":False}

def validate_plan(response:dict,available_lesson_ids:set[str])->dict:
    if not isinstance(response,dict) or set(response)!={"decisions"}:
        raise TraceContractError("PREWRITE_SCHEMA_INVALID")
    choices=response["decisions"]
    if not isinstance(choices,list) or not 4<=len(choices)<=7:
        raise TraceContractError("PREWRITE_DECISION_COUNT_INVALID")
    angles=set();out=[]
    for item in choices:
        if (not isinstance(item,dict) or set(item)!={
            "angle","chosen_approach","reason","rejected_alternative",
            "expected_story_effect","learned_lesson_id"}):
            raise TraceContractError("PREWRITE_FIELDS_INVALID")
        angle=item["angle"]
        if angle not in ANGLES or angle in angles:
            raise TraceContractError("PREWRITE_UNKNOWN_OR_REPEATED_ANGLE")
        angles.add(angle)
        if item["learned_lesson_id"] not in available_lesson_ids|{"NONE"}:
            raise TraceContractError("PREWRITE_UNKNOWN_LEARNED_LESSON")
        if any(not _note(item[k],12,235) for k in (
            "chosen_approach","reason","rejected_alternative",
            "expected_story_effect")):
            raise TraceContractError("PREWRITE_DECISION_REASONS_INVALID")
        out.append(item)
    if not {"goal","knowledge","causality"}.issubset(angles):
        raise TraceContractError("PREWRITE_CORE_CAUSAL_ANGLES_MISSING")
    return {"decisions":out,
            "decisions_written_before_first_draft":True,
            "hidden_model_thought_not_available":True}

def validate_draft(text:str, source_windows:dict)->dict:
    if not isinstance(text,str) or not 350<=len(text)<=4500:
        raise TraceContractError("DRAFT_OUTSIDE_SAFE_BOUNDS")
    # Source and draft long exact-copy guard, ignoring line-wrap differences.
    normalized=_compact(text)
    for win in source_windows.values():
        original=_compact(win)
        for i in range(0,max(0,len(original)-23)):
            if original[i:i+24] in normalized:
                raise TraceContractError("ORIGINAL_TEXT_COPIED_INTO_NEW_DRAFT")
    return {"body":text,"body_sha256":sha(text),
            "characters_including_punctuation":len(text),
            "target":1120,"hard_minimum":950,"hard_maximum":1300,
            "within_absolute_length_bounds":950<=len(text)<=1300}

def validate_after(response:dict,draft:str,plan:dict)->dict:
    if not isinstance(response,dict) or set(response)!={"checks","biggest_mistake"}:
        raise TraceContractError("RETROSPECT_SCHEMA_INVALID")
    records=response["checks"]
    if not isinstance(records,list) or not 2<=len(records)<=5:
        raise TraceContractError("RETROSPECT_COUNT_INVALID")
    angles={x["angle"] for x in plan["decisions"]}
    outputs=[]
    for r in records:
        if not isinstance(r,dict) or set(r)!={
            "angle","actual_draft_quote","followed_prewrite_plan",
            "observed_gap","possible_next_revision"}:
            raise TraceContractError("RETROSPECT_FIELDS_INVALID")
        if r["angle"] not in angles or type(r["followed_prewrite_plan"]) is not bool:
            raise TraceContractError("RETROSPECT_NO_PREPLAN_ANGLE")
        q=r["actual_draft_quote"]
        if (not isinstance(q,str) or not 8<=len(_compact(q))<=65 or
            _compact(q) not in _compact(draft)):
            raise TraceContractError("RETROSPECT_QUOTE_NOT_IN_DRAFT")
        if any(not _note(r[k],12,250) for k in (
            "observed_gap","possible_next_revision")):
            raise TraceContractError("RETROSPECT_NOT_EXPLANATORY")
        outputs.append(r)
    if not _note(response["biggest_mistake"],14,280):
        raise TraceContractError("RETROSPECT_FAILURE_NOT_NAMED")
    return {"checks":outputs,
            "biggest_mistake":response["biggest_mistake"],
            "not_allowed_to_rewrite_frozen_preplan":True,
            "self_assessment_not_independent":True}
