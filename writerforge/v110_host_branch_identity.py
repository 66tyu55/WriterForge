"""V110: host-owned future branch IDENTITIES, not model-owned story facts.

Observed V109 failure: two different proposed futures reused a branch name.
The id string is a local software routing label, NOT a literary fact.
The host may deterministically assign position-based identities, but ONLY
when all source choice objects exist, every branch has distinct substantive
steps and the original model-produced bytes are stored separately.

This is an explicit DERIVED representation and never edited in place.
It cannot repair missing resources, wrong causal links, cost, motivation,
wrong world state, duplicate content, invalid steps or a bad JSON response.
No model calls, no external literature grader, no canonical fact writes.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256

from .v105_forward_horizon import packed,ident

class V110IdentityError(ValueError):
    pass

def need(test,code):
    if not test:raise V110IdentityError(code)
def digest(value):
    return sha256(packed(value)).hexdigest()

def recover_host_branch_identity(horizon):
    """Only rename duplicate labels in a derived COPY, never story steps."""
    need(type(horizon) is dict and set(horizon)=={"choices"},
         "WF110_ONLY_COMPLETE_HORIZON_OBJECT")
    choices=horizon["choices"]
    need(type(choices) is list and 2<=len(choices)<=3,
         "WF110_TWO_OR_THREE_FUTURES_REQUIRED")
    ids=[]
    steps_sha=[]
    for i,choice in enumerate(choices,1):
        need(type(choice) is dict and set(choice)=={"id","steps"} and
             ident(choice.get("id")) and
             type(choice.get("steps")) is list and
             1<=len(choice["steps"])<=4,
             "WF110_BRANCH_MUST_HAVE_REAL_MODEL_STEPS_AND_VALID_ID")
        ids.append(choice["id"])
        steps_sha.append(digest(choice["steps"]))
    need(len(set(ids))<len(ids),
         "WF110_NOT_A_DUPLICATE_ID_REPAIR_CASE")
    need(len(set(steps_sha))==len(steps_sha),
         "WF110_SAME_SUBSTANTIVE_FUTURE_NOT_ALTERNATIVES")
    original_sha=digest(horizon)
    derived=deepcopy(horizon)
    proof=[]
    for i,item in enumerate(derived["choices"],1):
        old=item["id"]
        new=f"wf110_branch_{i:02d}"
        item["id"]=new
        proof.append({
            "position":i,
            "model_label_sha256":sha256(old.encode("utf8")).hexdigest(),
            "software_assigned_label":new,
            "real_event_steps_sha256":steps_sha[i-1],
        })
    need(len(set(v["id"] for v in derived["choices"]))==len(choices),
         "WF110_INTERNAL_ID_REUSE")
    need(digest(horizon)==original_sha,
         "WF110_ORIGINAL_MODEL_CONTENT_WAS_MUTATED")
    for old,new in zip(horizon["choices"],derived["choices"]):
        need(old["steps"]==new["steps"] and
             digest(old["steps"])==digest(new["steps"]),
             "WF110_HOST_CHANGED_ACTUAL_PLOT_EVENTS_UNSAFE")
    receipt={
        "format":"wf.writing.v110.host-route-only-normalization",
        "original_horizon_sha256":original_sha,
        "derived_horizon_sha256":digest(derived),
        "replacements":proof,
        "model_answer_still_original_in_unmodified_raw_file":True,
        "only_routing_identifiers_changed":True,
        "every_prose_action_and_future_debt_unchanged":True,
        "no_additional_model_calls":True,
        "no_canonical_story_or_factjournal_writes":True,
        "no_syntactic_or_semantic_story_validation_bypassed":True,
        "literary_causal_quality_verified":False,
        "identity_metadata_not_author_intent":True,
    }
    receipt["receipt_sha256"]=digest(receipt)
    return derived,receipt
