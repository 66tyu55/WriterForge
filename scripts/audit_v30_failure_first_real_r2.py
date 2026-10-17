"""Real, zero-model bias-audited V30 R2 readback and failure-first archival.

A historical raw average is *not* a promotion gate. The immutable V29
three-task aggregate is read with exact SHA and validated; a new, separate
defect-first record is written with a fresh readback. No originals, prose,
prompts, drafts, credentials or arbitrary model reviews are saved or logged.
"""
from __future__ import annotations
from hashlib import sha256
import json

from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.v30_failure_first import failure_first_review
from scripts.run_v29_old_new_length_recovery import PREFIX as SOURCE_PREFIX

SOURCE_AGGREGATE_SHA="49ae267ebbc15be5f0350015ad610f994be277339471c4e72f27792d7f37683e"
V30_PREFIX="writerforge/v1/reverse-craft/wudongqiankun/v30-failure-first-unbiased-v1"

def run(store)->dict:
    if store.config.bucket!="writerforge-private-library":
        raise ValueError("PRIVATE_R2_BUCKET_MUST_MATCH")
    key=f"{SOURCE_PREFIX}/three-slot-holdout-audit/{SOURCE_AGGREGATE_SHA}.json"
    raw=store._get_small(key,17000)
    if sha256(raw).hexdigest()!=SOURCE_AGGREGATE_SHA:
        raise ValueError("SOURCE_REAL_R2_SCORE_AGGREGATE_TAMPERED")
    original=json.loads(raw)
    evidence=failure_first_review(original,receipt_sha256=SOURCE_AGGREGATE_SHA)
    payload=_canonical(evidence)
    if len(payload)>14000:
        raise ValueError("V30_FAILURE_FIRST_RECEIPT_TOO_LARGE")
    digest=sha256(payload).hexdigest()
    dest=f"{V30_PREFIX}/immutable-audits/{digest}.json"
    store._put_small_immutable(dest,payload,digest)
    confirmed=store._get_small(dest,14000)
    if confirmed!=payload or sha256(confirmed).hexdigest()!=digest:
        raise ValueError("V30_PRIVATE_IMMUTABLE_RECEIPT_NOT_RECOVERABLE")
    safe={
        "stage":"V30_FAILURE_FIRST_R2_VERIFIED_ZERO_PAID_MODEL_CALLS",
        "source_v29_aggregate_sha256":SOURCE_AGGREGATE_SHA,
        "new_immutable_sha256":digest,
        "validation_status":evidence["validation_status"],
        "stable_literary_progress_proven":False,
        "promotion_allowed":False,
        "actual_case_count":evidence["observed_case_count"],
        "five_dimension_negative_cases":evidence["critical_all_five_regressions"],
        "negative_literary_dimensions":evidence["number_of_negative_dimensions"],
        "positive_changed_mechanisms_unverified":
            evidence["technique_changed_and_model_positive_cases"],
        "negative_changed_mechanisms_unverified":
            evidence["technique_changed_and_model_negative_cases"],
        "same_mechanism_positive_excluded_from_selector_credit":
            evidence["positive_cases_with_same_techniques_no_selector_credit"],
        "absolute_length_noncompliant_cases":
            evidence["cases_with_absolute_length_noncompliance"],
        "cases":[{
            "scene":x["scenario"],"delta":x["reported_model_delta_new_minus_old"],
            "severity":x["case_verdict"],
            "negative_dimensions_do_not_cancel":x["negative_dimensions_do_not_cancel"],
            "old_new_mechanism_changed":x["old_and_new_mechanisms_changed"],
            "absolute_length_compliant_both":x["absolute_length_compliant_both"],
        } for x in evidence["cases"]],
        "old_evidence_overwritten":False,"source_or_manuscript_downloaded":False,
        "model_calls":0,"independent_human_review_done":False,
        "first_window":"NOT_PASSED","second_window":"LOCKED",
    }
    print(json.dumps(safe,ensure_ascii=False,sort_keys=True))
    return safe

if __name__=="__main__":
    run(R2StudyVault(R2Config.from_environment()))
