"""V99 independent-evidence-ready longform narrative logic audit (NO LLM judge).

A hard consistency error must be anchored to an actual excerpt and carry
two traceable positions: an earlier established fact + later contradiction.
An ungrounded evaluator assertion is UNKNOWN, not a failure. Literary style,
motivation and subtle causality always require an independent semantic judge.
Neither model/self-review nor a good character count can graduate WF skill.

This module is deliberately pure/side-effect free and can audit V97/V98
unaccepted manuscripts without mutating their R2 CAS or FactJournal state.
"""
from __future__ import annotations
from hashlib import sha256
import json

LENGTHS=(800,1500,1600,3200,6400)  # 1500 is V97's immutable original target
ARMS=("single","split_only","causal_guard","rolling_causal")
CATEGORIES=frozenset(("causality","character_knowledge","chronology",
                       "world_rule","identity","physical_state"))
MAX_PROSE_CHARS=12000
MAX_ANNOTATIONS=64
MAX_WITNESS=160


class V99EvidenceError(ValueError):
    pass


def need(condition,reason):
    if not condition: raise V99EvidenceError(reason)


def canonical(o):
    return json.dumps(o,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")


def digest(raw):
    return sha256(raw).hexdigest()


def _safe(s,minimum=1,maximum=MAX_WITNESS):
    if not isinstance(s,str) or not minimum<=len(s)<=maximum or (
            "\ufffd" in s or "\x00" in s):
        return False
    try: return s.encode("utf8","strict").decode("utf8","strict")==s
    except UnicodeError: return False


def _unique_position(prose,quote):
    need(_safe(quote,6,MAX_WITNESS),
         "WF99_WITNESS_INVALID_OR_GARBLED")
    first=prose.find(quote)
    need(first>=0,"WF99_WITNESS_NOT_IN_ACTUAL_PROSE")
    need(prose.find(quote,first+1)==-1,
         "WF99_WITNESS_NOT_UNIQUE_IN_ACTUAL_PROSE")
    return {"start":first,"end":first+len(quote),
            "quote_sha256":digest(quote.encode("utf8"))}


def freeze_manuscript(*,prose,arm,case_id,requested_chars):
    need(type(prose) is str and 80<=len(prose)<=MAX_PROSE_CHARS and
         _safe(prose,80,MAX_PROSE_CHARS) and arm in ARMS and
         _safe(case_id,4,90) and requested_chars in LENGTHS,
         "WF99_MANUSCRIPT_INPUT_OR_LENGTH_INVALID")
    # Counts Unicode codepoints including Chinese punctuation; not tokens
    # and not a claim that the story fits exactly its requested length.
    return {
        "format":"wf.writing.longform-frozen-sample.v99",
        "case_id":case_id,"arm":arm,
        "requested_characters_including_punctuation":requested_chars,
        "actual_characters_including_punctuation":len(prose),
        "prose_sha256":digest(prose.encode("utf8")),
        "review_status":"UNREVIEWED",
        "model_or_human_truth_verified":False,
        "original_prose_not_embedded":True,
    }


def evidence_annotation(*,prose,frozen,category,
                        established_quote,contradicting_quote,
                        reporter_kind="UNVERIFIED_REPORTER"):
    """Citation validity only. Does NOT establish a logical contradiction."""
    need(type(frozen) is dict and
         frozen.get("prose_sha256")==digest(prose.encode("utf8")) and
         frozen.get("actual_characters_including_punctuation")==len(prose),
         "WF99_FROZEN_MANUSCRIPT_CHANGED")
    need(category in CATEGORIES and
         reporter_kind in ("UNVERIFIED_REPORTER",
                           "INDEPENDENT_HUMAN_PENDING_CONFIRMATION"),
         "WF99_CATEGORY_OR_REVIEWER_AUTH_INVALID")
    previous=_unique_position(prose,established_quote)
    later=_unique_position(prose,contradicting_quote)
    need(previous["end"]<=later["start"],
         "WF99_EVIDENCE_NOT_ORDERED")
    row={
        "category":category,"earlier_witness":previous,
        "later_witness":later,
        "reporter_kind":reporter_kind,
        "semantic_conflict_proven":False,
        "first_failure_character_offset_verified":False,
        "may_change_writing_skill":False,
        "text_not_embedded":True,
    }
    row["annotation_sha256"]=digest(canonical(row))
    return row


def audit_unverified_claims(*,frozen,annotations):
    """Error locations and counts are NOT graded until independently reviewed."""
    need(type(annotations) in (tuple,list) and
         len(annotations)<=MAX_ANNOTATIONS,
         "WF99_ANNOTATION_COUNT_OVER_BUDGET")
    for row in annotations:
        need(isinstance(row,dict) and
             row.get("category") in CATEGORIES and
             row.get("semantic_conflict_proven") is False and
             row.get("first_failure_character_offset_verified") is False and
             row.get("may_change_writing_skill") is False and
             row.get("annotation_sha256")==digest(canonical({
                 k:v for k,v in row.items() if k!="annotation_sha256"})),
             "WF99_UNTRUSTED_ASSERTED_GRADE")
    need(type(frozen) is dict and
         frozen.get("format")=="wf.writing.longform-frozen-sample.v99",
         "WF99_NOT_A_FROZEN_CANDIDATE")
    return {
        "format":"wf.writing.longform-evidence-audit.v99",
        "case_id":frozen["case_id"],"arm":frozen["arm"],
        "actual_characters":frozen[
            "actual_characters_including_punctuation"],
        "candidate_observations":len(annotations),
        "verified_hard_contradictions":None,
        "first_verified_logic_failure_character":None,
        "errors_per_1000_characters":None,
        "literary_quality_winner":"UNDETERMINED",
        "independent_semantic_review_completed":False,
        "no_skill_graduation_or_canonical_fact_write":True,
        "source_prose_not_in_report":True,
    }


def compare_equal_length(*,samples,max_relative_gap=0.10):
    """Preflight FAIR A/B/C/D length, no simulated literature scores."""
    need(type(samples) in (list,tuple) and len(samples)>=2 and
         len(samples)<=4,"WF99_COMPARISON_ARMS_INVALID")
    arms=[x.get("arm") for x in samples]
    sizes=[x.get("actual_characters_including_punctuation") for x in samples]
    requested=[x.get("requested_characters_including_punctuation") for x in samples]
    need(len(set(arms))==len(arms) and
         all(x in ARMS for x in arms) and
         len(set(requested))==1 and
         all(type(s) is int and s>=80 for s in sizes),
         "WF99_ARMS_OR_LENGTH_TARGET_NOT_COMPARABLE")
    spread=(max(sizes)-min(sizes))/max(sizes)
    return {
        "format":"wf.writing.longform-length-fairness.v99",
        "requested_characters":requested[0],
        "actual_lengths":dict(zip(arms,sizes)),
        "relative_length_gap":round(spread,5),
        "lengths_comparable":spread<=max_relative_gap,
        "literary_winner":"UNDETERMINED",
        "independent_semantic_review_completed":False,
    }
