"""V38 actual frozen Xi You Ji negative-control replay: zero model calls.

The *same existing* after-writing validation path is invoked with the newly
wired required source-linked lesson proof. Historical WF stage-03 said L2
in foreshadowing; four historical postwrite checks omitted foreshadowing.
Correct result is an explicit MISSING-EVIDENCE failure, never success.

Private source, explanations, manuscripts remain in R2. Public log only
prints hashes, angle names, statuses and numbers; historical records immutable.
"""
from __future__ import annotations
import json

from writerforge.r2_storage import R2Config,R2StudyVault,_canonical
from writerforge.v35_observable_trace import (
    sha,validate_after,TraceContractError,
)
from writerforge.v38_lesson_transfer_bridge import LearnedTransferGateError
from scripts.forensic_v37_xiyouji_L2 import frozen_evidence
from scripts.run_v35_xiyouji_decision_trace import restore_stage
from scripts.debug_v36_xiyouji_learning_to_writing import (
    EXPECTED_ORIGINAL_SHA,AFTER_SHA,_after_key,_read_exact,
)

ROOT="writerforge/v1/examiner/v38-l2-postwrite-gate-readonly-v1"

def audit(vault,*,persist=True):
    if vault.config.bucket!="writerforge-private-library":
        raise ValueError("PRIVATE_R2_ONLY")
    material=frozen_evidence(vault)
    stage2=restore_stage(vault,2,EXPECTED_ORIGINAL_SHA[1])
    stage3=restore_stage(vault,3,EXPECTED_ORIGINAL_SHA[2])
    if (stage2 is None or stage2[1]!=EXPECTED_ORIGINAL_SHA[2]
        or stage3 is None or stage3[1]!=EXPECTED_ORIGINAL_SHA[3]):
        raise ValueError("HISTORICAL_SOURCE_LESSON_PLAN_SHA_CHANGED")
    lessons=stage2[0]["payload"]
    plan=stage3[0]["payload"]["plan"]
    retrospective=_read_exact(
        vault,_after_key("valid-retrospective",AFTER_SHA),
        AFTER_SHA,36000)
    response={
        "checks":retrospective["checks"],
        "biggest_mistake":retrospective["biggest_mistake"],
    }
    draft=material["revised_draft"]
    old=validate_after(response,draft,plan)
    required=sorted({x["angle"] for x in plan["decisions"]
                     if x["learned_lesson_id"]!="NONE"})
    old_checked=sorted({x["angle"] for x in old["checks"]})
    if required!=["foreshadowing"] or "foreshadowing" in old_checked:
        raise ValueError("L2_HISTORICAL_MISSING_ANGLE_EVIDENCE_CHANGED")
    # Opt into actual production validator. No model guesses or prompt
    # revisions: the old record does not magically acquire a new L2 claim.
    reason=None
    try:
        validate_after(
            response,draft,plan,
            learned_lessons=lessons,
            lesson_transfer_claims=[])
    except LearnedTransferGateError as exc:
        reason=str(exc)
    if reason!="LEARNED_LESSON_PREWRITE_NOT_REVIEWED":
        raise ValueError("UNVERIFIED_L2_WAS_INCORRECTLY_TREATED_AS_TRANSFER_SUCCESS")
    result={
        "format":"writerforge.v38-historical-L2-gate-failure.v1",
        "source_original_stage_sha256s":list(EXPECTED_ORIGINAL_SHA),
        "last_valid_original_review_sha256":AFTER_SHA,
        "actual_frozen_manuscript_sha256":sha(draft),
        "historical_source_linked_angles":required,
        "historical_postwrite_checked_angles":old_checked,
        "source_linked_angles_without_postwrite_evidence":sorted(
            set(required)-set(old_checked)),
        "historical_source_lesson_application_claims_present":0,
        "new_integrated_gate_real_result_code":reason,
        "old_summary_not_upgraded_to_success":True,
        "old_records_not_modified":True,
        "no_literary_transfer_proven":True,
        "zero_model_calls":True,
        "official_promotion_allowed":False,
        "first_window":"NOT_PASSED",
        "second_window":"LOCKED",
    }
    encoded=_canonical(result)
    if len(encoded)>9000:
        raise ValueError("V38_REPORT_TOO_LARGE")
    h=sha(encoded)
    if persist:
        key=f"{ROOT}/immutable-checks/{h}.json"
        vault._put_small_immutable(key,encoded,h)
        if vault._get_small(key,9000)!=encoded:
            raise ValueError("V38_PRIVATE_REPORT_READBACK_FAILED")
    safe={"stage":"V38_REAL_L2_GATE_NEGATIVE_CONTROL",
          "report_sha256":h,"private_report_stored":bool(persist),
          "new_integrated_gate_real_result_code":reason,
          "historical_source_linked_angles":required,
          "source_linked_angles_without_postwrite_evidence":
              result["source_linked_angles_without_postwrite_evidence"],
          "model_calls":0,"literary_skill_promoted":False}
    print(json.dumps(safe,ensure_ascii=False,sort_keys=True))
    return result

if __name__=="__main__":
    audit(R2StudyVault(R2Config.from_environment()))
