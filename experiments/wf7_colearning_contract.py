"""WF seven-Skill SHADOW co-learning contract.

This is an experimental, source-free *interface test*, NOT a model training
runner, semantic decoder, merged parameter store, or writing pipeline.
Skills keep independent versioned records. Peer suggestions are only inbox
items; the receiving owner alone may propose its own evidence-backed update.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

TIME="xianxia-time-rule"
SPACE="wf-space-topology"
CHARACTER="wf-character-epistemics"
WORLD="wf-world-logic"
EMOTION="wf-personality-affect"
BODY="wf-appearance-body"
ATMOSPHERE="wf-atmosphere-prose"
FOUR=(TIME,SPACE,CHARACTER,WORLD)
SEVEN=FOUR+(EMOTION,BODY,ATMOSPHERE)
FORMAT="wf.7skill.independent-ownership.v1"
EPISTEMIC=("UNKNOWN","PROVISIONAL","SOURCE_REVIEWED","INDEPENDENT_TESTED")

class ContractError(ValueError):pass

def ensure(ok:bool,reason:str):
    if not ok:raise ContractError(reason)

def _ids(items):
    return set(items)

def valid_source_id(x):
    return (type(x) is str and len(x)==64
            and all(a in "0123456789abcdef" for a in x))

def make_empty(study_id:str, source_sha256:str, holdout_sha256:str,
               evidence_ids:list[str], event_ids:list[str],
               active_owners=SEVEN)->dict[str,Any]:
    ensure(type(study_id) is str and bool(study_id.strip()),"INVALID_STUDY")
    ensure(valid_source_id(source_sha256) and valid_source_id(holdout_sha256)
           and source_sha256!=holdout_sha256,"SOURCE_SPLIT_INVALID")
    ensure(len(evidence_ids)==len(set(evidence_ids)) and evidence_ids and
           len(event_ids)==len(set(event_ids)) and event_ids,"EMPTY_OR_DUPLICATE_SOURCE_IDS")
    ensure(all(type(x) is str and bool(x) for x in evidence_ids+event_ids),
           "SOURCE_ID_INVALID")
    active=tuple(active_owners)
    ensure(active in (FOUR,SEVEN),"ONLY_REGISTERED_4_OR_7_SKILL_ARMS")
    return {"format":FORMAT,"study":study_id,
            "source_sha256":source_sha256,
            "sealed_holdout_sha256":holdout_sha256,
            "evidence_ids":list(evidence_ids),"event_ids":list(event_ids),
            "active_owners":list(active),
            "stores":{name:[] for name in active},
            "inbox":[],
            "weight_training_performed":False,
            "independent_semantic_review_passed":False}

def validate(s:dict)->bool:
    ensure(s.get("format")==FORMAT and s.get("weight_training_performed") is False,
           "FORMAT_OR_TRAINING_STATUS")
    owners=tuple(s.get("active_owners",[]))
    ensure(owners in (FOUR,SEVEN) and list(s.get("stores",{}))==list(owners),
           "OWNERSHIP_SCHEMA")
    ensure(valid_source_id(s.get("source_sha256")) and
           valid_source_id(s.get("sealed_holdout_sha256")) and
           s["source_sha256"]!=s["sealed_holdout_sha256"],"EDITION_BOUNDARY_MISSING")
    evs=_ids(s.get("evidence_ids",[]));eventids=_ids(s.get("event_ids",[]))
    ensure(bool(evs) and bool(eventids),"SOURCE_MANIFEST_EMPTY")
    for owner,records in s["stores"].items():
        seen=set()
        ensure(type(records) is list,"OWNER_RECORDS_INVALID")
        for x in records:
            ensure(type(x) is dict and
                   set(x)=={"id","owner","event_id","evidence_ids",
                            "dimension","value","epistemic","revision"},
                   "PARAMETER_SCHEMA")
            ensure(x["owner"]==owner,"CROSS_SKILL_PARAMETER_POLLUTION")
            ensure(type(x["id"]) is str and bool(x["id"]) and
                   type(x["revision"]) is int and x["revision"]>=1,
                   "VERSIONED_PARAMETER_INVALID")
            ensure((x["id"],x["revision"]) not in seen,
                   "PARAMETER_REVISION_COLLISION")
            seen.add((x["id"],x["revision"]))
            ensure(x["event_id"] in eventids and
                   type(x["evidence_ids"]) is list and
                   bool(x["evidence_ids"]) and
                   set(x["evidence_ids"])<=evs,"PARAMETER_WITHOUT_SOURCE")
            ensure(x["epistemic"] in EPISTEMIC and
                   type(x["dimension"]) is str and bool(x["dimension"]),
                   "UNCERTAIN_OR_UNTYPED_PARAMETER")
    seen_signal=set()
    for sig in s["inbox"]:
        ensure(type(sig) is dict and
               set(sig)=={"id","from_owner","to_owner","event_id",
                          "evidence_ids","hypothesis","status"},
               "PEER_SIGNAL_SCHEMA")
        ensure(sig["id"] not in seen_signal and
               type(sig["id"]) is str and bool(sig["id"]),"DUPLICATE_SIGNAL")
        seen_signal.add(sig["id"])
        ensure(sig["from_owner"] in owners and sig["to_owner"] in owners
               and sig["from_owner"]!=sig["to_owner"],"PEER_SOURCE_DEST_INVALID")
        ensure(sig["event_id"] in eventids and
               type(sig["evidence_ids"]) is list and
               bool(sig["evidence_ids"]) and
               set(sig["evidence_ids"])<=evs,"PEER_SIGNAL_WITHOUT_SOURCE")
        ensure(sig["status"]=="PROVISIONAL" and
               type(sig["hypothesis"]) is str and bool(sig["hypothesis"].strip())
               and len(sig["hypothesis"])<=160,"PEER_HINT_CANNOT_BE_APPROVED_FACT")
    return True

def owned_update(s:dict, actor:str, record:dict)->dict:
    """Only the receiver controls its OWN versioned parameter history.

    Unreviewed source IDs merely permit a candidate, never guarantee truth.
    """
    validate(s)
    ensure(actor in s["stores"],"UNKNOWN_SKILL")
    ensure(record.get("owner")==actor,"NOT_YOUR_PARAMETER")
    result=deepcopy(s)
    records=result["stores"][actor]
    ident=record.get("id")
    latest=max((x["revision"] for x in records if x["id"]==ident),default=0)
    ensure(record.get("revision")==latest+1,"VERSION_MUST_APPEND")
    records.append(deepcopy(record))
    validate(result)
    return result

def send_peer_hint(s:dict, signal:dict)->dict:
    """Receive source pointer + an explicit hypothesis; never auto-merge claims."""
    validate(s)
    new=deepcopy(s)
    new["inbox"].append(deepcopy(signal))
    validate(new)
    return new

def collaborative_view(s:dict)->dict:
    """Same immutable stores, inbox grouped for readers. No parameter blending."""
    validate(s)
    return {
      "study":s["study"],"source_sha256":s["source_sha256"],
      "active_owners":deepcopy(s["active_owners"]),
      "independent_parameters":deepcopy(s["stores"]),
      "peer_suggestions_by_owner":{
          owner:deepcopy([x for x in s["inbox"] if x["to_owner"]==owner])
          for owner in s["active_owners"]},
      "no_cross_owner_write":True,
      "collaboration_semantic_gain_verified":False
    }

def split_after_collaboration(s:dict)->dict:
    """Disconnect peers: exactly the independently owned original record versions."""
    validate(s)
    return deepcopy(s["stores"])

def assert_lossless_disconnect(before:dict,after:dict)->dict:
    validate(before);validate(after)
    ensure(before["study"]==after["study"] and
           before["source_sha256"]==after["source_sha256"],
           "DIFFERENT_STUDY_CANNOT_COMPARE")
    discrepancies={}
    for skill in before["active_owners"]:
        if before["stores"][skill]!=after["stores"].get(skill):
            discrepancies[skill]="CHANGED_OWNED_STATE"
    return {"independent_parameters_unchanged":not bool(discrepancies),
            "changed_owner_records":discrepancies,
            "skill_accuracy_after_split":"NOT_MEASURED",
            "holdout_transfer_accuracy":"NOT_MEASURED"}

def public_summary(s:dict)->dict:
    validate(s)
    return {
      "study":s["study"],"skill_count":len(s["active_owners"]),
      "source_sha256":s["source_sha256"],
      "owner_parameter_counts":{k:len(v) for k,v in s["stores"].items()},
      "peer_hint_count":len(s["inbox"]),
      "accuracy":"NOT_MEASURED",
      "literary_improvement":"NOT_MEASURED",
      "skills_have_trained_their_parameters":False,
      "private_source_text_exposed":False
    }
