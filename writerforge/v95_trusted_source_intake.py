"""V95 opt-in trusted source intake: V89 -> V85 -> V86 in ONE LEARN session.

Model proposals are NOT fact assertions. Verify literal visible-source
quotes with the V89 host, tie exact offsets and spans to a V85 PASS-A sealed
same-session audit and FactJournal's frozen knowledge snapshot, then verify
the already persisted V86 independent review signature and negative history.

Even a positively reviewed candidate is only a PROVISIONAL LITERARY
HYPOTHESIS -- never a KNOWN fact, skill promotion, or free WRITE permission.
This module cannot issue its own trusted signature, sign reviewer verdicts,
write R2, create a source ledger, or activate production learning.
"""
from __future__ import annotations

from hashlib import sha256
import hmac

from .runtime import Mode
from .v85_pass_a_bridge import V85SealedLearningBridge
from .v86_controlled_review_loop import V86ControlledReviewLoop
from .v89_source_anchor_gate import (
    resolve_quote_only_answer,WF89AnchorError
)
from .v86_review_contract import verify_link
from .v91_experience_migration import canonical
from .v95_authoritative_head import HeadCommitError,require_head_supported

FORMAT="wf.learn.trusted-source-provisional.v95"
MAX_CANDIDATE_BYTES=8192


class V95SourceAdmissionError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise V95SourceAdmissionError(code)


def hash_obj(doc):
    return sha256(canonical(doc)).hexdigest()


