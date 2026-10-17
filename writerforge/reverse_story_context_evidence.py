"""Context-scoped, score-grounded candidate evidence for original story topics.

A positive/negative A/B observation is never an auto-promoted craft rule. A
single negative scenario must NOT delete a mechanism that helped in two others.
Only source and story task hashes, host-owned technique IDs and numeric model
observations are retained. No original or generated novel prose survives.
"""
from __future__ import annotations
from hashlib import sha256
import json,re

from .random_original_openings import sample_manifest,selected_ids,sample_sha256
from .reverse_mechanism_boundary import TECHNIQUES

class StoryContextEvidenceError(ValueError):
    pass

def _canonical(item):
    return json.dumps(item,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf-8")

def derive_story_context_candidates(report:dict,*,report_sha256:str)->dict:
    if (not isinstance(report,dict) or not isinstance(report_sha256,str)
        or not re.fullmatch(r"[0-9a-f]{64}",report_sha256)
        or sha256(_canonical(report)).hexdigest()!=report_sha256):
        raise StoryContextEvidenceError("UNVERIFIED_AGGREGATE_DIGEST")
    if (report.get("format")!="writerforge.three-random-original-openings.audit.v1"
        or report.get("count_scored")!=3 or report.get("all_three_scored") is not True
        or report.get("sample_sha256")!=sample_sha256()
        or report.get("selected_scenarios")!=list(selected_ids())
        or report.get("source_window_sha256")!=
            "96b6363d40be7b99d5635af1346da0c04e44556fc06e32d1aab04e419e4942fa"
        or report.get("first_window")!="NOT_PASSED"
        or report.get("second_window")!="LOCKED"
        or report.get("core_promoted") is not False
        or report.get("literary_mastery_verified") is not False):
        raise StoryContextEvidenceError("INVALID_THREE_STORY_PROVENANCE")
    rows=report.get("results")
    if not isinstance(rows,list) or len(rows)!=3:
        raise StoryContextEvidenceError("MISSING_THREE_TRUE_RESULTS")
    manifest=sample_manifest()
    dimensions=("perception","causality","information","continuity","language")
    candidates=[]
    for index,row in enumerate(rows):
        if (not isinstance(row,dict) or row.get("slot")!=index
            or row.get("story_id")!=manifest["selected_ids"][index]
            or row.get("status")!="REAL_AB_R2_VERIFIED"):
            raise StoryContextEvidenceError("MISMATCHED_STORY_SLOT")
        item=row.get("dimension_deltas")
        if not isinstance(item,dict) or set(item)!=set(dimensions):
            raise StoryContextEvidenceError("MISSING_LITERARY_DIMENSIONS")
        delta=row.get("raw_effect")
        if type(delta) not in (int,float) or any(
            type(item[k]) is not int for k in dimensions):
            raise StoryContextEvidenceError("INVALID_MODEL_SCORES")
        if abs(sum(item.values())/5-delta)>0.00001:
            raise StoryContextEvidenceError("DIMENSION_DELTA_MISMATCH")
        pair=row.get("mechanisms_unreviewed")
        if (not isinstance(pair,list) or not 1<=len(pair)<=2
            or len(set(pair))!=len(pair)
            or any(not isinstance(x,str) or x not in TECHNIQUES for x in pair)):
            raise StoryContextEvidenceError("MECHANISM_OUTSIDE_HOST_REGISTRY")
        sha=row.get("receipt_sha256")
        if not isinstance(sha,str) or not re.fullmatch(r"[0-9a-f]{64}",sha):
            raise StoryContextEvidenceError("MISSING_IMMUTABLE_ORIGINAL_RECEIPT")
        status=("NEGATIVE_ALL_FIVE_NEEDS_INDEPENDENT_REVIEW"
                if delta<0 and all(n<0 for n in item.values())
                else "MODEL_POSITIVE_UNVERIFIED" if delta>0
                else "MIXED_OR_ZERO_UNVERIFIED")
        candidates.append({
            "story_id":row["story_id"],"writing_task_base_sha256":
                manifest["selected_task_sha256"][index],
            "source_unit_sha256":report["source_window_sha256"],
            "raw_receipt_sha256":sha,
            "mechanism_pair_unreviewed":sorted(pair),
            "model_effect":delta,"dimension_deltas":{k:item[k] for k in dimensions},
            "candidate_status":status,
            "human_review":False,
            "forbid_global_skill_deletion":True,
            "auto_apply_as_skill":False,
        })
    pattern={tuple(row["mechanism_pair_unreviewed"]) for row in candidates}
    result={
        "format":"writerforge.original-story-context-evidence.v1",
        "aggregate_sha256":report_sha256,
        "source_unit_sha256":report["source_window_sha256"],
        "model_only_contextual_observations":candidates,
        "same_mechanism_pair_all_three":len(pattern)==1,
        "positive_and_negative_same_pair":(
            len(pattern)==1 and any(x["model_effect"]<0 for x in candidates)
            and any(x["model_effect"]>0 for x in candidates)),
        "model_judgment_not_causal_proof":True,
        "disable_global_mechanisms":False,
        "automatic_skill_promotion":False,
        "first_window":"NOT_PASSED","second_window":"LOCKED",
    }
    if len(_canonical(result))>8000:
        raise StoryContextEvidenceError("UNBOUNDED_CANDIDATE_METADATA")
    return result
