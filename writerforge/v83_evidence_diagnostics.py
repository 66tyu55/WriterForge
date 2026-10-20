"""V84 source-aware, model-free diagnostics for private V81 answer pairs.

Only publish aggregate numeric indicators. Lexical overlap with the two
actually read source units is a diagnostic, NOT proof of a valid literary
interpretation. Never return source phrases or the model's prose.
"""
from __future__ import annotations

from difflib import SequenceMatcher
import json
import re

FIELDS=("question","hypothesis","uncertainty","focus")
HAN=re.compile(r"[\u3400-\u9fff]+")
NUMBERS=re.compile(r"(?<!\d)\d+(?!\d)")


def _grams(text: str, width: int) -> set[str]:
    out=set()
    for chunk in HAN.findall(text):
        if len(chunk)>=width:
            out.update(chunk[i:i+width] for i in range(len(chunk)-width+1))
    return out


def _longest_shared(text: str, source_units: tuple[str, str]) -> int:
    return max(SequenceMatcher(
        None,text,unit,autojunk=False
    ).find_longest_match(0,len(text),0,len(unit)).size for unit in source_units)


def diagnostics(answer: dict, *, source_units: tuple[str, str]) -> dict:
    """Never emits answer text, source text, candidate terms, or entity names."""
    if (not isinstance(answer,dict) or
        any(not isinstance(answer.get(f),str) for f in FIELDS) or
        not isinstance(source_units,tuple) or len(source_units)!=2 or
        any(not isinstance(x,str) or not x for x in source_units)):
        raise ValueError("WF_V84_AUDIT_INVALID_PRIVATE_INPUT")
    combined="".join(source_units)
    source3=_grams(combined,3)
    source4=_grams(combined,4)
    source_numbers=set(NUMBERS.findall(combined))
    per_field={}
    for field in FIELDS:
        value=answer[field]
        three=_grams(value,3)
        four=_grams(value,4)
        new_numeric=set(NUMBERS.findall(value))-source_numbers
        per_field[field]={
            "characters":len(value),
            "source_3gram_hits":len(three & source3),
            "distinct_3grams":len(three),
            "source_3gram_overlap_pct":round(
                100*len(three & source3)/len(three),1) if three else None,
            "source_4gram_hits":len(four & source4),
            "distinct_4grams":len(four),
            "longest_verbatim_source_match_characters":
                _longest_shared(value,source_units),
            "numerals_not_present_in_two_read_units":len(new_numeric),
        }
    refs=answer.get("evidence_units")
    if not isinstance(refs,list) or any(
            type(x) is not int or x not in (1,2) for x in refs):
        raise ValueError("WF_V84_AUDIT_SOURCE_REFERENCES_INVALID")
    return {
        "fields":per_field,
        "source_units_declared":list(refs),
        "per_claim_exact_source_quote_offsets_available":False,
        "sentence_level_causal_grounding_adjudicated":False,
        "character_knowledge_state_adjudicated":False,
        "prediction_falsifiability_adjudicated":False,
        "uncertainty_literary_suitability_adjudicated":False,
        "quality_grade":None,
        "lexical_similarity_is_not_semantic_truth":True,
    }


def compare_diagnostics(baseline: dict, experience: dict,
                        baseline_answer: dict, experience_answer: dict) -> dict:
    if any(f not in baseline.get("fields",{}) or
           f not in experience.get("fields",{}) for f in FIELDS):
        raise ValueError("WF_V84_AUDIT_MISSING_METRIC_FIELDS")
    output={}
    for field in FIELDS:
        old=baseline["fields"][field]
        new=experience["fields"][field]
        a=old["source_3gram_overlap_pct"]
        b=new["source_3gram_overlap_pct"]
        output[field]={
            "baseline_source_3gram_overlap_pct":a,
            "experience_source_3gram_overlap_pct":b,
            "experience_minus_baseline_lexical_pct":
                round(b-a,1) if a is not None and b is not None else None,
            "between_arm_text_similarity_pct":round(
                100*SequenceMatcher(None,
                    baseline_answer[field],experience_answer[field],
                    autojunk=False).ratio(),1),
            "baseline_longest_verbatim_characters":
                old["longest_verbatim_source_match_characters"],
            "experience_longest_verbatim_characters":
                new["longest_verbatim_source_match_characters"],
        }
    return {
        "diagnostics_by_field":output,
        "comparison_is_one_pair_only":True,
        "source_overlap_can_reward_copying_or_penalize_paraphrase":True,
        "independent_literary_judgement_performed":False,
        "causal_effect_of_experience_identified":False,
        "promotion_allowed":False,
        "overall_quality_winner":"UNDETERMINED",
        "negative_examples_and_unknowns_must_be_preserved":True,
    }


def safe_json(doc: dict) -> str:
    return json.dumps(doc,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False)
