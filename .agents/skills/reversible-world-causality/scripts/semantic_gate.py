"""Fail-closed semantic admission boundary for world-causality observations.

This gate does NOT do NLI or certify novel comprehension. A byte-exact source
anchor supports a candidate's provenance, not the truth of its interpretation.
Only an out-of-band review attestation may authorize a *shadow trial* prefix.
The HMAC authenticates receipt bytes, NOT the reviewer's correctness.
"""
from __future__ import annotations

from hashlib import sha256
import hmac
import re

try:
    from .codec import canonical, validate_observations, ReversibleError, require
except ImportError:
    from codec import canonical, validate_observations, ReversibleError, require

DECISIONS = frozenset(("SUPPORTED", "PARTIAL", "REJECTED", "UNKNOWN"))
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CLAIM_ID = re.compile(r"^(?:F[0-9]{3,8}|L[0-9]{3,8})$")


def _sha(value):
    return sha256(canonical(value)).hexdigest()


def claims(obs):
    """Fingerprints include exact source positions, literal private spans and direction."""
    anchors = {a["id"]: a for a in obs["anchors"]}
    found = {}
    for fact in obs["facts"]:
        cid = fact["id"]
        deps = [anchors[x] for x in fact["evidence_ids"]]
        found[cid] = {
            "type": "fact",
            "digest": _sha({"edition": obs["source_sha256"], "id": cid,
                            "fact": fact, "evidence": deps}),
            "evidence_ids": list(fact["evidence_ids"]),
            "available_at": max(a["end"] for a in deps),
            "object": fact
        }
    for i, link in enumerate(obs["links"]):
        cid = f"L{i:03}"
        if cid in found:
            raise ReversibleError("LINK_ID_COLLISION")
        deps = [anchors[x] for x in link["evidence_ids"]]
        # Link evidence may be an empty list in legacy observations.
        # Without its own cited evidence, it can never be reviewed as SUPPORTED.
        fact_by_id = {f["id"]: f for f in obs["facts"]}
        ends = []
        for target in (link["source"], link["target"]):
            ends.extend(anchors[x]["end"] for x in
                        fact_by_id[target]["evidence_ids"])
        ends.extend(a["end"] for a in deps)
        found[cid] = {
            "type": "link",
            "digest": _sha({
                "edition": obs["source_sha256"], "id": cid,
                "directed_link": link, "evidence": deps,
                "source_fact": fact_by_id[link["source"]],
                "target_fact": fact_by_id[link["target"]]}),
            "evidence_ids": list(link["evidence_ids"]),
            "available_at": max(ends),
            "object": link,
        }
    return found


def receipt_payload(review):
    needed = {"claim_id", "claim_sha256", "decision", "evidence_ids",
              "reviewer_id", "reviewer_role", "independent",
              "reason", "source_sha256"}
    require(isinstance(review, dict) and set(review) == needed | {"signature"},
            "REVIEW_RECEIPT_SCHEMA_INVALID")
    return {k: review[k] for k in needed}


def sign_review(payload, *, trusted_key):
    """Use only in a separate trusted review process, not inside WF writing."""
    require(isinstance(trusted_key, bytes) and len(trusted_key) >= 32,
            "TRUSTED_REVIEW_KEY_REQUIRED")
    return hmac.new(trusted_key, canonical(payload), sha256).hexdigest()


