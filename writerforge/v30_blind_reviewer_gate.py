"""V30 future critic-diversity and A/B label-swap integrity gate.

This verifier NEVER turns a pair of model opinions into a human-literary
endorsement. Requires two host-recorded distinct model IDs, no model matching
the planner or author, and reversed A/B assignment. Opposing reviewers'
ratings are retained individually, never averaged to conceal disagreements.

Original V29 drafts are already gone, so this gate cannot be retroactively
run on them. Offline synthetic tests do NOT constitute independent reviews.
"""
from __future__ import annotations

DIMS=("perception","causality","information","continuity","language")
class BlindReviewerGateError(ValueError):
    pass

def verify_double_blind_model_reviews(*,planner_model:str,writer_model:str,
                                      critiques:list[dict])->dict:
    if (not isinstance(planner_model,str) or not planner_model or
        not isinstance(writer_model,str) or not writer_model or
        planner_model==writer_model or
        not isinstance(critiques,list) or len(critiques)!=2):
        raise BlindReviewerGateError("TWO_SEPARATE_MODEL_REVIEWERS_REQUIRED")
    ids=set()
    results=[]
    label_layouts=({"A":"legacy","B":"semantic"},
                   {"A":"semantic","B":"legacy"})
    for position,receipt in enumerate(critiques):
        if (not isinstance(receipt,dict) or set(receipt)!={
                "reviewer_model","host_label_mapping","anonymous_task_only",
                "source_prose_exposed","ratings"}):
            raise BlindReviewerGateError("BLIND_REVIEW_SCHEMA_INVALID")
        model=receipt["reviewer_model"]
        if (not isinstance(model,str) or not model
            or model in (planner_model,writer_model) or model in ids):
            raise BlindReviewerGateError("SELF_OR_DUPLICATE_CRITIC_NOT_INDEPENDENT")
        ids.add(model)
        if (receipt["host_label_mapping"]!=label_layouts[position] or
            receipt["anonymous_task_only"] is not True or
            receipt["source_prose_exposed"] is not False):
            raise BlindReviewerGateError("BLIND_LABEL_SWAP_OR_SOURCE_ISOLATION_INVALID")
        scores=receipt["ratings"]
        if not isinstance(scores,dict) or set(scores)!={"A","B"}:
            raise BlindReviewerGateError("CRITIC_MISSING_ANONYMOUS_ARMS")
        old_label="A" if position==0 else "B"
        new_label="B" if position==0 else "A"
        for label in ("A","B"):
            val=scores[label]
            if (not isinstance(val,dict) or set(val)!=set(DIMS)
                or any(type(val[k]) is not int or not 0<=val[k]<=100 for k in DIMS)):
                raise BlindReviewerGateError("CRITIC_DIMENSIONS_INCOMPLETE_OR_FORGED")
        negative={dim:scores[new_label][dim]-scores[old_label][dim]
                  for dim in DIMS if scores[new_label][dim]<scores[old_label][dim]}
        results.append({
            "reviewer_model":model,
            "negative_dimensions":negative,
            "has_regression":bool(negative),
            "preference_positive_all_five":all(
                scores[new_label][dim]>scores[old_label][dim] for dim in DIMS),
            "label_assignment_verified":True,
        })
    agreed_positive=all(x["preference_positive_all_five"] for x in results)
    return {
        "format":"writerforge.v30-two-blinded-model-opinions.v1",
        "reviewer_count":2,"reviewer_model_ids_distinct_from_planner_writer":True,
        "a_b_label_order_swapped_by_host":True,
        "reviewers":results,
        "unanimous_all_dimensions_model_preference":agreed_positive,
        "any_model_disagrees_or_sees_regression":not agreed_positive,
        "status":("TWO_MODELS_POSITIVE_ONLY_NOT_INDEPENDENT_HUMAN_LITERARY_PROOF"
                  if agreed_positive else "MODEL_DISAGREEMENT_OR_REGRESSION_NOT_PASSED"),
        "human_review_performed":False,
        "literary_skill_advanced":False,
        "does_not_override_any_negative_historical_trial":True,
    }
