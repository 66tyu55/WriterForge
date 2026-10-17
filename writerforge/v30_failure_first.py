"""Failure-first V30 evidence evaluator: no average can hide a real defect.

Inputs MUST be fresh SHA-verified immutable V29 R2 aggregate. A validation
result is about evidence adequacy and potential harmful technique selections,
not the model's taste or a purported numerical WF mastery score.

No source book, original manuscript, quote or secret enters this module.
Existing scores are immutable; this creates a new candidate record only.
"""
from __future__ import annotations
from hashlib import sha256
import re

from .v29_semantic_regression_candidates import (
    candidate_from_audit, canonical, SemanticRegressionEvidenceError,
)
from .v29_fresh_holdout import manifest
from .v29_old_new_trial import COMMON_TARGET

DIMENSIONS=("perception","causality","information","continuity","language")
DEFAULT_MAX_AB_LENGTH_DIFFERENCE=.15
DRAFT_ABSOLUTE_TARGET_TOLERANCE=.08
MINIMUM_BLIND_SAMPLES_FOR_NEXT_STAGE=6

class FailureFirstError(ValueError):
    pass


def _checked(raw_report:dict,receipt_sha256:str)->dict:
    try:
        return candidate_from_audit(raw_report,report_sha256=receipt_sha256)
    except (SemanticRegressionEvidenceError,ValueError,TypeError,KeyError) as exc:
        raise FailureFirstError("UNTRUSTED_OR_INCOMPLETE_V29_R2_AUDIT") from None


