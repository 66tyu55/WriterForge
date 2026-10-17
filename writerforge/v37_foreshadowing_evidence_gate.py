"""Experimental learned-foreshadowing evidence gate for FUTURE WF writing.

A learner may claim L2 was used only by identifying a real, earlier setup
and a later payoff in its *own* draft and explaining the character's
knowledge boundary. Choosing 'NOT_APPLIED' or 'UNCERTAIN' is legitimate;
a missing anchor can never be converted to success.

Host certifies exact passage existence, order and hash ONLY. Whether the
setup/payoff creates genuine literary significance needs independent review.
No text, explanation, model score or private prose is returned to public
reports by this validator.
"""
from __future__ import annotations
from hashlib import sha256

FIELDS={"lesson_id","angle","application_status","setup_quote",
        "payoff_quote","character_knowledge_at_setup",
        "setup_to_payoff_connection","uncertainty_or_abstention"}
STATUSES={"CLAIMED_APPLIED","NOT_APPLIED","UNCERTAIN"}
class ForeshadowingEvidenceError(ValueError):pass

def _require(ok,code):
    if not ok:raise ForeshadowingEvidenceError(code)

def _explain(s,lo=14,hi=260):
    return isinstance(s,str) and lo<=len(s.strip())<=hi

def validate_transfer_claim(*,response,story,plan,lessons)->dict:
    _require(isinstance(story,str) and 350<=len(story)<=4500,
             "V37_EVIDENCE_DRAFT_OUTSIDE_BOUNDS")
    _require(isinstance(response,dict) and set(response)==FIELDS,
             "V37_EVIDENCE_RESPONSE_SCHEMA_INVALID")
    _require(isinstance(plan,dict) and isinstance(plan.get("decisions"),list)
             and isinstance(lessons,dict) and isinstance(lessons.get("lessons"),list),
             "V37_EVIDENCE_LESSON_PLAN_MISSING")
    lesson_id=response["lesson_id"]
    _require(isinstance(lesson_id,str) and lesson_id in {
        x.get("id") for x in lessons["lessons"] if isinstance(x,dict)},
        "V37_EVIDENCE_UNKNOWN_LEARNED_LESSON")
    angle=response["angle"]
    _require(isinstance(angle,str) and any(
        x.get("angle")==angle and x.get("learned_lesson_id")==lesson_id
        for x in plan["decisions"] if isinstance(x,dict)),
        "V37_EVIDENCE_LESSON_NOT_BOUND_IN_PREWRITE")
    status=response["application_status"]
    _require(isinstance(status,str) and status in STATUSES,
             "V37_EVIDENCE_STATUS_UNKNOWN")
    for key in ("character_knowledge_at_setup","setup_to_payoff_connection",
                "uncertainty_or_abstention"):
        _require(_explain(response[key]),
                 "V37_EVIDENCE_CHARACTER_OR_CAUSE_EXPLANATION_INVALID")
    setup=response["setup_quote"];payoff=response["payoff_quote"]
    _require((setup is None or isinstance(setup,str))
             and (payoff is None or isinstance(payoff,str)),
             "V37_EVIDENCE_QUOTE_TYPE_INVALID")
    _require(status=="CLAIMED_APPLIED" or
             (setup is None and payoff is None),
             "V37_EVIDENCE_ABSTENTION_MUST_NOT_ASSERT_ANCHORS")
    if status=="CLAIMED_APPLIED":
        _require(isinstance(setup,str) and 10<=len(setup)<=100 and
                 isinstance(payoff,str) and 10<=len(payoff)<=100,
                 "V37_EVIDENCE_BOTH_SETUP_AND_PAYOFF_REQUIRED")
        p=story.find(setup);q=story.find(payoff)
        _require(p>=0 and q>=0,"V37_EVIDENCE_FABRICATED_DRAFT_QUOTE")
        _require(p+len(setup)<q,"V37_EVIDENCE_PAYOFF_NOT_AFTER_SETUP")
        # Early/late is a diagnostic, not a universal literary axiom.
        times={"setup_offset":p,"payoff_offset":q,
               "setup_position_pct":round(p/len(story)*100,2),
               "payoff_position_pct":round(q/len(story)*100,2),
               "setup_in_first_half":p<len(story)/2,
               "payoff_after_two_thirds":q>=2*len(story)/3,
               "setup_to_payoff_gap":q-(p+len(setup))}
    else:times=None
    return {
        "format":"writerforge.v37-experimental-lesson-application-evidence.v1",
        "source_lesson_id":lesson_id,
        "frozen_plan_angle":angle,
        "story_sha256":sha256(story.encode("utf-8")).hexdigest(),
        "application_claim":status,
        "setup_quote_sha256":sha256(setup.encode("utf-8")).hexdigest()
            if setup is not None else None,
        "payoff_quote_sha256":sha256(payoff.encode("utf-8")).hexdigest()
            if payoff is not None else None,
        "actual_text_positions":times,
        "character_knowledge_explanation_sha256":
            sha256(response["character_knowledge_at_setup"].encode()).hexdigest(),
        "causal_connection_explanation_sha256":
            sha256(response["setup_to_payoff_connection"].encode()).hexdigest(),
        "uncertainty_explanation_sha256":
            sha256(response["uncertainty_or_abstention"].encode()).hexdigest(),
        "exact_characters_grounded_by_host":status=="CLAIMED_APPLIED",
        "semantics_correct_not_proven":True,
        "independent_literary_review_required":True,
        "automatic_skill_promotion_allowed":False,
    }
