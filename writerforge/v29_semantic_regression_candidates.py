"""V29: strict SHA-based old-vs-semantic mechanism-change evidence.

Pure metadata; never invokes models, reads novel or retains manuscripts.
One topic's negative five-dimensional model result cannot globally erase
a skill mechanism. Likewise a positive result cannot auto-promote.

This is a diagnostic anti-regression ledger, NOT independent literary review.
"""
from __future__ import annotations
from hashlib import sha256
import json,re
from .v29_fresh_holdout import chosen_ids,manifest_sha
from .reverse_mechanism_boundary import TECHNIQUES

class SemanticRegressionEvidenceError(ValueError):
    pass

def canonical(doc)->bytes:
    return json.dumps(doc,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode("utf-8")

def candidate_from_audit(report:dict, *, report_sha256:str)->dict:
    if (not isinstance(report,dict) or
        not isinstance(report_sha256,str) or
        not re.fullmatch(r"[a-f0-9]{64}",report_sha256) or
        sha256(canonical(report)).hexdigest()!=report_sha256):
        raise SemanticRegressionEvidenceError("AUDIT_SHA_NOT_TRUSTED")
    if (report.get("format")!=
            "writerforge.v29-heldout-old-new-recovered-model-observation.v1" or
        report.get("valid_graded_scenarios")!=3 or
        report.get("manifest_sha256")!=manifest_sha() or
        report.get("selected_scenarios")!=list(chosen_ids()) or
        report.get("second_window")!="LOCKED" or
        report.get("core_promoted") is not False or
        report.get("causal_improvement_proven") is not False or
        report.get("mixed_length_protocol_between_slot0_and_recovery_slots") is not True):
        raise SemanticRegressionEvidenceError("MISSING_HOLDOUT_OR_HONEST_PROTOCOL")
    entries=[]
    observed=report.get("results")
    if not isinstance(observed,list) or len(observed)!=3:
        raise SemanticRegressionEvidenceError("MISSING_THREE_SOURCE_SLOTS")
    dims=("perception","causality","information","continuity","language")
    for slot,record in enumerate(observed):
        if (not isinstance(record,dict) or
            record.get("slot")!=slot or
            record.get("scenario")!=chosen_ids()[slot] or
            record.get("status")!="BLIND_OLD_NEW_R2_VERIFIED"):
            raise SemanticRegressionEvidenceError("FORGED_SCENARIO_IDENTITY")
        raw=record.get("per_dimension_new_minus_old")
        old=record.get("mechanisms_old")
        new=record.get("mechanisms_new")
        if (not isinstance(raw,dict) or set(raw)!=set(dims)
            or any(type(raw[d]) is not int or not -100<=raw[d]<=100 for d in dims)
            or not isinstance(old,list) or not isinstance(new,list)
            or not 1<=len(old)<=2 or not 1<=len(new)<=2
            or any(n not in TECHNIQUES for n in old+new)
            or len(set(old))!=len(old) or len(set(new))!=len(new)):
            raise SemanticRegressionEvidenceError("INVALID_MODEL_OR_HOST_DIMENSIONS")
        delta=record.get("delta")
        if (type(delta) not in (int,float) or
            abs(sum(raw.values())/5-delta)>1e-6 or
            abs(record["new_score"]-record["old_score"]-delta)>1e-6):
            raise SemanticRegressionEvidenceError("FALSE_A_B_DELTA")
        h=record.get("receipt_sha256")
        if not isinstance(h,str) or not re.fullmatch(r"[a-f0-9]{64}",h):
            raise SemanticRegressionEvidenceError("MISSING_TRUE_RECEIPT")
        status=("TASK_SCOPED_ALL_FIVE_REGRESSION_CANDIDATE"
            if all(raw[d]<0 for d in dims)
            else "POSITIVE_BUT_SAME_MECHANISMS_NOT_CAUSAL"
            if delta>0 and set(old)==set(new)
            else "POSITIVE_CHANGED_MECHANISMS_UNVERIFIED"
            if delta>0 else "MIXED_OR_UNKNOWN_MODEL_EVIDENCE")
        entries.append({
            "slot":slot,"scenario":record["scenario"],
            "receipt_sha256":h,
            "task_sha256_from_manifest_position":slot,
            "old_mechanisms":sorted(old),
            "semantic_mechanisms":sorted(new),
            "semantic_changed_operations":set(old)!=set(new),
            "model_effect_new_minus_old":delta,
            "dimension_deltas":{d:raw[d] for d in dims},
            "candidate_status":status,
            "human_independent_review":False,
            "generalize_to_other_contexts":False,
        })
    result={
        "format":"writerforge.v29-semantic-change-regression-candidates.v1",
        "source_audit_sha256":report_sha256,
        "source_manifest_sha256":manifest_sha(),
        "observations":entries,
        "any_five_dimension_regression":any(
            x["candidate_status"]=="TASK_SCOPED_ALL_FIVE_REGRESSION_CANDIDATE"
            for x in entries),
        "all_three_same_protocol":False,
        "stable_literary_improvement_proven":False,
        "allow_core_promotion":False,
        "allow_global_mechanism_deletion":False,
        "first_window":"NOT_PASSED","second_window":"LOCKED",
    }
    if len(canonical(result))>10000:
        raise SemanticRegressionEvidenceError("OVERSIZED_REGRESSION_EVIDENCE")
    return result
