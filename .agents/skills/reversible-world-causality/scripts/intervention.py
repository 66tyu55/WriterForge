#!/usr/bin/env python3
"""Counterfactual branch boundary for WF source-grounded world experiments.

Never replay original future facts after an intervention. Candidate outcomes
remain proposals, not forecasts or real story Canon. No model calls or writes.
"""
from __future__ import annotations
from hashlib import sha256
import json
import re

try:
    from .chronology import available_prefix, availability
    from .codec import ReversibleError, require, canonical
except ImportError:
    from chronology import available_prefix, availability
    from codec import ReversibleError, require, canonical

CODE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*$")
IDENT = re.compile(r"^[A-Z][0-9]{3,8}$")
KINDS = frozenset(("modify", "insert"))
CAUSE_TAGS = frozenset(("observed_constraint", "contingency",
                        "irrational_choice", "unknown_origin"))
PREDICTION_STATES = frozenset(("POSSIBLE", "UNKNOWN", "UNEXPLAINED"))


def prepare_branch(obs, raw, encoding, *, cutoff_byte, change):
    """Wrap a source prefix in an invariant, non-prescriptive fork contract."""
    prefix = available_prefix(obs, raw, encoding, cutoff_byte)
    availability(obs, raw, encoding)
    require(isinstance(change, dict) and set(change) ==
            {"id", "mode", "target_fact_id", "kind", "cause_tag"},
            "INTERVENTION_SCHEMA")
    ident, mode, target = change["id"], change["mode"], change["target_fact_id"]
    require(type(ident) is str and IDENT.fullmatch(ident) is not None and
            ident.startswith("I"), "INTERVENTION_ID")
    require(mode in KINDS, "INTERVENTION_MODE")
    require(type(change["kind"]) is str and CODE.fullmatch(change["kind"]),
            "INTERVENTION_KIND")
    require(change["cause_tag"] in CAUSE_TAGS, "INTERVENTION_CAUSE")
    visible = set(prefix["visible_fact_ids"])
    if mode == "modify":
        require(type(target) is str and target in visible,
                "INTERVENTION_TARGET_NOT_IN_SEEN_SOURCE")
    else:
        require(target is None, "INSERT_CANNOT_TARGET_ORIGINAL_FUTURE")
    # An intervention can be causally unexplained; do not fabricate a motive.
    result = {
        "format": "wf.world-counterfactual-branch.v1",
        "source_sha256": sha256(raw).hexdigest(),
        "cutoff_byte": cutoff_byte,
        "source_visible_fact_ids": prefix["visible_fact_ids"],
        "source_visible_link_indices": prefix["visible_link_indices"],
        "intervention": change,
        "prior_original_future_facts_in_branch": [],
        "prior_original_future_links_in_branch": [],
        "withheld_original_fact_count": prefix["hidden_fact_count"],
        "withheld_original_link_count": prefix["hidden_link_count"],
        "candidate_futures": [],
        "past_is_not_rewritten": True,
        "replay_original_future_after_change": False,
        "unexplained_events_permitted": True,
        "no_predicted_outcome_marked_certain": True,
        "semantic_claims_not_verified": True,
    }
    result["contract_sha256"] = sha256(canonical(result)).hexdigest()
    return result


def validate_proposal(branch, proposal):
    """Reject hidden-original answers and unsupported certainty assertions.

    Deliberately *does not* claim an original outcome should be repeated.
    """
    require(isinstance(branch, dict) and branch.get("format") ==
            "wf.world-counterfactual-branch.v1", "BRANCH_INVALID")
    receipt = branch.get("contract_sha256")
    require(type(receipt) is str and receipt == sha256(canonical(
        {k: v for k, v in branch.items() if k != "contract_sha256"})).hexdigest(),
        "BRANCH_CONTRACT_TAMPERED")
    require(isinstance(proposal, dict) and set(proposal) ==
            {"contract_sha256", "candidate_futures"}, "PROPOSAL_SCHEMA")
    require(proposal["contract_sha256"] == receipt, "PROPOSAL_BRANCH_MISMATCH")
    values = proposal["candidate_futures"]
    require(type(values) is list and len(values) <= 12,
            "PROPOSAL_TOO_MANY_EVENTS")
    seen = set()
    prior = set(branch["source_visible_fact_ids"])
    for item in values:
        require(isinstance(item, dict) and set(item) ==
                {"id", "kind", "basis_fact_ids", "status", "cause_tag"},
                "PROPOSED_FUTURE_SCHEMA")
        ident = item["id"]
        require(type(ident) is str and IDENT.fullmatch(ident) is not None and
                ident.startswith("H") and ident not in seen,
                "FUTURE_ID_MUST_BE_FRESH_HYPOTHESIS")
        require(type(item["kind"]) is str and CODE.fullmatch(item["kind"]),
                "PROPOSED_FUTURE_KIND")
        require(item["status"] in PREDICTION_STATES,
                "PROPOSED_FUTURE_CANNOT_BE_CERTAIN")
        require(item["cause_tag"] in CAUSE_TAGS, "PROPOSED_FUTURE_CAUSE")
        ids = item["basis_fact_ids"]
        require(type(ids) is list and len(ids) <= 16 and
                all(type(fid) is str and fid in prior for fid in ids),
                "PREDICTION_USED_UNSEEN_ORIGINAL_FACT")
        require(ids or item["status"] in {"UNKNOWN", "UNEXPLAINED"},
                "UNSUPPORTED_CAUSAL_EXPLANATION")
        seen.add(ident)
    return {
        "format": "wf.world-branch-proposal-check.v1",
        "candidate_count": len(values), "structurally_accepted": True,
        "future_original_knowledge_used": False,
        "world_interpretation_verified": False,
        "candidate_prediction_correctness": "NOT_TESTED",
        "literary_improvement_proven": False,
    }
