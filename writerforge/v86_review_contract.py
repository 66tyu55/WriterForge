"""V86 signed, bounded review protocol for opt-in V85 evidence candidates.

Verification key is separately supplied by the trusted review authority, not
the WF model. A signature proves credential possession, NOT human identity,
semantic truth or statistically measured literary improvement.
No novel prose, review comments, raw model answers or original excerpts stored.
"""
from __future__ import annotations

from hashlib import sha256
import hmac
import json
import re

SHA=re.compile(r"[0-9a-f]{64}\Z")
ID=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,79}\Z")
VERDICTS=frozenset(("SUPPORTED_FOR_EXPERIMENT","NEGATIVE","UNCERTAIN"))
REASONS=frozenset(("SOURCE_SUPPORTS_TRIAL","CONTRADICTED_BY_SOURCE",
    "CHARACTER_KNOWLEDGE_ERROR","UNSUPPORTED_CAUSAL_CHAIN",
    "INSUFFICIENT_EVIDENCE","OTHER_REVIEWER_FINDING"))
MAX_REVIEWS_PER_CANDIDATE=16
LINK_FIELDS=frozenset(("project_id","experience_id","candidate_sha",
                       "audit_sha","claim_id","anchor_sha","producer_id",
                       "link_sha"))
REVIEW_FIELDS=frozenset(("contract","project_id","experience_id",
    "candidate_sha","audit_sha","review_id","reviewer_id",
    "verdict","reason_code","literary_graduation_approved"))


class V86ReviewError(ValueError):
    pass


def need(ok,code):
    if not ok:
        raise V86ReviewError(code)


def canonical(doc):
    return json.dumps(doc,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False)


def digest(doc):
    return sha256(canonical(doc).encode("utf-8")).hexdigest()


def _id(value):
    return isinstance(value,str) and ID.fullmatch(value) is not None


def _sha(value):
    return isinstance(value,str) and SHA.fullmatch(value) is not None


def make_link(*,project_id,experience_id,candidate_sha,audit_sha,
              claim_id,anchor_sha,producer_id):
    record=dict(project_id=project_id,experience_id=experience_id,
                candidate_sha=candidate_sha,audit_sha=audit_sha,
                claim_id=claim_id,anchor_sha=anchor_sha,
                producer_id=producer_id)
    need(all(_id(record[x]) for x in (
            "project_id","experience_id","claim_id","producer_id")) and
         all(_sha(record[x]) for x in (
            "candidate_sha","audit_sha","anchor_sha")),
         "WF_V86_LINK_IDENTIFIERS_INVALID")
    return {**record,"link_sha":digest(record)}


def verify_link(link, *, expected_candidate_sha=None):
    need(isinstance(link,dict) and set(link)==LINK_FIELDS,
         "WF_V86_LINK_SCHEMA_INVALID")
    expected=make_link(**{k:link[k] for k in LINK_FIELDS
                          if k!="link_sha"})
    need(link==expected and
         (expected_candidate_sha is None or
          link["candidate_sha"]==expected_candidate_sha),
         "WF_V86_LINK_HASH_OR_CANDIDATE_MISMATCH")
    return link


def review_payload(link, *, reviewer_id,review_id,verdict,reason_code):
    link=verify_link(link)
    need(_id(reviewer_id) and _id(review_id) and
         reviewer_id!=link["producer_id"],
         "WF_V86_REVIEWER_NOT_SEPARATE_FROM_PRODUCER")
    need(verdict in VERDICTS and reason_code in REASONS,
         "WF_V86_REVIEW_VERDICT_INVALID")
    need((verdict=="SUPPORTED_FOR_EXPERIMENT" and
          reason_code=="SOURCE_SUPPORTS_TRIAL") or
         (verdict=="NEGATIVE" and reason_code in (
           "CONTRADICTED_BY_SOURCE","CHARACTER_KNOWLEDGE_ERROR",
           "UNSUPPORTED_CAUSAL_CHAIN","OTHER_REVIEWER_FINDING")) or
         (verdict=="UNCERTAIN" and reason_code=="INSUFFICIENT_EVIDENCE"),
         "WF_V86_REVIEW_REASON_VERDICT_MISMATCH")
    return {
        "contract":"writerforge.v86-frozen-literary-review",
        "project_id":link["project_id"],
        "experience_id":link["experience_id"],
        "candidate_sha":link["candidate_sha"],
        "audit_sha":link["audit_sha"],
        "review_id":review_id,"reviewer_id":reviewer_id,
        "verdict":verdict,"reason_code":reason_code,
        "literary_graduation_approved":False,
    }


