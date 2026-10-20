"""V88 forensic diagnostic of private WF anchor coordinates (NO repair/write).

This is a reader-only classification tool for the four real saved answers.
It NEVER emits original prose, model answers or private excerpt strings.
It checks whether the model selected an actual short passage but guessed the
wrong integer offsets. A host-located quote is only SOURCE existence,
not a verified semantic cause or a positive literary grade.
"""
from __future__ import annotations
from copy import deepcopy

from .v88_frozen_blind_exam import (
    validate_wf_answer,WF88BlindError,ANCHOR_KEYS,
    MIN_TEXT,MAX_QUOTE,ANSWER_KEYS,
)

def one_anchor(anchor,units):
    report={
        "anchor_object_format":False,
        "unit_is_visible":False,
        "quote_length_allowed":False,
        "literal_quote_occurs_in_claimed_unit":False,
        "quote_occurrence_count_clamped_to_two":0,
        "numerical_offsets_exact":False,
        "unique_quote_host_location_possible":False,
        "model_quote_or_source_text_exposed":False,
    }
    if not isinstance(anchor,dict) or set(anchor)!=ANCHOR_KEYS:
        return report,None
    report["anchor_object_format"]=True
    unit=anchor.get("unit")
    if type(unit) is not int or unit not in (1,2):
        return report,None
    report["unit_is_visible"]=True
    quote=anchor.get("quote")
    if not isinstance(quote,str):
        return report,None
    report["quote_length_allowed"]=MIN_TEXT<=len(quote)<=MAX_QUOTE
    if not report["quote_length_allowed"]:
        return report,None
    source=units[unit-1]
    occur=source.count(quote)
    report["literal_quote_occurs_in_claimed_unit"]=occur>0
    report["quote_occurrence_count_clamped_to_two"]=min(occur,2)
    start,end=anchor.get("start"),anchor.get("end")
    if type(start) is int and type(end) is int:
        report["numerical_offsets_exact"]=(
            0<=start<end<=len(source) and source[start:end]==quote
            and end-start==len(quote))
    if occur!=1:
        return report,None
    right=source.find(quote)
    report["unique_quote_host_location_possible"]=True
    return report,{
        "unit":unit,"start":right,"end":right+len(quote),
        "quote":quote,
    }

def diagnose(answer,*,visible_units):
    if not isinstance(answer,dict) or not isinstance(visible_units,tuple) or (
         len(visible_units)!=2):
        return {"status":"NON_DIAGNOSABLE_RESPONSE",
                "no_private_text_emitted":True,
                "literary_truth_reviewed":False}
    observations={}
    replacements={}
    for field in ("observation","consequence"):
        observations[field], replacements[field]=one_anchor(
            answer.get(field),visible_units)
    possible=all(replacements.values())
    candidate=deepcopy(answer)
    if possible:
        for field in ("observation","consequence"):
            candidate[field]=replacements[field]
    independent_schema_after_host_offset_change=False
    remaining_error=None
    if possible and set(candidate)==ANSWER_KEYS:
        try:
            validate_wf_answer(candidate,visible_units=visible_units)
            independent_schema_after_host_offset_change=True
        except WF88BlindError as exc:
            remaining_error=str(exc)
    return {
        "status":"PRIVATE_SOURCE_LOCATION_DIAGNOSTICS_ONLY",
        "model_answer_status":answer.get("status") if
             answer.get("status") in ("HYPOTHESIS","ABSTAIN") else "OTHER",
        "claimed_anchor_diagnostics":observations,
        "both_quotes_have_unique_exact_source_occurrence":possible,
        "full_schema_passes_if_ONLY_coordinates_host_computed":
            independent_schema_after_host_offset_change,
        "remaining_failure_code_after_pure_coordinate_rebase":
            remaining_error,
        "would_be_correct_to_change_historical_raw_answer":False,
        "private_source_or_model_text_emitted":False,
        "literary_causality_semantically_verified":False,
    }
