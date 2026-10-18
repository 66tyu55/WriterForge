"""Read-only, source-verified WriterForge lookup from the author's private R2.

The R2 vault stores immutable SQLite snapshots; it is NOT a mounted or live
database. Existing R2StudyVault.restore verifies snapshot pointer, manifest,
blobs, SQLite and source metadata before any search. The restored database
is opened strictly read-only, with a bounded XuehaiStore query. Returned rows
are source locators, NEVER reviewed literary technique claims.

No account secrets, text dumps, sqlite mutations, uploading, arbitrary bucket
names, or fallback to unverified web content.
"""
from __future__ import annotations
from hashlib import sha1, sha256
from pathlib import Path
from urllib.parse import quote
from dataclasses import dataclass
import re
import sqlite3

from .r2_storage import R2Config, R2StudyVault, R2StorageError
from .xuehai import Query, XuehaiStore
from .runtime import RuntimeEngine

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_TERM_BAD = re.compile(r"[%_\\\x00-\x1f]")
MAX_TERMS=4
MAX_ROWS=8


class R2RetrievalError(ValueError):
    pass


def _valid_terms(terms):
    if (not isinstance(terms, tuple) or not 1<=len(terms)<=MAX_TERMS
        or any(not isinstance(t,str) or not 2<=len(t.strip())<=32
               or t!=t.strip() or _TERM_BAD.search(t) for t in terms)):
        raise R2RetrievalError("R2_SEARCH_TERMS_INVALID_OR_UNBOUNDED")
    return tuple(dict.fromkeys(terms))


@dataclass(frozen=True)
class R2Lookup:
    library: str
    snapshot: str
    published_snapshot_id: int
    term: tuple[str,...]
    matches: tuple[dict,...]
    from_local_cache: bool
    catalog_edition_verified: bool = False
    private_source_blob_present: bool = False

    def public(self) -> dict:
        return {
            "format":"writerforge.r2-source-retrieval.v1",
            "provider":"Cloudflare R2",
            "library":self.library,
            "verified_r2_snapshot_sha256":self.snapshot,
            "published_xuehai_snapshot_id":self.published_snapshot_id,
            "search_terms":list(self.term),
            "matched_source_units":list(self.matches),
            "match_count":len(self.matches),
            "from_verified_local_cache":self.from_local_cache,
            "r2_manifest_blobs_and_sqlite_verified":True,
            "catalog_original_edition_verified":self.catalog_edition_verified,
            "private_source_blob_present":self.private_source_blob_present,
            "source_location_sha_crosschecked":True,
            "source_lexical_match_only":True,
            "literary_experience_semantics_verified":False,
            "independent_literary_review_performed":False,
            "skill_learning_promoted":False,
            "read_only":True,
        }


class _ReadOnlyDb:
    def __init__(self, conn):
        self.conn=conn
        self.fts_enabled=conn.execute(
            "SELECT EXISTS(SELECT 1 FROM sqlite_master "
            "WHERE name='xuehai_fts' AND type='table')"
        ).fetchone()[0]==1