def failure_first_review(raw_report:dict,*,receipt_sha256:str)->dict:
    """Derive loss-preserving observations, never an averaged 'pass' verdict."""
    source=_checked(raw_report,receipt_sha256)
    records=raw_report["results"]
    candidates=source["observations"]
    if len(records)!=3 or len(candidates)!=3:
        raise FailureFirstError("UNREGISTERED_RESULT_COUNT")
    rows=[]
    changed_with_positive=0
    changed_with_negative=0
    same_mechanism_positive=0
    negative_dimensions=0
    severe_regressions=0
    length_noncompliant_count=0
    low=round(COMMON_TARGET*(1-DRAFT_ABSOLUTE_TARGET_TOLERANCE))
    high=round(COMMON_TARGET*(1+DRAFT_ABSOLUTE_TARGET_TOLERANCE))
    if low>=high:
        raise FailureFirstError("INVALID_ABSOLUTE_LENGTH_TARGET")
    for slot,(record,candidate) in enumerate(zip(records,candidates)):
        if (record.get("slot")!=slot or
            record.get("scenario")!=candidate["scenario"] or
            record.get("receipt_sha256")!=candidate["receipt_sha256"]):
            raise FailureFirstError("RESULT_RECEIPT_OR_ORDER_MISMATCH")
        old=record["mechanisms_old"]
        new=record["mechanisms_new"]
        changed=set(old)!=set(new)
        if (type(record.get("mechanisms_same")) is not bool or
            record["mechanisms_same"]==changed or
            candidate["semantic_changed_operations"]!=changed):
            raise FailureFirstError("FALSE_TECHNIQUE_CHANGE_FLAG")
        actual_delta=record["delta"]
        impacts=record["per_dimension_new_minus_old"]
        weak={dim:abs(impacts[dim]) for dim in DIMENSIONS if impacts[dim]<0}
        if len(weak)==len(DIMENSIONS):
            verdict="ALL_FIVE_DIMENSIONS_REGRESSED_BLOCKS_PROMOTION"
            severe_regressions+=1
        elif weak:
            verdict="PARTIAL_DIMENSION_REGRESSION_REQUIRES_REVIEW"
        elif actual_delta>0 and not changed:
            verdict="POSITIVE_SCORE_SAME_OPERATIONS_NO_SELECTOR_CREDIT"
        elif actual_delta>0 and changed:
            verdict="MODEL_POSITIVE_CHANGED_OPERATIONS_NOT_YET_VERIFIED"
        else:
            verdict="NO_NEGATIVE_DIMENSION_BUT_NO_POSITIVE_EVIDENCE"
        negative_dimensions+=len(weak)
        if changed and actual_delta>0:
            changed_with_positive+=1
        if changed and actual_delta<0:
            changed_with_negative+=1
        if not changed and actual_delta>0:
            same_mechanism_positive+=1
        lengths={}
        for name in ("old","new"):
            value=record.get("draft_chars_"+name)
            if type(value) is not int or not 220<=value<=4500:
                raise FailureFirstError("INVALID_OR_MISSING_DRAFT_LENGTH")
            lengths[name]={"chars":value,
                           "meets_common_absolute_target":low<=value<=high,
                           "chars_outside_target":max(low-value,0,value-high)}
        relative_diff=abs(lengths["old"]["chars"]-lengths["new"]["chars"])/max(
            lengths["old"]["chars"],lengths["new"]["chars"])
        if relative_diff>DEFAULT_MAX_AB_LENGTH_DIFFERENCE:
            raise FailureFirstError("MODEL_LENGTH_COMPARISON_NOT_FAIR")
        if not all(x["meets_common_absolute_target"] for x in lengths.values()):
            length_noncompliant_count+=1
        rows.append({
            "slot":slot,"scenario":record["scenario"],
            "precommitted_task_sha256":manifest()["task_sha256"][slot],
            "underlying_actual_r2_sha256":record["receipt_sha256"],
            "old_and_new_mechanisms_changed":changed,
            "old_mechanisms":sorted(old),"new_mechanisms":sorted(new),
            "reported_model_delta_new_minus_old":actual_delta,
            "negative_dimensions_do_not_cancel":weak,
            "other_dimensions":{d:impacts[d] for d in DIMENSIONS if d not in weak},
            "number_of_negative_dimensions":len(weak),
            "critical_failure":len(weak)==len(DIMENSIONS),
            "case_verdict":verdict,
            "model_critic_not_independent_human":True,
            "selector_improvement_caused_by_this_example_proven":False,
            "length_by_arm":lengths,
            "relative_length_comparable":True,
            "absolute_length_compliant_both":all(
                x["meets_common_absolute_target"] for x in lengths.values()),
            "original_full_text_available_for_independent_re_review":False,
        })
    if severe_regressions==0 and negative_dimensions==0:
        defect_verdict="NO_CONFIRMED_MODEL_RATED_NEGATIVE_CASE_BUT_STILL_UNVERIFIED"
    else:
        defect_verdict="MODEL_RATED_REGRESSION_PRESENT_NO_PROMOTION"
    result={
        "format":"writerforge.v30-failure-first-unbiased-assessment.v1",
        "input_v29_actual_immutable_audit_sha256":receipt_sha256,
        "actual_source_window_sha256":raw_report["source_window_sha256"],
        "holdout_manifest_sha256":raw_report["manifest_sha256"],
        "cases":rows,
        "observed_case_count":len(rows),
        "critical_all_five_regressions":severe_regressions,
        "number_of_negative_dimensions":negative_dimensions,
        "technique_changed_and_model_positive_cases":changed_with_positive,
        "technique_changed_and_model_negative_cases":changed_with_negative,
        "positive_cases_with_same_techniques_no_selector_credit":same_mechanism_positive,
        "cases_with_absolute_length_noncompliance":length_noncompliant_count,
        "common_length_target_chars":COMMON_TARGET,
        "common_target_tolerance_pct":8,
        "diagnostic_mean_intentionally_not_an_eligibility_metric":True,
        "validation_status":defect_verdict,
        "stable_literary_progress_proven":False,
        "literary_promotion_allowed":False,
        "v29_model_scores_are_single_critic_unverified":True,
        "critic_and_planner_same_flash_model_family":True,
        "unavailable_independent_full_text_re_review":True,
        "mixed_first_attempt_and_recovery_edit_protocol":True,
        "sample_count_below_fresh_minimum":len(rows)<MINIMUM_BLIND_SAMPLES_FOR_NEXT_STAGE,
        "does_not_auto_disable_positive_legacy_techniques":True,
        "separate_model_generation_variance_not_estimated":True,
        "first_window":"NOT_PASSED",
        "second_window":"LOCKED",
        "model_calls_for_this_v30_review":0,
        "historical_raw_scores_or_receipts_changed":False,
    }
    if len(canonical(result))>14000:
        raise FailureFirstError("BOUNDED_FAILURE_EVIDENCE_TOO_LARGE")
    return result
