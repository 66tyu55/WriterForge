"""0.BN: signature-bound classical method admission inside the existing Xuehai.

No reviewer keys or approval scores are generated here. Classical methods
start PENDING and require two pre-enrolled, distinct external public keys.
An attestation grants at most a bounded experimental WRITE method; it does not
prove legal permissions, human identity, or literary gains on its own.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .runtime import Mode
from .xuehai_method_trust import (
    CONTRACT,SCOPE, public_key_fingerprints, trusted_public_keys,
    validate_challenge,verify_external_signatures,
)


class XuehaiMethodAdmission:
    def __init__(self,store):
        self.store=store
        self.db=store.db
        self.rt=store.runtime

    def _pending_source(self,entry_id:int)->dict:
        from .xuehai import _method_sha, _is_digest
        self.rt.require(Mode.LEARN)
        row=self.db.conn.execute(
            """SELECT m.*,e.text AS entry_text,e.source_hash AS live_entry_hash,
                      e.snapshot_id AS entry_snapshot,
                      e.work_id AS entry_work,
                      e.chapter AS entry_chapter,e.paragraph AS entry_paragraph,
                      e.sentence AS entry_sentence,
                      s.status AS snapshot_status,
                      w.source_uri AS work_uri,w.source_sha256 AS work_sha,
                      sp.excerpt AS span_excerpt,
                      sp.source_sha256 AS span_sha,
                      ch.chapter_sha256 AS chapter_sha,
                      ch.snapshot_id AS study_sid, ps.status AS study_status
               FROM xuehai_method_cards m
               JOIN xuehai_entries e ON m.entry_id=e.id
               JOIN snapshots s ON s.id=e.snapshot_id
               LEFT JOIN studied_works w ON w.work_id=e.work_id
               LEFT JOIN source_spans sp ON sp.work_id=e.work_id
                    AND sp.chapter=e.chapter AND sp.paragraph=e.paragraph
                    AND sp.sentence=e.sentence
               LEFT JOIN studied_chapters ch ON ch.work_id=e.work_id
                    AND ch.chapter=e.chapter
               LEFT JOIN snapshots ps ON ps.id=ch.snapshot_id
              WHERE m.entry_id=?""",(entry_id,),
        ).fetchone()
        if row is None:
            raise ValueError("XUEHAI_EXTERNAL_REVIEW_SOURCE_NOT_FOUND")
        r=dict(row)
        if (r["snapshot_status"]!="staging" or r["revoked_at"] is not None
            or r["source_kind"]!="PUBLIC_DOMAIN_CLASSIC"
            or r["rights_status"]!="RIGHTS_UNVERIFIED"
            or r["review_status"]!="PENDING" or r["value_status"]!="UNVERIFIED"
            or r["review_receipt_sha256"]!=""
            or not _is_digest(r["card_sha256"])
            or _method_sha(r)!=r["card_sha256"]):
            raise ValueError("XUEHAI_EXTERNAL_REVIEW_NOT_PENDING_CLASSIC")
        if (r["snapshot_id"]!=r["entry_snapshot"]
            or r["work_id"]!=r["entry_work"]
            or r["source_uri"]!=r["work_uri"]
            or r["source_sha256"]!=r["work_sha"]
            or r["source_unit_sha256"]!=r["span_sha"]
            or r["span_excerpt"]!=r["entry_text"]
            or r["source_locator"]!=(
                f"{r['entry_chapter']}:{r['entry_paragraph']}:{r['entry_sentence']}")
            or r["entry_source_hash"]!=r["live_entry_hash"]
            or r["entry_source_hash"]!=sha256(
                (r["work_id"]+"|"+" ".join(r["entry_text"].split()).strip()
                ).encode("utf8")).hexdigest()
            or not all(_is_digest(r[k]) for k in (
                "source_sha256","source_unit_sha256","chapter_sha"))
            or r["study_status"]!="published"):
            raise ValueError("XUEHAI_EXTERNAL_REVIEW_SOURCE_OR_CARD_MISMATCH")
        ancestor=self.db.conn.execute(
            """WITH RECURSIVE lineage(id,parent_id,layout) AS(
                 SELECT id,parent_id,layout FROM snapshots WHERE id=?
                 UNION ALL
                 SELECT p.id,p.parent_id,p.layout FROM snapshots p
                   JOIN lineage l ON l.parent_id=p.id
                  WHERE l.layout='delta' AND p.status='published'
               ) SELECT 1 FROM lineage WHERE id=? LIMIT 1""",
            (r["snapshot_id"],r["study_sid"]),
        ).fetchone()
        if not ancestor:
            raise ValueError("XUEHAI_EXTERNAL_REVIEW_SOURCE_NOT_IN_LINEAGE")
        return r

    def challenge(self, *, entry_id:int,rights_basis_uri:str,
                  rights_evidence_sha256:str,craft_review_sha256:str,
                  use_scope:str=SCOPE)->dict:
        keys=trusted_public_keys(require=True)
        r=self._pending_source(entry_id)
        if use_scope!=SCOPE:
            raise ValueError("XUEHAI_EXTERNAL_REVIEW_SCOPE_NOT_PILOT")
        a,b=public_key_fingerprints(keys)
        payload={
            "contract":CONTRACT,
            "entry_id":entry_id,
            "snapshot_id":r["snapshot_id"],
            "card_sha256":r["card_sha256"],
            "work_id":r["work_id"],
            "source_uri":r["source_uri"],
            "source_sha256":r["source_sha256"],
            "source_unit_sha256":r["source_unit_sha256"],
            "source_locator":r["source_locator"],
            "source_edition":r["source_edition"],
            "source_kind":r["source_kind"],
            "rights_status":"RIGHTS_VERIFIED",
            "review_status":"PILOT_APPROVED",
            "value_status":"UNPROVEN_PILOT",
            "use_scope":use_scope,
            "rights_basis_uri":rights_basis_uri,
            "rights_evidence_sha256":rights_evidence_sha256,
            "craft_review_sha256":craft_review_sha256,
            "rights_key_sha256":a,
            "craft_key_sha256":b,
        }
        validate_challenge(payload,r,keys)
        return payload

    def admit(self, *, entry_id:int,challenge:dict,
              rights_signature_hex:str,craft_signature_hex:str)->dict:
        """Explicit LEARN approval: never publish staging or create Canon."""
        keys=trusted_public_keys(require=True)
        r=self._pending_source(entry_id)
        validate_challenge(challenge,r,keys)
        expected=self.challenge(
            entry_id=entry_id,
            rights_basis_uri=challenge["rights_basis_uri"],
            rights_evidence_sha256=challenge["rights_evidence_sha256"],
            craft_review_sha256=challenge["craft_review_sha256"],
            use_scope=challenge["use_scope"])
        if expected!=challenge:
            raise ValueError("XUEHAI_EXTERNAL_REVIEW_SOURCE_OR_CARD_SCOPE_MISMATCH")
        h=verify_external_signatures(
            challenge,rights_signature_hex,craft_signature_hex,keys)
        raw=json.dumps(
            challenge,ensure_ascii=False,sort_keys=True,
            separators=(",",":"),allow_nan=False)
        if len(raw)>3000:
            raise ValueError("XUEHAI_EXTERNAL_REVIEW_CAPSULE_TOO_LARGE")
        self.db.conn.execute(
            """INSERT INTO xuehai_method_attestations(
                   entry_id,payload_json,rights_signature_hex,
                   craft_signature_hex,approval_sha256)
                 VALUES(?,?,?,?,?)""",
            (entry_id,raw,rights_signature_hex,craft_signature_hex,h),
        )
        self.db.conn.commit()
        return {"status":"ATTESTED_STAGING_NOT_PUBLISHED",
                "entry_id":entry_id,"approval_sha256":h,
                "literary_benefit_proven":False,
                "production_canon_writes":0}

    def verified_for_write(self,r:dict)->tuple[str|None,str]:
        """Do not trust mutable SQL flags, even after snapshot publication."""
        if r["source_kind"] not in (
                "PUBLIC_DOMAIN_CLASSIC","AUTHORIZED_MODERN"):
            return None,"NOT_APPLICABLE"
        if (r["rights_status"]!="RIGHTS_UNVERIFIED" or
            r["review_status"]!="PENDING" or
            r["value_status"]!="UNVERIFIED" or
            r["review_receipt_sha256"]!=""):
            return None,"EXTERNAL_REVIEW_PROOF_REQUIRED"
        row=self.db.conn.execute(
            "SELECT * FROM xuehai_method_attestations WHERE entry_id=?",
            (r["entry_id"],),
        ).fetchone()
        if row is None:
            return None,"EXTERNAL_REVIEW_PROOF_REQUIRED"
        try:
            keys=trusted_public_keys(require=True)
        except ValueError:
            return None,"AUTHORITY_NOT_CONFIGURED"
        try:
            payload=json.loads(row["payload_json"])
            validate_challenge(payload,r,keys)
            h=verify_external_signatures(
                payload,row["rights_signature_hex"],
                row["craft_signature_hex"],keys)
            if h!=row["approval_sha256"]:
                return None,"EXTERNAL_REVIEW_SIGNATURE_OR_SOURCE_INVALID"
            return h,"SIGNED_EXTERNAL_REVIEW_VERIFIED"
        except (ValueError,TypeError,KeyError):
            return None,"EXTERNAL_REVIEW_SIGNATURE_OR_SOURCE_INVALID"
