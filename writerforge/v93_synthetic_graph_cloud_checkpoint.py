"""V93 bounded R2 CAS cold checkpoint for SYNTHETIC WF relation state only.

This is an honest end-to-end rehearsal of WriterForgeDB + FactJournal
persistence. V92 real experience blobs are linked by SHA but NOT rewritten.
No real production knowledge graph has been found in the Railway service:
the existing service has no mounted persistent volume. Never manufacture an
apparently real graph from the R2 literary note history.

SECURITY: this version may publish ONLY a tightly whitelisted synthetic
fixture; production SQLite upload is explicitly unsupported until the owner
provides a genuine source, quiescence, privacy and key-rotation design.
Raw synthetic databases are compressed and stored as immutable private R2
index chunks; no hidden model credentials or literary text in logs.
No model calls, no database graph replacement or skill promotion.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sqlite3
import zlib

from .v91_lifelong_checkpoint import (
    FILE_NAMES, canonical, digest, is_sha, verify_checkpoint,
    _audit_db, _check_path, V91MemoryCheckpointError,
)

FORMAT="writerforge.lifelong.synthetic-graph-r2.v93"
VERSION=1
KIND="SYNTHETIC_TEST_ONLY"
V92_EXPERIENCE_CHAIN_SHA="bd905ae9e812fb5283f24ed7fec3bc35cf0febde7b6405476c455bba468f84db"
FIXTURE_ID="v93_synthetic_relations"
FIXTURE_WORK_URI="test://writerforge/v93/synthetic-only"
FIXTURE_QUOTE="守桥人合上木牌，少年并不能据此知道真正的因果原因。"
MAX_FILE_BYTES=8*1024*1024
MAX_COMPRESSED_BYTES=8*1024*1024
PART_BYTES=128*1024
MAX_CHUNKS_PER_FILE=64
MAX_MANIFEST_BYTES=64*1024
FILE_ORDER=tuple(FILE_NAMES)
HEADER_KEYS=frozenset((
    "format","schema_version","snapshot_kind","checkpoint_id",
    "v91_local_manifest","v91_local_manifest_sha256",
    "v92_real_experience_manifest_sha256","files",
    "all_user_originals_excluded","production_graph_migrated",
    "reviewer_identity_independently_verified",
    "next_training_unlocked","literary_semantics_verified",
    "no_model_called","no_source_text_in_public_receipt",
))
FILE_META_KEYS=frozenset((
    "plain_sha256","plain_bytes","compressed_sha256",
    "compressed_bytes","parts"))
PART_META_KEYS=frozenset(("sha256","bytes"))


class V93CloudGraphError(ValueError):
    pass


def require(ok,code):
    if not ok:
        raise V93CloudGraphError(code)


def _read_json(raw, *, max_length=MAX_MANIFEST_BYTES):
    require(type(raw) is bytes and 0<len(raw)<=max_length,
            "WF93_METADATA_BYTE_BOUND")
    try:
        text=raw.decode("utf8","strict")
        require("\ufffd" not in text,"WF93_REPLACEMENT_CHAR_FORBIDDEN")
        def pairs(items):
            value={}
            for k,v in items:
                if k in value:
                    raise ValueError("duplicate field")
                value[k]=v
            return value
        doc=json.loads(text,object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(
                           ValueError("invalid number")))
        canonical(doc)
    except (UnicodeError,ValueError,TypeError,OverflowError):
        raise V93CloudGraphError("WF93_STRICT_METADATA_DECODE_FAILED") from None
    require(type(doc) is dict,"WF93_METADATA_NOT_OBJECT")
    return doc


def _database_uri(path):
    from urllib.parse import quote
    return "file:"+quote(str(Path(path).resolve()),safe="/:")+"?mode=ro"


def _verify_synthetic_origin(writer_db,fact_db):
    """Refuse a real user DB even if its checkpoint digests look valid."""
    for f in (writer_db,fact_db):
        require(Path(f).is_file() and not Path(f).is_symlink(),
                "WF93_SYNTHETIC_DATABASE_NOT_REGULAR_FILE")
    # These are the ONLY user-content tables permitted to have rows in
    # the cloud rehearsal. Any extra story, preference, training trace, or
    # legacy source is a production-data contamination: refuse upload.
    permitted_writer_rows={
        "snapshots","studied_works","studied_chapters","source_spans",
        "experience_candidates","experience_approvals",
        "experience_revocations","experience_decisions",
    }
    permitted_fact_rows={
        "fact_events","temporal_claims","story_scenes","story_subjects",
        "event_import_receipts","journal_cursor_keys",
        "ledger_operations","ledger_bootstrap",
    }

    def enforce_only_fixture_rows(db,permitted):
        names=[r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        for table in names:
            if (table.startswith("sqlite_") or
                table.startswith("xuehai_fts_")):
                continue
            if table not in permitted:
                require(db.execute(
                    'SELECT COUNT(*) FROM "'+table+'"'
                    ).fetchone()[0]==0,
                    "WF93_UNEXPECTED_OTHER_USER_DATA_REFUSED")
    with closing(sqlite3.connect(_database_uri(writer_db),uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        enforce_only_fixture_rows(db,permitted_writer_rows)
        works=db.execute(
            "SELECT work_id,source_uri FROM studied_works").fetchall()
        quotes=db.execute(
            "SELECT excerpt FROM source_spans").fetchall()
        candidate_count=db.execute(
            "SELECT COUNT(*) FROM experience_candidates").fetchone()[0]
        approval_count=db.execute(
            "SELECT COUNT(*) FROM experience_approvals").fetchone()[0]
        revoke_count=db.execute(
            "SELECT COUNT(*) FROM experience_revocations").fetchone()[0]
        decisions=db.execute(
            "SELECT plan_json FROM experience_decisions").fetchall()
        require(works==[(FIXTURE_ID,FIXTURE_WORK_URI)] and
                quotes==[(FIXTURE_QUOTE,)] and
                candidate_count==1 and approval_count==1 and
                revoke_count==1 and len(decisions)==2,
                "WF93_REAL_OR_UNRECOGNIZED_PRODUCTION_DB_REFUSED")
        require(all(len(x[0])<8192 and
                    "lesson_v93" in x[0] for x in decisions),
                "WF93_FIXTURE_DECISION_SET_MISMATCH")
    with closing(sqlite3.connect(_database_uri(fact_db),uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        enforce_only_fixture_rows(db,permitted_fact_rows)
        scenes=db.execute("SELECT story_id,scene_id FROM story_scenes "
                          "ORDER BY scene_id").fetchall()
        if len(scenes)!=2 or any(s[0]!=FIXTURE_ID for s in scenes):
            raise V93CloudGraphError("WF93_UNKNOWN_FACTJOURNAL_STORY")
        for table,n in (("fact_events",1),("temporal_claims",1)):
            require(db.execute(f'SELECT COUNT(*) FROM "{table}"'
                               ).fetchone()[0]==n,
                    "WF93_SYNTHETIC_FACTJOURNAL_CONTENT_INVALID")


def _part_chunks(raw):
    require(type(raw) is bytes and 0<len(raw)<=MAX_COMPRESSED_BYTES,
            "WF93_COMPRESSED_DATA_LIMIT")
    pieces=[raw[i:i+PART_BYTES] for i in range(0,len(raw),PART_BYTES)]
    require(1<=len(pieces)<=MAX_CHUNKS_PER_FILE,
            "WF93_PART_COUNT_BUDGET_EXCEEDED")
    return pieces


def build_private_synthetic_package(root):
    """Create bounded CAS objects + a LAST-published metadata manifest."""
    root=Path(root)
    try:
        proof=verify_checkpoint(root)
    except V91MemoryCheckpointError:
        raise V93CloudGraphError(
            "WF93_LOCAL_CHECKPOINT_INTEGRITY_NOT_VERIFIED") from None
    folder=root/"checkpoints"/proof["checkpoint_id"]
    files=[folder/n for n in FILE_ORDER]
    _verify_synthetic_origin(*files)
    v91_raw=(folder/"manifest.json").read_bytes()
    require(len(v91_raw)<=MAX_MANIFEST_BYTES,
            "WF93_LOCAL_V91_MANIFEST_OVERSIZED")
    # Existing V91 checkpoint verifier validates the local manifest and DBs.
    local=_read_json(v91_raw)
    parts={}
    file_metadata={}
    for name,path in zip(FILE_ORDER,files):
        identity=_check_path(path)
        require(identity["bytes"]<=MAX_FILE_BYTES,
                "WF93_SQLITE_UNCOMPRESSED_BUDGET_EXCEEDED")
        raw=path.read_bytes()
        compressed=zlib.compress(raw,level=9)
        chunks=_part_chunks(compressed)
        for block in chunks:
            key=digest(block)
            require(key not in parts or parts[key]==block,
                    "WF93_CAS_SHA_COLLISION")
            parts[key]=block
        file_metadata[name]={
            "plain_sha256":identity["sha256"],
            "plain_bytes":identity["bytes"],
            "compressed_sha256":digest(compressed),
            "compressed_bytes":len(compressed),
            "parts":[{"sha256":digest(chunk),"bytes":len(chunk)}
                     for chunk in chunks],
        }
    manifest={
        "format":FORMAT,"schema_version":VERSION,"snapshot_kind":KIND,
        "checkpoint_id":proof["checkpoint_id"],
        "v91_local_manifest":local,
        "v91_local_manifest_sha256":digest(v91_raw),
        "v92_real_experience_manifest_sha256":V92_EXPERIENCE_CHAIN_SHA,
        "files":file_metadata,
        "all_user_originals_excluded":True,
        "production_graph_migrated":False,
        "reviewer_identity_independently_verified":False,
        "next_training_unlocked":False,
        "literary_semantics_verified":False,
        "no_model_called":True,
        "no_source_text_in_public_receipt":True,
    }
    document=canonical(manifest)
    require(len(document)<=MAX_MANIFEST_BYTES,
            "WF93_CLOUD_MANIFEST_BUDGET_EXCEEDED")
    return document,parts


def _validate_envelope(raw):
    doc=_read_json(raw)
    require(set(doc)==HEADER_KEYS and
            doc["format"]==FORMAT and
            type(doc["schema_version"]) is int and
            doc["schema_version"]==VERSION and
            doc["snapshot_kind"]==KIND and
            doc["v92_real_experience_manifest_sha256"]==
                V92_EXPERIENCE_CHAIN_SHA and
            doc["all_user_originals_excluded"] is True and
            doc["production_graph_migrated"] is False and
            doc["reviewer_identity_independently_verified"] is False and
            doc["next_training_unlocked"] is False and
            doc["literary_semantics_verified"] is False and
            doc["no_model_called"] is True and
            doc["no_source_text_in_public_receipt"] is True,
            "WF93_ENVELOPE_VERSION_OR_AUTHORITY_INVALID")
    from .v91_lifelong_checkpoint import ID
    require(type(doc["checkpoint_id"]) is str and
            ID.fullmatch(doc["checkpoint_id"]) is not None and
            type(doc["files"]) is dict and
            set(doc["files"])==set(FILE_ORDER) and
            type(doc["v91_local_manifest"]) is dict and
            is_sha(doc["v91_local_manifest_sha256"]) and
            digest(canonical(doc["v91_local_manifest"]))==
                doc["v91_local_manifest_sha256"],
            "WF93_CLOUD_LOCAL_CHECKPOINT_MANIFEST_INVALID")
    for name in FILE_ORDER:
        file=doc["files"][name]
        require(type(file) is dict and set(file)==FILE_META_KEYS and
                all(is_sha(file[x]) for x in
                    ("plain_sha256","compressed_sha256")) and
                type(file["plain_bytes"]) is int and
                0<file["plain_bytes"]<=MAX_FILE_BYTES and
                type(file["compressed_bytes"]) is int and
                0<file["compressed_bytes"]<=MAX_COMPRESSED_BYTES and
                type(file["parts"]) is list and
                1<=len(file["parts"])<=MAX_CHUNKS_PER_FILE,
                "WF93_CLOUD_FILE_METADATA_INVALID")
        for x in file["parts"]:
            require(type(x) is dict and set(x)==PART_META_KEYS and
                    is_sha(x["sha256"]) and
                    type(x["bytes"]) is int and
                    0<x["bytes"]<=PART_BYTES,
                    "WF93_CLOUD_CHUNK_DESCRIPTOR_INVALID")
        require(sum(x["bytes"] for x in file["parts"])==
                    file["compressed_bytes"],
                "WF93_CLOUD_COMPRESSED_SIZE_MISMATCH")
    return doc


def _inflate(compressed,expected):
    require(digest(compressed)==expected["compressed_sha256"] and
            len(compressed)==expected["compressed_bytes"],
            "WF93_COMPRESSED_BYTES_HASH_CHANGED")
    try:
        inflater=zlib.decompressobj()
        payload=inflater.decompress(compressed,MAX_FILE_BYTES+1)
        require(len(payload)<=MAX_FILE_BYTES and inflater.eof and
                not inflater.unused_data and
                not inflater.unconsumed_tail,
                "WF93_DECOMPRESSION_LIMIT_OR_TRAILING_DATA")
        payload+=inflater.flush(MAX_FILE_BYTES+1-len(payload))
    except zlib.error:
        raise V93CloudGraphError("WF93_INVALID_COMPRESSED_CHECKPOINT") from None
    require(len(payload)==expected["plain_bytes"] and
            digest(payload)==expected["plain_sha256"],
            "WF93_INFLATED_SQLITE_HASH_CHANGED")
    return payload


def publish_to_cas(journal,*,manifest_raw,parts):
    """Append chunks, verify each readback, then immutable manifest LAST.

    DO NOT call this in production mode with real user SQLite in V93.
    """
    _validate_envelope(manifest_raw)
    require(isinstance(parts,dict) and parts,
            "WF93_NO_PARTS_TO_UPLOAD")
    expected={part["sha256"] for f in
              _read_json(manifest_raw)["files"].values()
              for part in f["parts"]}
    require(set(parts)==expected,"WF93_CHUNK_SET_NOT_EXACT")
    require(journal.read_only is False and bool(journal.writer),
            "WF93_CLOUD_WRITER_ROLE_REQUIRED")
    uploaded=[]
    for chunk_sha in sorted(parts):
        raw=parts[chunk_sha]
        require(type(raw) is bytes and
                0<len(raw)<=PART_BYTES and
                digest(raw)==chunk_sha,
                "WF93_CHUNK_CONTENT_INVALID")
        remote,created=journal._put_content(raw)
        require(remote==chunk_sha and
                journal._get_content(remote)==raw,
                "WF93_REMOTE_CHUNK_IMMEDIATE_READBACK_FAILED")
        uploaded.append({"sha256":remote,"created":bool(created)})
    manifest_sha=digest(manifest_raw)
    actual,created=journal._put_content(manifest_raw)
    require(actual==manifest_sha and
            journal._get_content(actual)==manifest_raw,
            "WF93_CLOUD_MANIFEST_PUBLISH_FAILURE")
    return {
        "status":"WF93_SYNTHETIC_RELATIONAL_GRAPH_CAS_PUBLISHED",
        "manifest_sha256":manifest_sha,
        "immutable_chunk_count":len(uploaded),
        "new_chunk_count":sum(int(x["created"]) for x in uploaded),
        "new_manifest_created":bool(created),
        "only_synthetic_data":True,
        "production_graph_migrated":False,
        "no_user_novel_or_history_ever_written":True,
        "r2_legacy_v92_experience_chain_untouched":True,
        "independent_cold_reader_verification_pending":True,
        "new_model_calls":0,
    }


def cold_restore_from_cas(reader,*,manifest_sha,restore_parent):
    """Cold read all R2 chunks, reconstruct BOTH SQLite DBs in a fresh tree.

    V91 verify_checkpoint compares original SQLite file SHA, schema, logical
    table hashes and foreign key checks. Synthetic fixture guard is repeated
    after restoration. A pinned SHA is required; no mutable 'latest' claim.
    """
    require(is_sha(manifest_sha),"WF93_MANIFEST_PIN_INVALID")
    require(reader.read_only and reader.writer is None,
            "WF93_COLD_READER_MUST_NOT_HOLD_WRITER_ROLE")
    raw=reader._get_content(manifest_sha)
    require(digest(raw)==manifest_sha,
            "WF93_REMOTE_MANIFEST_CAS_NOT_PINNED")
    doc=_validate_envelope(raw)
    target=Path(restore_parent)
    require(target.exists() and target.is_dir() and
            not target.is_symlink() and
            not any(target.iterdir()),
            "WF93_PRIVATE_RESTORE_TARGET_NOT_EMPTY")
    folder=target/"checkpoints"/doc["checkpoint_id"]
    folder.mkdir(parents=True,exist_ok=False)
    for name in FILE_ORDER:
        spec=doc["files"][name]
        pieces=[]
        for part in spec["parts"]:
            blob=reader._get_content(part["sha256"])
            require(digest(blob)==part["sha256"] and
                    len(blob)==part["bytes"],
                    "WF93_REMOTE_CHECKPOINT_PART_CHANGED")
            pieces.append(blob)
        inflated=_inflate(b"".join(pieces),spec)
        (folder/name).write_bytes(inflated)
    (folder/"manifest.json").write_bytes(
        canonical(doc["v91_local_manifest"]))
    (target/"CURRENT").write_bytes(canonical({
        "format":"writerforge.lifelong-memory.current-pointer.v91",
        "checkpoint_id":doc["checkpoint_id"],
        "manifest_sha256":doc["v91_local_manifest_sha256"],
    }))
    verification=verify_checkpoint(target)
    require(verification["checkpoint_id"]==doc["checkpoint_id"],
            "WF93_RESTORED_POINTER_ID_CHANGED")
    _verify_synthetic_origin(
        folder/FILE_ORDER[0],folder/FILE_ORDER[1])
    return {
        "status":"WF93_SYNTHETIC_RELATIONAL_GRAPH_CLOUD_COLD_VERIFIED",
        "manifest_sha256":manifest_sha,
        "checkpoint_id":doc["checkpoint_id"],
        "sqlite_files_restored":len(FILE_ORDER),
        "critical_tables_verified":verification["critical_tables_verified"],
        "source_experience_v92_manifest_sha256":
            V92_EXPERIENCE_CHAIN_SHA,
        "reconstructed_database_files":[str(folder/x) for x in FILE_ORDER],
        "production_graph_migrated":False,
        "independent_literary_semantics_verified":False,
        "model_calls":0,"r2_writes":0,
    }
