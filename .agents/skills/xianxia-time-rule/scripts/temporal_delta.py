"""WF xianxia time Skill: source-first *candidate* change detector.

Never overwrite earlier source claims; distinguish newly known information
from an event that actually happened. No automatic causal truth promotion.
This is not a new Skill or another fixed world-template ontology.
"""
from __future__ import annotations
from collections import defaultdict
from copy import deepcopy

ALLOWED_EPISTEMIC={"NARRATED","REPORTED","FORECAST","UNKNOWN"}
ALLOWED_RELATIONS={"AFTER","SAME_TIME","UNKNOWN"}
ALLOWED_EVENT_TYPES={"PHYSICAL","SOCIAL","KNOWLEDGE"}

class TemporalDeltaError(ValueError):
    pass

def require(ok,code):
    if not ok:raise TemporalDeltaError(code)

def propose_changes(source_events):
    """Find needed reviews, not immutable world rules or fake rates.

    Requires an upstream evidence-linked event reader. Chronological source
    reveal order is *not* automatically the events' fictional world order.
    """
    require(type(source_events) is list and 0<len(source_events)<=2000,
            "EVENT_LIST_INVALID")
    grouped=defaultdict(list)
    seen=set()
    for event in source_events:
        required={"id","entity","property","value","evidence_ids",
                  "reveal_index","story_relation_to_prior","epistemic",
                  "event_type","elapsed_status"}
        require(type(event) is dict and set(event)==required,
                "EVENT_SCHEMA_INVALID")
        require(type(event["id"]) is str and event["id"] not in seen and
                1<=len(event["id"])<=60,"EVENT_ID_INVALID")
        seen.add(event["id"])
        require(type(event["entity"]) is str and event["entity"] and
                type(event["property"]) is str and event["property"],
                "PARAMETER_OWNER_INVALID")
        require(type(event["reveal_index"]) is int and event["reveal_index"]>=1,
                "REVELATION_TIME_INVALID")
        require(type(event["evidence_ids"]) is list and
                len(event["evidence_ids"])>=1 and
                all(type(a) is str and a for a in event["evidence_ids"]),
                "SOURCE_EVIDENCE_REQUIRED")
        require(event["story_relation_to_prior"] in ALLOWED_RELATIONS,
                "STORY_TIME_RELATION_INVALID")
        require(event["epistemic"] in ALLOWED_EPISTEMIC,"EPISTEMIC_INVALID")
        require(event["event_type"] in ALLOWED_EVENT_TYPES,"EVENT_TYPE_INVALID")
        require(event["elapsed_status"] is None or
                (type(event["elapsed_status"]) is str and
                 0<len(event["elapsed_status"])<=80),
                "ELAPSED_TIME_STATUS_INVALID")
        grouped[(event["entity"],event["property"])].append(deepcopy(event))
    results=[]
    for (entity,prop),chain in sorted(grouped.items()):
        chain.sort(key=lambda r:(r["reveal_index"],r["id"]))
        for i,item in enumerate(chain):
            previous=chain[i-1] if i else None
            if previous is None:
                classification="FIRST_REVEALED_EVIDENCE"
            elif item["value"]==previous["value"]:
                classification="ADDITIONAL_SOURCE_SUPPORT_NOT_NEW_RULE"
            elif (item["story_relation_to_prior"]=="AFTER" and
                  item["epistemic"]=="NARRATED" and
                  previous["epistemic"]=="NARRATED"):
                classification=("SOCIAL_DECISION_CHANGE_CANDIDATE"
                    if item["event_type"]=="SOCIAL"
                    else "OBSERVED_STATE_CHANGE_CANDIDATE")
            elif item["epistemic"]=="FORECAST":
                classification="POSSIBLE_FUTURE_NOT_COMMITTED"
            else:
                classification="NEW_INFORMATION_OR_CONTRADICTION_NOT_PROVEN_CHANGE"
            results.append({
                "entity":entity,"property":prop,
                "new_claim_id":item["id"],
                "previous_claim_id":previous["id"] if previous else None,
                "old_value":previous["value"] if previous else None,
                "new_value":item["value"],
                "classification":classification,
                "evidence_ids":item["evidence_ids"],
                "story_relation_to_prior":item["story_relation_to_prior"],
                "elapsed_status":item["elapsed_status"],
                "inferred_physical_rate":None,
                "cause_established_by_this_diff":False,
                "cannot_promote_to_world_rule_without_semantic_review":True
            })
    return {
        "format":"wf.time-parameter-change-candidates.v1",
        "candidates":results,
        "original_event_count":len(source_events),
        "all_past_claims_preserved":True,
        "revelation_is_not_event_time":True,
        "complete_original_training":False,
        "independent_semantics_verified":False,
        "world_rule_commit_approved":False
    }
