"""V37c lossless revalidation of ALREADY SAVED L2 literary reviews.

Not new grading, no guessing or truncating commentary. Previous reviewer
format failures remain immutable. Require all substantive reasons >=15 chars,
allow short but explicit uncertainty (>=8), long complete literary paragraphs
(up to 450), up to 8 verified exact numbered source/draft citations.
Null/non-string uncertainty remains an actual failure, not filled by host.
"""
from __future__ import annotations
import json

from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.v35_observable_trace import sha,canonical
from scripts.forensic_v37b_xiyouji_two_stage import (
    _root,_unwrap,SOURCE_FIELDS,DRAFT_FIELDS,SOURCE_ENUM,DRAFT_ENUM,
    L2SplitReviewError,CRITICS,
)
from scripts.diagnose_v37b_private_review_lengths import RAW
from scripts.forensic_v37_xiyouji_L2 import frozen_evidence,sentence_menu

ROOT="writerforge/v1/examiner/v37c-preserve-original-l2-review-evidence"
MAX_RAW=35000

def _check(condition,code):
    if not condition:raise L2SplitReviewError(code)

def validate_source(raw:dict)->dict:
    row=_unwrap(raw,SOURCE_FIELDS)
    for key,allowed in SOURCE_ENUM.items():
        _check(isinstance(row[key],str) and row[key] in allowed,
               "V37C_INVALID_SOURCE_ENUM")
    for name in ("source_reason","abstraction_reason","fit_reason"):
        _check(isinstance(row[name],str) and 15<=len(row[name].strip())<=450,
               "V37C_SUBSTANTIVE_SOURCE_REASON_MISSING")
    _check(isinstance(row["uncertainty"],str)
           and 8<=len(row["uncertainty"].strip())<=300,
           "V37C_UNCERTAINTY_MISSING_OR_UNBOUNDED")
    return row

def _ids(row,name,menu):
    values=row[name]
    _check(isinstance(values,list) and len(values)<=8
           and all(type(v) is int and 1<=v<=len(menu) for v in values)
           and len(values)==len(set(values)),
           "V37C_CITATIONS_NOT_GENUINE_NUMBERED_OFFSETS")
    return [menu[n-1]["start"] for n in values]

def validate_draft(raw:dict,menus:dict)->dict:
    row=_unwrap(raw,DRAFT_FIELDS)
    for key,allowed in DRAFT_ENUM.items():
        _check(isinstance(row[key],str) and row[key] in allowed,
               "V37C_INVALID_DRAFT_ENUM")
    _check(isinstance(row["execution_reason"],str)
           and 15<=len(row["execution_reason"].strip())<=450,
           "V37C_SUBSTANTIVE_EXECUTION_REASON_MISSING")
    _check(isinstance(row["uncertainty"],str)
           and 8<=len(row["uncertainty"].strip())<=300,
           "V37C_UNCERTAINTY_MISSING_OR_UNBOUNDED")
    for part in ("first","revised"):
        start=_ids(row,f"{part}_setup_numbers",menus[part])
        payoff=_ids(row,f"{part}_payoff_numbers",menus[part])
        if start and payoff:
            _check(min(start)<max(payoff),
                   "V37C_SOURCE_PAYOFF_PRECEDES_SETUP")
        if row[f"{part}_execution"]=="NOT_OBSERVED":
            _check(not start and not payoff,
                   "V37C_MODEL_CITES_NONEXISTENT_EXECUTION")
    if row["revised_payoff"]=="GROUNDED":
        _check(row["revised_setup_numbers"] and row["revised_payoff_numbers"],
               "V37C_GROUNDED_PAYOFF_WITHOUT_LINKED_EVIDENCE")
    if row["revised_payoff"]=="MISSING":
        _check(not row["revised_payoff_numbers"],
               "V37C_CLAIMS_MISSING_BUT_CITES_PAYOFF")
    return row

def _get_raw(vault,model,phase):
    h=RAW[(model,phase)]
    key=f"{_root()}/unfiltered-{model}-{phase}-{h}.json"
    body=vault._get_small(key,MAX_RAW)
    _check(sha(body)==h,"V37C_HISTORICAL_RAW_REPLY_TAMPERED")
    record=json.loads(body)
    _check(record.get("model")==model and record.get("phase")==phase
           and record.get("before_validation") is True,
           "V37C_RAW_REPLY_PROVENANCE_MISMATCH")
    return record["unmodified_model_response"],h

def replay(vault,*,persist=True):
    _check(vault.config.bucket=="writerforge-private-library","PRIVATE_R2_ONLY")
    actual=frozen_evidence(vault)
    menus={
        "first":sentence_menu(actual["original_draft"],"I"),
        "revised":sentence_menu(actual["revised_draft"],"R"),
    }
    rows=[];failures=[]
    for model in CRITICS:
        for phase in ("source","draft"):
            raw,h=_get_raw(vault,model,phase)
            try:
                data=(validate_source(raw) if phase=="source"
                      else validate_draft(raw,menus))
                row={
                    "reviewer":model,"phase":phase,"raw_sha256":h,
                    "status":"LOSSLESS_ORIGINAL_RESPONSE_VALID_AFTER_BOUNDARY_FIX",
                    "source_support":data.get("source_support"),
                    "abstraction_fidelity":data.get("abstraction_fidelity"),
                    "task_fit":data.get("task_fit"),
                    "first_execution":data.get("first_execution"),
                    "revised_execution":data.get("revised_execution"),
                    "revised_payoff":data.get("revised_payoff"),
                    "cited_exact_numbered_sentences":{
                        k:list(data[k]) for k in (
                            "first_setup_numbers","first_payoff_numbers",
                            "revised_setup_numbers","revised_payoff_numbers")
                    } if phase=="draft" else None,
                    "no_original_review_content_edited":True,
                }
                rows.append(row)
            except L2SplitReviewError as err:
                failures.append({"reviewer":model,"phase":phase,
                                 "raw_sha256":h,"code":str(err),
                                 "not_substituted_with_an_average":True})
    report={
        "format":"writerforge.v37c-raw-evidence-revalidation.v1",
        "source_stage_sha256s":actual["stage_sha256s"],
        "old_v37_and_v37b_errors_preserved":True,
        "status":("ALL_FOUR_RAW_OPINIONS_LOSSLESSLY_VERIFIED"
                  if len(rows)==4 and not failures else
                  "PARTIAL_HISTORICAL_RAW_OPINIONS_ONLY"),
        "valid_raw_phases":rows,"invalid_raw_phases":failures,
        "expected_four_phases":4,
        "new_model_calls":0,
        "literary_quality_or_mastery_proven":False,
        "official_skill_promoted":False,
        "first_window":"NOT_PASSED","second_window":"LOCKED",
    }
    blob=canonical(report);h=sha(blob)
    _check(len(blob)<=22000,"V37C_REPORT_TOO_LARGE")
    if persist:
        key=f"{ROOT}/audits/{h}.json"
        vault._put_small_immutable(key,blob,h)
        _check(vault._get_small(key,22000)==blob,
               "V37C_PRIVATE_RESULT_READBACK_FAILED")
    print(json.dumps({"stage":"V37C_ZERO_MODEL_HISTORICAL_REPLAY",
                      "result_sha256":h,**report},
                     ensure_ascii=False,sort_keys=True))
    return report

if __name__=="__main__":
    replay(R2StudyVault(R2Config.from_environment()))
