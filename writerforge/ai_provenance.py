"""V64 bounded signed provenance for assistant-generated story acceptance.

A signed permit proves the configured *host signer* authorized this exact
candidate/scene/snapshot/commit and declared explicit author approval.
It does NOT independently prove a human clicked approve or literature quality.
Untrusted extensions must not have the signing key or raw SQLite access.
"""
from __future__ import annotations

from hashlib import sha256
import hmac
import json
import os
import re

VERSION="writerforge.v64-assistant-provenance-permit.v1"
ID=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,79}")
SHA=re.compile(r"[0-9a-f]{64}")
FIELDS={
    "protocol","project_id","scene_id","commit_id","snapshot_id",
    "body_sha256","candidate_sha256","author_approved",
    "decision_sha256","experience_attempt_id",
    "origin","literary_quality_verified","signature"
}


class AIProvenanceError(PermissionError):
    pass


def require(ok:bool,reason:str)->None:
    if not ok:
        raise AIProvenanceError(reason)


def canonical(data)->str:
    return json.dumps(data,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False)


def trusted_commit_key()->bytes:
    value=os.environ.get("WRITERFORGE_AI_COMMIT_VERIFY_KEY_HEX")
    require(isinstance(value,str) and len(value)>=32,
            "AI_PROVENANCE_SIGNING_KEY_REQUIRED")
    try:
        key=bytes.fromhex(value)
    except ValueError as exc:
        raise AIProvenanceError("AI_PROVENANCE_SIGNING_KEY_INVALID") from exc
    require(len(key)>=16,"AI_PROVENANCE_SIGNING_KEY_INVALID")
    return key


def payload(*,project_id,scene_id,commit_id,snapshot_id,
            body_sha256,candidate_sha256,author_approved,
            decision_sha256=None,experience_attempt_id=None):
    # Real WriterForge scenes may use dots (novel.ch1.s1) or Chinese text.
    # HMAC binds the WHOLE exact value; forbid controls, not legitimate names.
    require(all(isinstance(v,str) and 1<=len(v)<=160
                and v==v.strip()
                and all(ord(char)>=32 and ord(char)!=127 for char in v)
                for v in (project_id,scene_id,commit_id)),
            "AI_PROVENANCE_IDENTIFIERS_INVALID")
    require(type(snapshot_id) is int and snapshot_id>=1,
            "AI_PROVENANCE_SNAPSHOT_INVALID")
    require(all(isinstance(x,str) and SHA.fullmatch(x)
                for x in (body_sha256,candidate_sha256))
                and hmac.compare_digest(body_sha256,candidate_sha256),
            "AI_PROVENANCE_CANDIDATE_HASH_INVALID")
    require(author_approved is True,
            "AI_PROVENANCE_AUTHOR_APPROVAL_REQUIRED")
    require(
        (decision_sha256 is None and experience_attempt_id is None) or
        (isinstance(decision_sha256,str) and SHA.fullmatch(decision_sha256)
         and isinstance(experience_attempt_id,str)
         and ID.fullmatch(experience_attempt_id)),
        "AI_PROVENANCE_EXPERIENCE_REFERENCE_INVALID")
    return {
        "protocol":VERSION,"project_id":project_id,
        "scene_id":scene_id,"commit_id":commit_id,
        "snapshot_id":snapshot_id,"body_sha256":body_sha256,
        "candidate_sha256":candidate_sha256,
        "author_approved":True,
        "decision_sha256":decision_sha256,
        "experience_attempt_id":experience_attempt_id,
        "origin":"assistant_generated",
        "literary_quality_verified":False,
    }


def issue_ai_commit_permit(*,key:bytes,project_id,scene_id,commit_id,
                            snapshot_id,body_sha256,candidate_sha256,
                            author_approved,decision_sha256=None,
                            experience_attempt_id=None):
    """Trusted host only; do not expose key or issuance to model/plugins."""
    require(isinstance(key,bytes) and len(key)>=16,
            "AI_PROVENANCE_SIGNING_KEY_INVALID")
    core=payload(
        project_id=project_id,scene_id=scene_id,
        commit_id=commit_id,snapshot_id=snapshot_id,
        body_sha256=body_sha256,candidate_sha256=candidate_sha256,
        author_approved=author_approved,
        decision_sha256=decision_sha256,
        experience_attempt_id=experience_attempt_id)
    signature=hmac.new(
        key,canonical(core).encode("utf-8"),"sha256").hexdigest()
    return {**core,"signature":signature}


def validate_ai_commit_permit(proof, *,key:bytes,
                              project_id,scene_id,commit_id,
                              snapshot_id,body):
    """Fail closed for unsigned/swapped candidate, scene, clock or origin."""
    require(isinstance(proof,dict) and set(proof)==FIELDS,
            "AI_PROVENANCE_SCHEMA_INVALID")
    require(isinstance(key,bytes) and len(key)>=16,
            "AI_PROVENANCE_SIGNING_KEY_REQUIRED")
    expected_body=sha256(body.encode("utf-8")).hexdigest()
    expected=payload(
        project_id=project_id,scene_id=scene_id,
        commit_id=commit_id,snapshot_id=snapshot_id,
        body_sha256=expected_body,candidate_sha256=expected_body,
        author_approved=True,
        decision_sha256=proof["decision_sha256"],
        experience_attempt_id=proof["experience_attempt_id"])
    require(all(proof.get(k)==v for k,v in expected.items()),
            "AI_PROVENANCE_CONTEXT_MISMATCH")
    candidate_sig=proof["signature"]
    require(isinstance(candidate_sig,str) and SHA.fullmatch(candidate_sig),
            "AI_PROVENANCE_SIGNATURE_INVALID")
    wanted=hmac.new(
        key,canonical(expected).encode("utf-8"),
        "sha256").hexdigest()
    require(hmac.compare_digest(wanted,candidate_sig),
            "AI_PROVENANCE_SIGNATURE_INVALID")
    serialized=canonical(proof)
    return {"permit_sha256":sha256(serialized.encode("utf-8")).hexdigest(),
            "permit_json":serialized,
            "decision_sha256":expected["decision_sha256"],
            "experience_attempt_id":expected["experience_attempt_id"]}
