"""V37d hard arithmetic: where EXACT source-linked L2 setup/payoff evidence lies.

No text publicly logged, only true immutable numbered citation locations
and draft-percent positions. Does NOT pretend chronological order alone
proves foreshadowing or literary transfer.
"""
from __future__ import annotations
from hashlib import sha256
import json

from writerforge.r2_storage import R2Config,R2StudyVault
from writerforge.v35_observable_trace import sha,canonical
from scripts.forensic_v37_xiyouji_L2 import frozen_evidence,sentence_menu
from scripts.revalidate_v37c_l2_historical_reviews import (
    _get_raw,validate_draft,validate_source,
    L2SplitReviewError,
)
from scripts.forensic_v37b_xiyouji_two_stage import _unwrap,DRAFT_FIELDS,CRITICS
ROOT="writerforge/v1/examiner/v37d-frozen-clue-positions"

def run(vault):
    if vault.config.bucket!="writerforge-private-library":
        raise ValueError("PRIVATE_R2_ONLY")
    actual=frozen_evidence(vault)
    menus={
        "first":sentence_menu(actual["original_draft"],"I"),
        "revised":sentence_menu(actual["revised_draft"],"R"),
    }
    lengths={"first":len(actual["original_draft"]),
             "revised":len(actual["revised_draft"])}
    results=[]
    for model in CRITICS:
        raw,source_h=_get_raw(vault,model,"source")
        src=validate_source(raw)
        other,raw_h=_get_raw(vault,model,"draft")
        item=_unwrap(other,DRAFT_FIELDS)
        is_valid=True
        invalid_code=None
        try:
            validate_draft(other,menus)
        except L2SplitReviewError as exc:
            is_valid=False;invalid_code=str(exc)
        cited={}
        for phase in ("first","revised"):
            for label in ("setup_numbers","payoff_numbers"):
                ids=item[f"{phase}_{label}"]
                # Metadata only even if model values invalid; use None where
                # unable to prove exact int and source menu index.
                valid=(isinstance(ids,list)
                    and all(type(i) is int and 1<=i<=len(menus[phase]) for i in ids))
                points=[menus[phase][i-1]["start"] for i in ids] if valid else []
                cited[f"{phase}_{label}"]={
                    "indices":ids if valid else None,
                    "offsets":points,
                    "as_pct_of_draft":[round(p/lengths[phase]*100,2) for p in points],
                    "is_unambiguous_sentence_index":valid,
                }
        setup=cited["revised_setup_numbers"]["offsets"]
        payoff=cited["revised_payoff_numbers"]["offsets"]
        results.append({
            "model":model,
            "source_opinion_sha256":source_h,
            "draft_opinion_sha256":raw_h,
            "source_support":src["source_support"],
            "abstraction_fidelity":src["abstraction_fidelity"],
            "task_fit":src["task_fit"],
            "draft_format_valid":is_valid,
            "draft_missing_or_invalid_reason":invalid_code,
            "draft_uncertainty_type":type(item.get("uncertainty")).__name__,
            "unvalidated_draft_enums_for_diagnostics_only":{
                name:item[name] for name in ("first_execution",
                    "revised_execution","revised_payoff")},
            "cited_genuine_sentence_positions":cited,
            "earliest_revised_setup_as_pct":(
                round(min(setup)/lengths["revised"]*100,2) if setup else None),
            "earliest_payoff_as_pct":(
                round(min(payoff)/lengths["revised"]*100,2) if payoff else None),
            "revised_setup_in_first_half":(
                min(setup)<len(actual["revised_draft"])/2 if setup else None),
            "revised_setup_to_payoff_first_gap_characters":(
                min(payoff)-min(setup) if setup and payoff else None),
            "no_literary_truth_claimed_from_numeric_location":True,
        })
    result={
        "format":"writerforge.v37d-clue-position-diagnostics.v1",
        "two_verified_frozen_manuscript_lengths":lengths,
        "critic_sentence_menu_sizes":{k:len(menus[k]) for k in menus},
        "reviewer_position_evidence":results,
        "model_calls":0,
        "historical_raw_opinions_unchanged":True,
        "not_independent_human_review":True,
        "formal_skill_promoted":False,
    }
    blob=canonical(result);h=sha(blob)
    if len(blob)>18000:raise ValueError("EXCESSIVE_POSITION_REPORT")
    key=f"{ROOT}/audits/{h}.json"
    vault._put_small_immutable(key,blob,h)
    if vault._get_small(key,18000)!=blob:
        raise ValueError("R2_POSITION_REPORT_NOT_RECOVERABLE")
    print(json.dumps({"stage":"V37D_REAL_L2_TIMING_POSITION_AUDIT",
                      "report_sha256":h,**result},
                     ensure_ascii=False,sort_keys=True))
    return result
if __name__=="__main__":
    run(R2StudyVault(R2Config.from_environment()))
