"""V86 controlled LEARN -> sealed source -> signed review -> WRITE experiment.

This is an OPT-IN bridge. It never self-signs reviews or approvals, and never
writes R2. Reviews are signed by an external verifier distinct from the
approval key. A signed review is an attested observation, not literary truth.
Only system-owned operations can ever become experimental WRITE guidance.

On failed prior behavior, the old hypothesis remains immutable and the next
WRITE decision must SKIP it. A revision uses a fresh experience_id, explicit
changed operating conditions and separate signed experimental approval.
"""
from __future__ import annotations

from hashlib import sha256
import hmac
import sqlite3

from .experience_decision import ExperienceDecisionBridge, digest as decision_digest
from .runtime import Mode
from .v86_review_contract import (
    make_link,review_payload,verify_external_signature,load_link_and_state,
    digest,canonical,need,V86ReviewError,
)

MAX_TEXT=120


class V86ControlledReviewLoop:
    def __init__(self,experience:ExperienceDecisionBridge,sealed_session):
        need(isinstance(experience,ExperienceDecisionBridge) and
             hasattr(sealed_session,"require_same_session_receipt"),
             "WF_V86_TYPED_BRIDGE_REQUIRED")
        need(experience.runtime is sealed_session.runtime,
             "WF_V86_SAME_LEARN_SESSION_REQUIRED")
        self.experience=experience
        self.sealed_session=sealed_session

    def stage_from_sealed(self,*,project_id,experience_id,
                          snapshot_id,source_ref,source_quote,receipt,
                          claim_id,producer_id,operation_code,
                          required_tags,forbidden_tags,
                          supersedes_experience_id=None):
        self.experience.runtime.require(Mode.LEARN)
        audit_sha=self.sealed_session.require_same_session_receipt(receipt)
        audit=receipt["audit"]
        matches=[c for c in audit["claims"] if c["claim_id"]==claim_id]
        need(len(matches)==1,"WF_V86_CLAIM_NOT_IN_VERIFIED_AUDIT")
        claim=matches[0]
        need(claim.get("source_sha256")==audit["source_sha256"] and
             claim.get("chapter")==audit["chapter"] and
             claim.get("evidence_relation_kind")==
                 "SOURCE_ANCHORED_HYPOTHESIS_ONLY" and
             claim.get("context_status")==
                 "TYPED_CONTEXT_PRESENT_SEMANTIC_UNVERIFIED" and
             audit["literary_semantics_independently_verified"] is False,
             "WF_V86_CLAIM_UNRESOLVED_OR_NOT_PROVISIONAL")
        need(isinstance(source_quote,str) and
             8<=len(source_quote)<=MAX_TEXT and
             sha256(source_quote.encode("utf8")).hexdigest()==
             claim["observation"]["span_sha256"],
             "WF_V86_SOURCE_QUOTE_NOT_BOUND_TO_V85")
        need(isinstance(source_ref,dict) and
             source_ref.get("chapter")==audit["chapter"] and
             isinstance(snapshot_id,int) and snapshot_id>=1,
             "WF_V86_SOURCE_REF_WRONG_CHAPTER")
        # Existing Xuehai is one exact source version. No separate copied
        # novel or second relational memory database is introduced.
        row=self.experience.db.conn.execute(
            "SELECT excerpt,source_sha256 FROM source_spans "
            "WHERE work_id=? AND chapter=? AND paragraph=? AND sentence=?",
            (source_ref["work_id"],source_ref["chapter"],
             source_ref["paragraph"],source_ref["sentence"])
        ).fetchone()
        need(row is not None and
             row["source_sha256"]==source_ref["source_sha256"] and
             sha256(row["excerpt"].encode("utf8")).hexdigest()==
             row["source_sha256"] and
             row["excerpt"].count(source_quote)==1,
             "WF_V86_SOURCE_SPAN_CROSSWALK_FAILED")
        book=self.experience.db.conn.execute(
            "SELECT source_sha256 FROM studied_works WHERE work_id=?",
            (source_ref["work_id"],)).fetchone()
        need(book is not None and
             book["source_sha256"]==audit["source_sha256"],
             "WF_V86_ORIGINAL_WORK_VERSION_CHANGED")
        # Reconstruct existing V61 candidate digest exactly. Review case
        # and candidate are created in ONE SQLite transaction by V61.
        base=dict(project_id=project_id,experience_id=experience_id,
                  source_snapshot_id=snapshot_id,source_ref=dict(source_ref),
                  required_tags=sorted(required_tags),
                  forbidden_tags=sorted(forbidden_tags),
                  operation_code=operation_code,
                  source_semantics_verified=False,status="HYPOTHESIS_ONLY")
        if supersedes_experience_id is not None:
            old_link=self._link(project_id,supersedes_experience_id)
            # A previously refuted literary interpretation cannot regain
            # authority merely by renaming its candidate or action. Require
            # a genuinely NEW V85 sealed claim and audit receipt; even then
            # it remains only an unreviewed hypothesis until separately
            # signed again by the external reviewer.
            need(old_link["audit_sha"]!=audit_sha and
                 old_link["claim_id"]!=claim_id,
                 "WF_V86_REVISION_REQUIRES_NEW_SEALED_CLAIM")
            prior,_=self.experience._lookup_candidate(
                project_id,supersedes_experience_id)
            base.update(
                supersedes_experience_id=supersedes_experience_id,
                prior_candidate_sha256=prior["candidate_sha"],
                revision_reason="PRIOR_ADVERSE_OR_REVOKED")
        candidate_sha=decision_digest(base)
        link=make_link(
            project_id=project_id,experience_id=experience_id,
            candidate_sha=candidate_sha,audit_sha=audit_sha,
            claim_id=claim_id,
            anchor_sha=claim["observation"]["span_sha256"],
            producer_id=producer_id)
        result=self.experience.stage_candidate(
            project_id=project_id,experience_id=experience_id,
            snapshot_id=snapshot_id,source_ref=source_ref,
            required_tags=required_tags,forbidden_tags=forbidden_tags,
            operation_code=operation_code,
            supersedes_experience_id=supersedes_experience_id,
            evidence_link=link)
        need(result["candidate_sha256"]==candidate_sha,
             "WF_V86_CANDIDATE_SOURCE_RACE")
        return {
            "candidate_sha256":candidate_sha,"evidence_link_sha256":link["link_sha"],
            "sealed_v85_audit_sha256":audit_sha,
            "experiment_approved":False,
            "independent_literary_quality_proven":False,
            "model_weight_updated":False,
            "private_source_or_explanations_returned":False,
        }

    def review_payload(self,*,project_id,experience_id,reviewer_id,
                       review_id,verdict,reason_code):
        self.experience.runtime.require(Mode.LEARN)
        link=self._link(project_id,experience_id)
        return review_payload(link,reviewer_id=reviewer_id,
                              review_id=review_id,verdict=verdict,
                              reason_code=reason_code)

    def _link(self,project_id,experience_id):
        from .v86_review_contract import verify_link
        row=self.experience.db.conn.execute(
            "SELECT * FROM experience_evidence_links WHERE "
            "project_id=? AND experience_id=?",
            (project_id,experience_id)).fetchone()
        need(row is not None,"WF_V86_LINKED_CANDIDATE_NOT_FOUND")
        return verify_link(dict(row))

    def append_external_review(self,*,payload,signature):
        """An external actor generates signature over a precommitted payload.

        No signing key or fake semantic grade is created by WriterForge.
        """
        self.experience.runtime.require(Mode.LEARN)
        need(isinstance(payload,dict) and
             isinstance(payload.get("project_id"),str) and
             isinstance(payload.get("experience_id"),str),
             "WF_V86_REVIEW_PAYLOAD_INVALID")
        link=self._link(payload["project_id"],payload["experience_id"])
        exact=review_payload(
            link,reviewer_id=payload.get("reviewer_id"),
            review_id=payload.get("review_id"),
            verdict=payload.get("verdict"),
            reason_code=payload.get("reason_code"))
        need(payload==exact,"WF_V86_REVIEW_PAYLOAD_NOT_PRECOMMITTED")
        verify_external_signature(
            exact,signature,self.experience._literary_review_key)
        receipt_sha=digest({"payload":exact,"signature":signature})
        conn=self.experience.db.conn
        previous=conn.execute(
            "SELECT * FROM experience_literary_reviews "
            "WHERE project_id=? AND experience_id=? AND review_id=?",
            (exact["project_id"],exact["experience_id"],
             exact["review_id"])).fetchone()
        if previous is not None:
            need(previous["review_sha"]==receipt_sha and
                 previous["signature"]==signature and
                 previous["review_json"]==canonical(exact),
                 "WF_V86_REVIEW_IMMUTABLE_REPLAY_MISMATCH")
            return {"review_sha256":receipt_sha,"replayed":True,
                    "literary_truth_verified":False}
        # No model answer, private quote, reviewer commentary or raw
        # original paragraphs are part of the SQL receipt.
        try:
            with conn:
                conn.execute(
                    "INSERT INTO experience_literary_reviews("
                    "project_id,experience_id,review_id,reviewer_id,"
                    "review_json,review_sha,signature)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (exact["project_id"],exact["experience_id"],
                     exact["review_id"],exact["reviewer_id"],
                     canonical(exact),receipt_sha,signature))
        except sqlite3.IntegrityError as exc:
            raise V86ReviewError("WF_V86_CONCURRENT_REVIEW_CONFLICT") from exc
        return {"review_sha256":receipt_sha,"replayed":False,
                "literary_truth_verified":False,
                "approved_writing_only_with_separate_signed_permission":True}

    def status(self,*,project_id,experience_id):
        return load_link_and_state(
            self.experience.db.conn,project_id,experience_id,
            self.experience._literary_review_key)
