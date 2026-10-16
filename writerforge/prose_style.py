"""Explicit, bounded prose-style references for the REAL WriterForge draft route.

An accepted AI draft is NOT a style benchmark. No source study, structural
tag, heuristic quality score or first-chapter guess can activate this record.
Only a user-confirmed reference is stored; it lives in the EXISTING SQLite,
therefore an ordinary verified R2 database backup also preserves it.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re

from .db import WriterForgeDB

MIN_REFERENCE_CHARS = 120
MAX_REFERENCE_CHARS = 1200
MAX_REFERENCE_LINES = 65
COPY_GUARD_CHARS = 24


class ProseStyleError(ValueError):
    pass


@dataclass(frozen=True)
class ApprovedProseStyle:
    text: str
    sha256: str
    version: int
    source_kind: str
    source_scope: str | None


class ProseStyleStore:
    """One project-scoped, author-approved reference; no automatic promotion."""

    def __init__(self, db: WriterForgeDB, project_id: str):
        if (not isinstance(project_id, str) or not 1 <= len(project_id) <= 128
            or not project_id.strip() or any(ord(c) < 32 for c in project_id)):
            raise ProseStyleError("invalid project ID")
        self.db = db
        self.project_id = project_id

    def approve(self, text: str, *, author_confirmed: bool,
                accepted_scope: str | None = None) -> dict:
        if author_confirmed is not True:
            raise ProseStyleError("reference requires explicit author quality approval")
        if not isinstance(text, str):
            raise ProseStyleError("reference must be prose text")
        excerpt = text.strip()
        if (not MIN_REFERENCE_CHARS <= len(excerpt) <= MAX_REFERENCE_CHARS
            or len(excerpt.splitlines()) > MAX_REFERENCE_LINES
            or "\x00" in excerpt):
            raise ProseStyleError("reference must be a 120..1200-character bounded prose excerpt")
        kind = "author_supplied"
        source_hash = None
        if accepted_scope is not None:
            if (not isinstance(accepted_scope, str) or not accepted_scope
                or len(accepted_scope) > 128):
                raise ProseStyleError("invalid accepted source scope")
            row = self.db.conn.execute(
                "SELECT body,body_hash FROM accepted_prose WHERE project_id=? AND scope_id=?",
                (self.project_id, accepted_scope),
            ).fetchone()
            if not row or excerpt not in row["body"]:
                raise ProseStyleError("approved excerpt is absent from this project's accepted prose")
            if sha256(row["body"].encode("utf-8")).hexdigest() != row["body_hash"]:
                raise ProseStyleError("accepted source body has invalid hash")
            source_hash = row["body_hash"]
            kind = "approved_project_prose"

        digest = sha256(excerpt.encode("utf-8")).hexdigest()
        self.db.conn.execute(
            """INSERT INTO project_prose_style(
               project_id,reference_text,reference_sha256,source_kind,
               source_scope,source_body_hash,version)
               VALUES(?,?,?,?,?,?,1)
               ON CONFLICT(project_id) DO UPDATE SET
               reference_text=excluded.reference_text,
               reference_sha256=excluded.reference_sha256,
               source_kind=excluded.source_kind,
               source_scope=excluded.source_scope,
               source_body_hash=excluded.source_body_hash,
               version=project_prose_style.version+1,
               approved_at=CURRENT_TIMESTAMP""",
            (self.project_id, excerpt, digest, kind, accepted_scope, source_hash),
        )
        self.db.conn.commit()
        style = self.load()
        if style is None:
            raise ProseStyleError("approved style did not survive database write")
        return self._metadata(style)

    def load(self) -> ApprovedProseStyle | None:
        row = self.db.conn.execute(
            """SELECT reference_text,reference_sha256,source_kind,source_scope,
                      source_body_hash,version
               FROM project_prose_style WHERE project_id=?""",
            (self.project_id,),
        ).fetchone()
        if row is None:
            return None
        excerpt = row["reference_text"]
        if (not isinstance(excerpt, str) or not MIN_REFERENCE_CHARS <= len(excerpt) <= MAX_REFERENCE_CHARS
            or sha256(excerpt.encode("utf-8")).hexdigest() != row["reference_sha256"]):
            return None  # Fail closed if storage is tampered or corrupted.
        if row["source_kind"] == "approved_project_prose":
            if not row["source_scope"] or not row["source_body_hash"]:
                return None
            source = self.db.conn.execute(
                "SELECT body,body_hash FROM accepted_prose WHERE project_id=? AND scope_id=?",
                (self.project_id, row["source_scope"]),
            ).fetchone()
            if (source is None or source["body_hash"] != row["source_body_hash"]
                or sha256(source["body"].encode("utf-8")).hexdigest() != source["body_hash"]
                or excerpt not in source["body"]):
                return None  # Previous chapter revised/deleted: do not copy stale style.
        elif row["source_kind"] != "author_supplied":
            return None
        return ApprovedProseStyle(
            excerpt, row["reference_sha256"], int(row["version"]),
            row["source_kind"], row["source_scope"],
        )

    def status(self) -> dict:
        exists = self.db.conn.execute(
            "SELECT 1 FROM project_prose_style WHERE project_id=?",
            (self.project_id,),
        ).fetchone() is not None
        style = self.load()
        return (
            {**self._metadata(style), "active": True, "quality_proven": False}
            if style else {
                "active": False, "stored_but_stale_or_invalid": exists,
                "quality_proven": False, "automatic_style_training": False,
            }
        )

    def disable(self) -> bool:
        changed = self.db.conn.execute(
            "DELETE FROM project_prose_style WHERE project_id=?", (self.project_id,),
        ).rowcount > 0
        self.db.conn.commit()
        return changed

    @staticmethod
    def _metadata(style: ApprovedProseStyle) -> dict:
        return {
            "style_reference_sha256": style.sha256,
            "style_reference_chars": len(style.text),
            "style_reference_version": style.version,
            "style_reference_origin": style.source_kind,
            "style_reference_scope": style.source_scope,
            "automatic_style_training": False,
        }


def rejects_verbatim_copy(text: str, approved_reference: str) -> bool:
    """Bounded exact-span guard; prevents long verbatim imitation, not semantic plagiarism."""
    if not isinstance(text, str) or not approved_reference:
        return False
    source = re.sub(r"\s+", "", approved_reference)
    output = re.sub(r"\s+", "", text)
    if len(source) < COPY_GUARD_CHARS or len(output) < COPY_GUARD_CHARS:
        return False
    return any(source[i:i + COPY_GUARD_CHARS] in output
               for i in range(len(source) - COPY_GUARD_CHARS + 1))