class R2SourceGateway:
    """Explicitly configured private vault; no implicit provider selection."""
    def __init__(self, vault: R2StudyVault):
        if not isinstance(vault,R2StudyVault):
            raise R2RetrievalError("R2_VERIFIED_VAULT_REQUIRED")
        if vault.config.bucket!="writerforge-private-library":
            raise R2RetrievalError("R2_PRIVATE_LIBRARY_BUCKET_REQUIRED")
        self.vault=vault

    @classmethod
    def from_environment(cls):
        return cls(R2StudyVault(R2Config.from_environment()))

    def search(self, *, library:str, snapshot:str|None,
               terms:tuple[str,...], cache_dir:str|Path,limit:int=6)->R2Lookup:
        terms=_valid_terms(terms)
        if type(limit) is not int or not 1<=limit<=MAX_ROWS:
            raise R2RetrievalError("R2_SEARCH_LIMIT_INVALID")
        if snapshot is not None and (
            not isinstance(snapshot,str) or not _SHA.fullmatch(snapshot)):
            raise R2RetrievalError("R2_SNAPSHOT_SHA256_INVALID")
        # No unverified local SQLite path is ever accepted by the caller.
        restored=self.vault.restore(
            library=library,snapshot=snapshot,destination=cache_dir)
        if not restored.get("verified") or not _SHA.fullmatch(restored["snapshot"]):
            raise R2RetrievalError("R2_RESTORE_DID_NOT_VERIFY_PROVENANCE")
        dbpath=Path(restored["db"]).resolve()
        if not dbpath.is_file():
            raise R2RetrievalError("R2_STUDY_SQLITE_MISSING_AFTER_VERIFICATION")
        # mode=ro cannot write and is not WriterForgeDB (whose __init__
        # can migrate/schema-write). Keep mutation attempts fail-closed.
        uri="file:"+quote(str(dbpath),safe="/")+ "?mode=ro"
        conn=sqlite3.connect(uri,uri=True,cached_statements=32)
        conn.row_factory=sqlite3.Row
        try:
            conn.execute("PRAGMA query_only=ON")
            ok=conn.execute("PRAGMA quick_check").fetchone()
            if not ok or ok[0]!="ok":
                raise R2RetrievalError("R2_STUDY_SQLITE_CORRUPT")
            sid=conn.execute(
                "SELECT id FROM snapshots WHERE status='published' "
                "ORDER BY id DESC LIMIT 1").fetchone()
            if sid is None:
                raise R2RetrievalError("R2_NO_PUBLISHED_XUEHAI_SNAPSHOT")
            snap_id=int(sid["id"])
            works=conn.execute("SELECT work_id,source_sha256 FROM studied_works").fetchall()
            if not works or len(works)>16:
                raise R2RetrievalError("R2_STUDIED_WORK_COUNT_UNEXPECTED")
            source_digests={x["work_id"]:x["source_sha256"] for x in works}
            # R2 integrity is NOT the same as independently verified original
            # provenance. For strictly catalogued public-domain books, recheck
            # the exact upstream Git blob and study-decoded full-source hash.
            from .classics_catalog import CATALOG
            catalog_edition_verified=False
            known=next((b for b in CATALOG.values()
                        if b.library==library),None)
            if known:
                source_path=restored.get("source")
                if (not source_path or
                    known.work_id not in source_digests or
                    len(source_digests)!=1):
                    raise R2RetrievalError("R2_CATALOG_SOURCE_BLOB_MISSING_OR_WRONG_WORK")
                raw=Path(source_path).read_bytes()
                git=sha1(f"blob {len(raw)}\0".encode("ascii")+raw).hexdigest()
                if git!=known.git_blob_sha1:
                    raise R2RetrievalError("R2_ORIGINAL_CATALOG_EDITION_CHANGED")
                decoded_sha=sha256(raw.decode("utf-8-sig").encode("utf-8")).hexdigest()
                if decoded_sha!=source_digests[known.work_id]:
                    raise R2RetrievalError("R2_ORIGINAL_TEXT_AND_STUDIED_WORK_DISAGREE")
                catalog_edition_verified=True
            rt=RuntimeEngine()
            rt.enter_write(snap_id)
            # Source terms are lexical search; existing WF Xuehai retrieval
            # handles bounded rank and per-work diversity.
            query=Query(text_terms=terms,limit=limit,
                        max_per_work=limit,max_per_cluster=limit)
            candidates=XuehaiStore(_ReadOnlyDb(conn),rt).query(query)
            result=[]
            for record in candidates:
                excerpt=record["evidence_excerpt"]
                if not any(t.casefold() in excerpt.casefold() for t in terms):
                    continue
                work_id=record["work_id"]
                location=record["location"]
                span=conn.execute(
                    "SELECT excerpt,source_sha256 FROM source_spans "
                    "WHERE work_id=? AND chapter=? AND paragraph=? AND sentence=?",
                    (work_id,*location),
                ).fetchone()
                if span is None or span["excerpt"][:80]!=excerpt:
                    raise R2RetrievalError("R2_SOURCE_SPAN_CROSSCHECK_FAILED")
                if (work_id not in source_digests or
                    not _SHA.fullmatch(str(source_digests[work_id])) or
                    not _SHA.fullmatch(str(span["source_sha256"]))):
                    raise R2RetrievalError("R2_SOURCE_HASH_PROVENANCE_INVALID")
                result.append({
                    "work_id":work_id,
                    "work_original_sha256":source_digests[work_id],
                    "location":location,
                    "source_unit_sha256":span["source_sha256"],
                    "source_excerpt":excerpt[:80],
                    "excerpt_complete_unit_not_guaranteed":True,
                    "evidence_class":"PINNED_ORIGINAL_SOURCE_LEXICAL_ONLY",
                    "source_role":record["function"],
                    "literary_method_review_status":"UNVERIFIED",
                })
                if len(result)>=limit:
                    break
            return R2Lookup(
                library=restored["library"],snapshot=restored["snapshot"],
                published_snapshot_id=snap_id,term=terms,matches=tuple(result),
                from_local_cache=bool(restored["from_local_cache"]),
                catalog_edition_verified=catalog_edition_verified,
                private_source_blob_present=bool(restored.get("source")))
        finally:
            conn.close()
