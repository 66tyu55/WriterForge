#!/usr/bin/env python3
"""WF evidence-availability chronology: correct extraction order, not story time.

Checks when *all* supporting source spans become visible, rejects future
information in prefix experiments, and never infers events from source order.
No original text leaves the local host. This is not a literary truth judge.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

try:
    from .codec import checked_source, validate_observations, ReversibleError
except ImportError:
    from codec import checked_source, validate_observations, ReversibleError


def availability(obs: dict, raw: bytes, encoding: str) -> dict:
    validate_observations(obs, raw, encoding)
    by_anchor = {a["id"]: a for a in obs["anchors"]}
    facts = {}
    for f in obs["facts"]:
        # Use the *last* required source span, never its first mention.
        # Earlier known names alone cannot license future world knowledge.
        available_at = max(by_anchor[ident]["end"] for ident in f["evidence_ids"])
        facts[f["id"]] = available_at
    # Same reveal offset is tied by stable fact ID; no claim of story-time order.
    ranks = {
        ident: idx for idx, ident in enumerate(
            sorted(facts, key=lambda key: (facts[key], key)), 1)
    }
    links = {}
    for i, link in enumerate(obs["links"]):
        ends = [facts[link["source"]], facts[link["target"]]]
        ends += [by_anchor[a]["end"] for a in link["evidence_ids"]]
        links[i] = max(ends)
    mismatches = [
        {"fact_id": f["id"], "given": f["telling_seq"],
         "evidence_rank": ranks[f["id"]]}
        for f in obs["facts"] if f["telling_seq"] != ranks[f["id"]]
    ]
    return {"ranks": ranks, "facts_available_at": facts,
            "links_available_at": links, "mismatches": mismatches}


def audit(obs: dict, raw: bytes, encoding: str) -> dict:
    a = availability(obs, raw, encoding)
    return {
        "format": "wf.evidence-availability-audit.v1",
        "source_sha256": sha256(raw).hexdigest(),
        "facts_checked": len(obs["facts"]),
        "links_checked": len(obs["links"]),
        "telling_seq_mismatches": len(a["mismatches"]),
        "offending_fact_ids": [r["fact_id"] for r in a["mismatches"]],
        "evidence_order_verified": not a["mismatches"],
        "story_time_inferred_from_text_order": False,
        "semantic_truth_verified": False,
        "future_evidence_assumed_known": False,
    }


def normalized(obs: dict, raw: bytes, encoding: str) -> dict:
    a = availability(obs, raw, encoding)
    fixed = deepcopy(obs)
    for f in fixed["facts"]:
        f["telling_seq"] = a["ranks"][f["id"]]
    validate_observations(fixed, raw, encoding)
    assert not availability(fixed, raw, encoding)["mismatches"]
    return fixed


def available_prefix(obs: dict, raw: bytes, encoding: str,
                     cutoff_byte: int) -> dict:
    a = availability(obs, raw, encoding)
    if type(cutoff_byte) is not int or not 0 < cutoff_byte < len(raw):
        raise ReversibleError("PREFIX_OUT_OF_SOURCE_BOUNDS")
    try:
        raw[:cutoff_byte].decode(encoding, errors="strict")
    except UnicodeError as exc:
        raise ReversibleError("PREFIX_SPLITS_SOURCE_CHARACTER") from exc
    visible_facts = {
        key for key, at in a["facts_available_at"].items() if at <= cutoff_byte
    }
    visible_links = [
        idx for idx, at in a["links_available_at"].items()
        if at <= cutoff_byte
        and obs["links"][idx]["source"] in visible_facts
        and obs["links"][idx]["target"] in visible_facts
    ]
    # IDs only: no future evidence strings, gold answers or full original.
    return {
        "format": "wf.world-evidence-prefix.v1",
        "source_sha256": sha256(raw).hexdigest(),
        "cutoff_byte": cutoff_byte,
        "visible_fact_ids": sorted(visible_facts),
        "visible_link_indices": visible_links,
        # Never disclose how many held-out events/links the model cannot see.
        # The private auditor can count them after the blinded trial.
        "source_order_is_not_story_time": True,
        "unknown_future_not_predicted": True,
        "semantic_truth_verified": False,
    }


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="action", required=True)
    for action in ("audit", "normalize", "prefix"):
        s = sub.add_parser(action)
        s.add_argument("--source", required=True)
        s.add_argument("--observations", required=True)
        if action == "normalize":
            s.add_argument("--out", required=True)
        if action == "prefix":
            s.add_argument("--cutoff-byte", required=True, type=int)
    args = ap.parse_args()
    try:
        raw, enc = checked_source(args.source)
        original = json.loads(Path(args.observations).read_text("utf-8"))
        if args.action == "audit":
            result = audit(original, raw, enc)
        elif args.action == "normalize":
            p = Path(args.out)
            if p.exists():
                raise ReversibleError("NORMALIZED_OUTPUT_EXISTS")
            fixed = normalized(original, raw, enc)
            p.write_text(json.dumps(fixed, ensure_ascii=False, indent=2),
                         encoding="utf-8")
            result = {
                "format": "wf.private-chronology-normalization.v1",
                "original_ledger_sha256": sha256(
                    Path(args.observations).read_bytes()).hexdigest(),
                "new_ledger_sha256": sha256(p.read_bytes()).hexdigest(),
                "original_mismatches": len(
                    availability(original, raw, enc)["mismatches"]),
                "after_audit": audit(fixed, raw, enc),
                "fictional_story_time_changed": False,
                "private_output": True,
            }
        else:
            result = available_prefix(original, raw, enc, args.cutoff_byte)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        ap.exit(2, "FAIL: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