def intake_verified_experimental_candidate(
        *, sealed:V85SealedLearningBridge,
        review_loop:V86ControlledReviewLoop,
        v85_receipt:dict,
        project_id:str,experience_id:str,
        quote_only_model_answer:dict,
        visible_units:tuple[str,...],
        pinned_visible_unit_sha256:list[str],
        original_source_sha256:str,
        frozen_fragment_sha256:str,
        sealed_future_unit_sha256:str):
    """No network or write; *requires* existing signed V86 review in SQLite.

    No ability to forge PASS-A: uses V85SealedLearningBridge's same-session
    seal, which depends on private source bytes and genuine event chain.
    A source-hash-shaped string presented alone is never enough.
    """
    require(isinstance(sealed,V85SealedLearningBridge) and
            isinstance(review_loop,V86ControlledReviewLoop) and
            review_loop.sealed_session is sealed and
            review_loop.experience.runtime is sealed.runtime,
            "WF95_LEARN_BRIDGES_NOT_SAME_TRUSTED_SESSION")
    sealed.runtime.require(Mode.LEARN)
    audit_sha=sealed.require_same_session_receipt(v85_receipt)
    audit=v85_receipt["audit"]
    require(audit.get("claims_count")==1 and
            len(audit.get("claims",[]))==1 and
            audit.get("result")=="PROVISIONAL_CLAIMS" and
            audit.get("literary_semantics_independently_verified") is False and
            audit.get("eligible_to_direct_writing") is False and
            audit.get("source_sha256")==original_source_sha256 and
            audit.get("pass_a_seal_sha256")==
                 v85_receipt.get("r2_seal_sha256"),
            "WF95_V85_AUDIT_NOT_SEALED_SOURCE_HYPOTHESIS")
    claim=audit["claims"][0]
    link=verify_link(review_loop._link(project_id,experience_id))
    require(link["audit_sha"]==audit_sha and
            link["claim_id"]==claim.get("claim_id") and
            link["anchor_sha"]==claim["observation"]["span_sha256"] and
            claim.get("source_sha256")==original_source_sha256 and
            claim.get("context_status")==
                "TYPED_CONTEXT_PRESENT_SEMANTIC_UNVERIFIED" and
            claim.get("actor_knowledge_is_a_typed_claim_not_literary_truth")
                is True and
            claim.get("source_order_proves_causality") is False and
            claim.get("evidence_relation_kind")==
                "SOURCE_ANCHORED_HYPOTHESIS_ONLY",
            "WF95_V85_V86_SOURCE_OR_FACT_CROSSWALK_FAILED")
    require(type(visible_units) is tuple and len(visible_units)==2,
            "WF95_TWO_READ_VISIBLE_UNITS_REQUIRED")
    require(claim["observation"]["unit"] in (1,2) and
            claim.get("consequence") is not None and
            claim["consequence"]["unit"] in (1,2),
            "WF95_V85_CAUSAL_TWO_VISIBLE_SPANS_REQUIRED")
    require(isinstance(quote_only_model_answer,dict) and
            quote_only_model_answer.get("claim_id")==claim["claim_id"],
            "WF95_MODEL_CLAIM_ID_NOT_V85")
    # The raw model never determines a Python offset. Compute it on the
    # exact private visible source; the hidden/future unit is a SHA only.
    try:
        v89=resolve_quote_only_answer(
            quote_only_model_answer,visible_units=visible_units,
            pinned_visible_unit_sha256=pinned_visible_unit_sha256,
            original_source_sha256=original_source_sha256,
            frozen_fragment_sha256=frozen_fragment_sha256,
            sealed_future_unit_sha256=sealed_future_unit_sha256)
    except WF89AnchorError as exc:
        raise V95SourceAdmissionError(
            "WF95_HOST_LITERAL_SOURCE_ANCHOR_REJECTED_"+str(exc)) from None
    require(v89["model_answer_status"]=="HYPOTHESIS" and
            len(v89["located_anchor_meta"])==2 and
            v89["eligible_to_direct_writing"] is False,
            "WF95_MODEL_ABSTENTION_CANNOT_ADMIT_CANDIDATE")
    for field,located in zip(("observation","consequence"),
                             v89["located_anchor_meta"]):
        expected=claim[field]
        require(type(expected) is dict and
                located["unit"]==expected["unit"] and
                located["start"]==expected["start"] and
                located["end"]==expected["end"] and
                located["source_unit_sha256"]==
                     expected["source_unit_sha256"] and
                hmac.compare_digest(
                    located["short_quote_sha256"],
                    expected["span_sha256"]),
                "WF95_V89_V85_EXACT_SOURCE_SPAN_MISMATCH")
    # The V86 status function independently re-validates every persisted
    # review signature. A later NEGATIVE review dominates positive reviews.
    verdict=review_loop.status(
        project_id=project_id,experience_id=experience_id)
    require(verdict=="SUPPORTED_FOR_EXPERIMENT",
            "WF95_MISSING_NEGATIVE_OR_UNRESOLVED_INDEPENDENT_REVIEW")
    result={
        "format":FORMAT,
        "candidate_sha256":link["candidate_sha"],
        "evidence_link_sha256":link["link_sha"],
        "verified_pass_a_audit_sha256":audit_sha,
        "host_source_receipt_sha256":v89["receipt_sha256"],
        "original_source_sha256":original_source_sha256,
        "claim_id":claim["claim_id"],
        "review_state":"SUPPORTED_FOR_EXPERIMENT",
        "source_quote_positions_verified":True,
        "character_knowledge_is_older_typed_assertion_only":True,
        "trust_type":"REVIEWED_HYPOTHESIS_NOT_CHARACTER_FACT",
        "fact_journal_KNOWN_insert_allowed":False,
        "experimental_write_authorization_granted_here":False,
        "literary_skill_promotion_approved":False,
        "independent_literary_truth_proven":False,
        "model_weights_changed":False,
        "requires_external_authority_head_before_cloud_commit":True,
        "original_prose_and_model_explanation_embedded":False,
        "model_calls":0,"r2_writes":0,
    }
    require(len(canonical(result))<=MAX_CANDIDATE_BYTES,
            "WF95_CANDIDATE_RECEIPT_UNBOUNDED")
    result["receipt_sha256"]=hash_obj(result)
    return result