def verify_external_signature(payload,signature,key):
    need(isinstance(key,bytes) and len(key)>=32,
         "WF_V86_EXTERNAL_REVIEW_VERIFIER_UNAVAILABLE")
    need(isinstance(signature,str) and _sha(signature),
         "WF_V86_REVIEW_SIGNATURE_MISSING")
    expected=hmac.new(key,canonical(payload).encode("utf-8"),
                      "sha256").hexdigest()
    need(hmac.compare_digest(expected,signature),
         "WF_V86_REVIEW_SIGNATURE_INVALID")


def load_link_and_state(conn,project_id,experience_id,review_key):
    """Always revalidate row hashes and independent signatures on decision.

    Returns None for unchanged legacy V61/62 candidates. New opt-in V86
    candidates require a nonempty verifier and a review before selection.
    Multiple append-only reviews aggregate conservatively: any NEGATIVE
    blocks; UNKNOWN prevents positive reuse.
    """
    row=conn.execute(
        "SELECT * FROM experience_evidence_links "
        "WHERE project_id=? AND experience_id=?",
        (project_id,experience_id)).fetchone()
    if row is None:
        return None
    link=verify_link(dict(row))
    need(link["project_id"]==project_id and
         link["experience_id"]==experience_id,
         "WF_V86_LINK_SCOPE_INVALID")
    candidate=conn.execute(
        "SELECT candidate_sha FROM experience_candidates "
        "WHERE project_id=? AND experience_id=?",
        (project_id,experience_id)).fetchone()
    need(candidate is not None and
         candidate["candidate_sha"]==link["candidate_sha"],
         "WF_V86_CANDIDATE_SOURCE_CHANGED")
    need(isinstance(review_key,bytes) and len(review_key)>=32,
         "WF_V86_EXTERNAL_REVIEW_VERIFIER_UNAVAILABLE")
    rows=conn.execute(
        "SELECT * FROM experience_literary_reviews "
        "WHERE project_id=? AND experience_id=? "
        "ORDER BY review_seq LIMIT ?",
        (project_id,experience_id,MAX_REVIEWS_PER_CANDIDATE+1)
    ).fetchall()
    need(len(rows)<=MAX_REVIEWS_PER_CANDIDATE,
         "WF_V86_REVIEW_BUDGET_EXCEEDED")
    seen=set()
    verdicts=set()
    for r in rows:
        packet=json.loads(r["review_json"])
        need(isinstance(packet,dict) and
             set(packet)==REVIEW_FIELDS and
             packet["review_id"]==r["review_id"] and
             packet["reviewer_id"]==r["reviewer_id"] and
             packet["review_id"] not in seen,
             "WF_V86_REVIEW_RECORD_IMMUTABILITY_INVALID")
        expected=review_payload(
            link,reviewer_id=packet["reviewer_id"],
            review_id=packet["review_id"],verdict=packet["verdict"],
            reason_code=packet["reason_code"])
        need(packet==expected and
             digest({"payload":packet,"signature":r["signature"]})==
             r["review_sha"],
             "WF_V86_REVIEW_BINDING_OR_HASH_MISMATCH")
        verify_external_signature(packet,r["signature"],review_key)
        seen.add(packet["review_id"])
        verdicts.add(packet["verdict"])
    if "NEGATIVE" in verdicts:
        return "NEGATIVE"
    if "UNCERTAIN" in verdicts:
        return "UNCERTAIN"
    if "SUPPORTED_FOR_EXPERIMENT" in verdicts:
        return "SUPPORTED_FOR_EXPERIMENT"
    return "NOT_REVIEWED"
