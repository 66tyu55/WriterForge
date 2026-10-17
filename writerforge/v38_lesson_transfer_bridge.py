"""V38 one source-linked learned operation -> explicit after-draft evidence.

This is called by the EXISTING writerforge.v35_observable_trace.validate_after
when learning evidence is supplied. A successful shape/evidence match never
asserts learned literary meaning or skill quality. It instead closes the
missing data-flow edge between a frozen source-derived lesson, prewriting
choice, and actual draft citations.

No automatic promotion, mutation, new model call or external literary text.
"""
from __future__ import annotations
from hashlib import sha256
import json
from .v37_foreshadowing_evidence_gate import (
    validate_transfer_claim,ForeshadowingEvidenceError
)

class LearnedTransferGateError(ValueError):
    pass

def _canonical(v):
    return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(",",":"),
                      allow_nan=False).encode("utf-8")

def _sha(data):
    return sha256(data if isinstance(data,bytes)
                  else data.encode("utf-8")).hexdigest()

def verify_lesson_transfer_claims(*,story:str,plan:dict,lessons:dict,
                                   postwrite_angles:set[str],
                                   claims:list[dict])->dict:
    if not isinstance(story,str) or not 350<=len(story)<=4500:
        raise LearnedTransferGateError("LEARNED_TRANSFER_DRAFT_INVALID")
    if (not isinstance(plan,dict) or
        not isinstance(plan.get("decisions"),list) or
        not isinstance(lessons,dict) or
        not isinstance(lessons.get("lessons"),list) or
        not isinstance(postwrite_angles,set) or
        not isinstance(claims,list)):
        raise LearnedTransferGateError("LEARNED_TRANSFER_INPUTS_INVALID")
    known_ids=[x.get("id") for x in lessons["lessons"] if isinstance(x,dict)]
    if len(known_ids)!=len(lessons["lessons"]) or any(
        not isinstance(x,str) or not x for x in known_ids
    ) or len(set(known_ids))!=len(known_ids):
        raise LearnedTransferGateError("LEARNED_TRANSFER_LESSON_REGISTRY_UNTRUSTED")
    linked=[]
    seen_angle=set()
    for item in plan["decisions"]:
        if not isinstance(item,dict) or not isinstance(item.get("angle"),str):
            raise LearnedTransferGateError("LEARNED_TRANSFER_PLAN_UNTRUSTED")
        angle=item["angle"]
        if angle in seen_angle:
            raise LearnedTransferGateError("LEARNED_TRANSFER_DUPLICATE_PREWRITE_ANGLE")
        seen_angle.add(angle)
        lesson_id=item.get("learned_lesson_id")
        if lesson_id is None or not isinstance(lesson_id,str):
            raise LearnedTransferGateError("LEARNED_TRANSFER_PLAN_MISSING_LESSON_ID")
        if lesson_id=="NONE":
            continue
        if lesson_id not in known_ids:
            raise LearnedTransferGateError("LEARNED_TRANSFER_UNKNOWN_SOURCE_LESSON")
        linked.append((angle,lesson_id))
    expected={angle for angle,_ in linked}
    if not expected.issubset(postwrite_angles):
        raise LearnedTransferGateError("LEARNED_LESSON_PREWRITE_NOT_REVIEWED")
    if len(claims)!=len(linked):
        raise LearnedTransferGateError("LEARNED_LESSON_APPLICATION_EVIDENCE_MISSING")
    validated=[]
    distinct=set()
    for record in claims:
        if not isinstance(record,dict):
            raise LearnedTransferGateError("LEARNED_LESSON_CLAIM_NOT_OBJECT")
        pair=(record.get("angle"),record.get("lesson_id"))
        if pair not in linked or pair in distinct:
            raise LearnedTransferGateError("LEARNED_LESSON_CLAIM_NOT_LINKED_OR_DUPLICATED")
        distinct.add(pair)
        try:
            summary=validate_transfer_claim(
                response=record,story=story,plan=plan,lessons=lessons)
        except ForeshadowingEvidenceError as error:
            raise LearnedTransferGateError(str(error)) from None
        validated.append(summary)
    if distinct!=set(linked):
        raise LearnedTransferGateError("LEARNED_LESSON_CLAIM_MISSING_PLAN_LINK")
    validated=sorted(validated,
                     key=lambda r:(r["frozen_plan_angle"],r["source_lesson_id"]))
    statuses=[x["application_claim"] for x in validated]
    return {
        "format":"writerforge.v38-source-learned-postwrite-evidence.v1",
        "frozen_plan_sha256":_sha(_canonical(plan)),
        "candidate_lessons_sha256":_sha(_canonical(lessons)),
        "actual_complete_draft_sha256":_sha(story),
        "source_linked_prewrite_angle_count":len(linked),
        "source_linked_angle_names":sorted(expected),
        "postwrite_coverage_complete":True,
        "evidence_claims":validated,
        "claimed_applied_count":sum(x=="CLAIMED_APPLIED" for x in statuses),
        "admitted_not_applied_count":sum(x=="NOT_APPLIED" for x in statuses),
        "admitted_uncertain_count":sum(x=="UNCERTAIN" for x in statuses),
        "evidence_status":(
            "NO_LEARNED_SKILL_USED" if not linked else
            "CLAIMED_APPLICATION_TEXTUAL_EVIDENCE_ONLY"
            if all(x=="CLAIMED_APPLIED" for x in statuses)
            else "LEARNER_ADMITS_INCOMPLETE_OR_UNCERTAIN_APPLICATION"),
        "mechanism_semantically_verified":False,
        "independent_literary_improvement_proven":False,
        "formal_core_promoted":False,
    }