def audit_and_model_prefix(obs, raw, encoding, *,
                           reviews=(), trusted_key=None, cutoff_byte=None):
    """Return private audit + safe, approved-only model input.

    No human receipt -> zero approved facts/edges; ALL candidates quarantined.
    Avoid leaking held-out counts, source text, review rationale or future hashes.
    """
    validate_observations(obs, raw, encoding)
    if cutoff_byte is not None:
        require(type(cutoff_byte) is int and 0 < cutoff_byte < len(raw),
                "CUTOFF_OUT_OF_BOUNDS")
        try:
            raw[:cutoff_byte].decode(encoding, errors="strict")
        except UnicodeError as exc:
            raise ReversibleError("CUTOFF_SPLITS_CHARACTER") from exc
    require(isinstance(reviews, (list, tuple)) and len(reviews) <= 150000,
            "REVIEW_COUNT_INVALID")
    cmap = claims(obs)
    accepted = {}
    seen = set()
    for review in reviews:
        payload = receipt_payload(review)
        cid = payload["claim_id"]
        require(type(cid) is str and CLAIM_ID.fullmatch(cid)
                and cid in cmap and cid not in seen, "REVIEW_CLAIM_ID_INVALID")
        seen.add(cid)
        require(payload["claim_sha256"] == cmap[cid]["digest"] and
                payload["source_sha256"] == obs["source_sha256"],
                "REVIEW_DOES_NOT_BIND_EXACT_CLAIM")
        require(payload["decision"] in DECISIONS,
                "REVIEW_DECISION_INVALID")
        require(payload["evidence_ids"] == cmap[cid]["evidence_ids"],
                "REVIEW_EVIDENCE_NOT_EXACT")
        require(type(payload["reviewer_id"]) is str and
                2 <= len(payload["reviewer_id"]) <= 80 and
                type(payload["reason"]) is str and
                15 <= len(payload["reason"].strip()) <= 1000,
                "REVIEW_EXPLANATION_INVALID")
        require(payload["reviewer_role"] in {"human_editor", "independent_model"}
                and type(payload["independent"]) is bool,
                "REVIEW_AUTHORITY_INVALID")
        require(isinstance(trusted_key, bytes) and len(trusted_key) >= 32,
                "TRUSTED_REVIEW_KEY_REQUIRED")
        require(type(review["signature"]) is str and
                HEX64.fullmatch(review["signature"]) and
                hmac.compare_digest(
                    review["signature"],
                    sign_review(payload, trusted_key=trusted_key)),
                "REVIEW_SIGNATURE_MISMATCH")
        # Only human independent attestation can enter approved-only shadow
        # context. LLM proposals, even with a valid signature, never self-pass.
        if (payload["decision"] == "SUPPORTED"
                and payload["reviewer_role"] == "human_editor"
                and payload["independent"] is True
                and len(cmap[cid]["evidence_ids"]) >= 1):
            accepted[cid] = cmap[cid]
    visible = {
        cid for cid, info in accepted.items()
        if cutoff_byte is None or info["available_at"] <= cutoff_byte
    }
    facts = [
        {"id": f["id"], "kind": f["kind"],
         "subject_ids": f["subject_ids"], "epistemic": f["epistemic"],
         "telling_seq": f["telling_seq"], "story_tick": f["story_tick"],
         "time_axis": f["time_axis"], "parameters": f["parameters"]}
        for f in obs["facts"] if f["id"] in visible
    ]
    links = [
        {"source": link["source"], "target": link["target"],
         "kind": link["kind"], "epistemic": link["epistemic"]}
        for i, link in enumerate(obs["links"])
        if f"L{i:03}" in visible
        and link["source"] in visible and link["target"] in visible
    ]
    exposed = sorted({ref for f in facts for ref in f["subject_ids"]})
    kinds = {a["id"]: a["kind"] for a in obs["anchors"]}
    # Source hashes and offsets are deliberately excluded from model-facing
    # context. IDs are opaque symbols, not proof of stable cross-scene identity.
    model = {
        "format": "wf.reviewed-world-prefix.v1",
        "anchors": [{"id": a, "kind": kinds[a]} for a in exposed],
        "facts": facts,
        "links": links,
        "world_role_identity_resolution_verified": False,
        "causal_models_not_universally_true": True,
        "nothing_from_unseen_source_injected": True,
        "fictional_story_time_not_inferred": True,
        "cannot_certify_literary_skill": True,
    }
    private = {
        "format": "wf.world-semantic-review-gate.v1",
        "source_sha256": obs["source_sha256"],
        "candidate_facts": len(obs["facts"]),
        "candidate_links": len(obs["links"]),
        "reviewed_claims": len(seen),
        "supported_by_independent_human_receipt": len(accepted),
        "quarantined_claims": len(cmap) - len(accepted),
        "model_visible_facts": len(facts),
        "model_visible_links": len(links),
        "source_anchor_check": "PASS",
        "semantic_truth_machine_proven": False,
        "receipt_signature_only_authenticates_review_bytes": True,
        "fictional_causal_inverse_proven": False,
    }
    return {"private_audit": private, "model_prefix": model}
