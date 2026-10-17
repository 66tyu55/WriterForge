"""Bounded, additive V28 transfer policy from independent SOURCE contexts.

An A/B model review cannot establish literary ability. This protects future
optional writing experiments from blindly deploying a HOST mechanism pair
when multiple distinct source windows produced negative relative effects.
It never deletes mechanisms, rewrites immutable receipts, or changes legacy
CloudABTrial defaults.
"""
from __future__ import annotations
from hashlib import sha256
import json,re

from .reverse_mechanism_boundary import TECHNIQUES

class TransferPolicyError(ValueError):
    pass

def policy_from_immutable_random3(report:dict, *, report_sha256:str)->dict:
    if not isinstance(report,dict) or not isinstance(report_sha256,str):
        raise TransferPolicyError("invalid evidence")
    raw=json.dumps(report,sort_keys=True,ensure_ascii=False,
                   separators=(",",":"),allow_nan=False).encode()
    if (not re.fullmatch(r"[0-9a-f]{64}",report_sha256)
        or sha256(raw).hexdigest()!=report_sha256
        or report.get("format")!="writerforge.random3-postscore-audit.v1"
        or report.get("count")!=3
        or report.get("first_window")!="NOT_PASSED"
        or report.get("second_window")!="LOCKED"
        or report.get("core_promoted") is not False):
        raise TransferPolicyError("unverified random3 input or forged promotion")
    results=report.get("results")
    if not isinstance(results,list) or len(results)!=3:
        raise TransferPolicyError("requires exactly three real-trial metadata reports")
    chapters=set()
    sources=set()
    decisions={}
    for r in results:
        if not isinstance(r,dict): raise TransferPolicyError("invalid trial")
        chapter=r.get("chapter")
        unit=r.get("source_window_sha256")
        ids=r.get("mechanism_ids_unreviewed")
        if (type(chapter) is not int or chapter not in (3,15,17)
            or chapter in chapters
            or not isinstance(unit,str) or not re.fullmatch(r"[a-f0-9]{64}",unit)
            or unit in sources
            or not isinstance(ids,list) or not 1<=len(ids)<=2
            or any(not isinstance(x,str) or x not in TECHNIQUES for x in ids)
            or len(set(ids))!=len(ids)
            or type(r.get("negative_effect")) is not bool
            or type(r.get("enhanced_minus_baseline")) not in (int,float)):
            raise TransferPolicyError("unbounded, repeated or ineligible context")
        chapters.add(chapter)
        sources.add(unit)
        if r["negative_effect"] != (r["enhanced_minus_baseline"]<0):
            raise TransferPolicyError("negative evidence sign inconsistent")
        key=tuple(sorted(ids))
        group=decisions.setdefault(key,{"trials":0,"negative":0,"positive_or_tie":0})
        group["trials"]+=1
        if r["negative_effect"]:group["negative"]+=1
        else:group["positive_or_tie"]+=1
    if chapters!={3,15,17}:
        raise TransferPolicyError("sampled chapters changed")
    states=[]
    for pair,counts in sorted(decisions.items()):
        state=("HOLD_PAIR_IN_NEW_UNREVIEWED_CONTEXTS"
               if counts["trials"]==3 and counts["negative"]==3
               else "MODEL_EVIDENCE_MIXED_OR_INSUFFICIENT")
        states.append({"mechanism_pair":list(pair),
                       "distinct_windows":counts["trials"],
                       "model_rated_negative":counts["negative"],
                       "model_rated_not_negative":counts["positive_or_tie"],
                       "decision":state,"independent_human_validation":False})
    return {
        "format":"writerforge.transfer-policy-candidate.v1",
        "source_report_sha256":report_sha256,
        "source_edition_sha256":report.get("source_sha256"),
        "states":states,
        "whole_book_method_proven":False,
        "legacy_host_mechanisms_deleted":False,
        "new_production_skill_automatically_enabled":False,
        "first_window":"NOT_PASSED","second_window":"LOCKED",
        "independent_review_required_for_promoting":True,
    }


def should_withhold_opt_in(pair:list[str], policy:dict)->bool:
    """Only consulted by an explicit evidence-first caller, not legacy API."""
    if not isinstance(policy,dict) or policy.get("format")!="writerforge.transfer-policy-candidate.v1":
        raise TransferPolicyError("policy unavailable")
    selected=tuple(sorted(pair))
    return any(tuple(entry["mechanism_pair"])==selected and
               entry["decision"]=="HOLD_PAIR_IN_NEW_UNREVIEWED_CONTEXTS"
               for entry in policy["states"])
