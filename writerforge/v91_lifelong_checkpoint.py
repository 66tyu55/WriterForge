"""V91 private on-disk cold checkpoint of EXISTING WriterForge+FactJournal.

This is a verifiable LOCAL recovery primitive, not a deployed R2 backup or
cross-database atomic transaction. Copy the existing two SQLite DBs using
SQLite's WAL-safe online backup, compare schemas and bounded streaming
logical table digests, publish a manifest LAST, and keep the previous valid
CURRENT pointer on any failure.

No model, no network, no original paragraphs in the public JSON receipt.
The encrypted/private destination and separately approved R2 publication
remain the caller's responsibility. Fail closed on unsupported versions.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
from pathlib import Path
from tempfile import mkdtemp
from urllib.parse import quote
import fcntl
import json
import math
import os
import re
import shutil
import sqlite3

from .db import WriterForgeDB
from .fact_journal import FactJournal
from .runtime import Mode, RuntimeEngine

FORMAT="writerforge.lifelong-memory.local-checkpoint.v91"
POINTER_FORMAT="writerforge.lifelong-memory.current-pointer.v91"
SCHEMA_VERSION=1
FILE_NAMES=("writerforge.sqlite3","fact-journal.sqlite3")
MEMORY_TABLES={
    FILE_NAMES[0]:(
        "snapshots","studied_works","studied_chapters","source_spans",
        "experience_candidates","experience_approvals",
        "experience_revocations","experience_decisions",
        "experience_postwrites","experience_legacy_refs",
        "experience_evidence_links","experience_literary_reviews",
        "wf_anchor_failure_receipts",
    ),
    FILE_NAMES[1]:(
        "fact_events","fact_links","pattern_versions","temporal_claims",
        "story_scenes","story_subjects","reader_disclosures",
        "ledger_operations",
    ),
}
MAX_DB_FILE_BYTES=256*1024*1024
MAX_ROW_BYTES=2*1024*1024
MAX_MANIFEST_BYTES=128*1024
MAX_POINTER_BYTES=4096
MAX_ROWS_PER_TABLE=5_000_000
SHA=re.compile(r"[0-9a-f]{64}\Z")
ID=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,79}\Z")
R2_POINTER_FIELDS=frozenset(("batch","journal","experience"))


class V91MemoryCheckpointError(ValueError):
    pass


def require(ok,code):
    if not ok:
        raise V91MemoryCheckpointError(code)


def canonical(doc):
    return json.dumps(doc,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf8")


def digest(raw):
    return sha256(raw).hexdigest()


def is_sha(value):
    return isinstance(value,str) and SHA.fullmatch(value) is not None


def _json_strict(raw,max_bytes):
    require(isinstance(raw,bytes) and 0<len(raw)<=max_bytes,
            "WF91_RESTORE_JSON_BYTES_INVALID")
    try:
        decoded=raw.decode("utf8","strict")
        require("\ufffd" not in decoded,
                "WF91_RESTORE_REPLACEMENT_CHAR")
        def parse_pairs(pairs):
            doc={}
            for k,v in pairs:
                if k in doc:
                    raise V91MemoryCheckpointError(
                        "WF91_RESTORE_DUPLICATE_JSON_FIELD")
                doc[k]=v
            return doc
        def bad_constant(_):
            raise V91MemoryCheckpointError("WF91_NONFINITE_JSON")
        doc=json.loads(decoded,object_pairs_hook=parse_pairs,
                       parse_constant=bad_constant)
        canonical(doc)
    except (UnicodeError,ValueError,TypeError,OverflowError):
        raise V91MemoryCheckpointError(
            "WF91_RESTORE_JSON_INVALID_OR_GARBLED") from None
    require(isinstance(doc,dict),"WF91_RESTORE_DOCUMENT_NOT_OBJECT")
    return doc


def _fsync_file(path):
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_dir(path):
    # Only POSIX/Linux local file systems are implemented in V91.
    fd=os.open(str(path),os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _check_path(path):
    require(path.is_file() and not path.is_symlink(),
            "WF91_MISSING_OR_SYMLINKED_BUNDLE_FILE")
    length=path.stat().st_size
    require(0<length<=MAX_DB_FILE_BYTES,
            "WF91_CHECKPOINT_FILE_SIZE_EXCEEDED")
    h=sha256()
    with path.open("rb") as stream:
        while block:=stream.read(1024*1024):
            h.update(block)
    return {"bytes":length,"sha256":h.hexdigest()}


def _cell(value):
    if value is None or type(value) in (int,bool):
        return value
    if type(value) is float:
        require(math.isfinite(value),"WF91_NONFINITE_SQLITE_VALUE")
        return value
    if type(value) is str:
        require("\ufffd" not in value,
                "WF91_SQLITE_REPLACEMENT_CHARACTER")
        try:
            raw=value.encode("utf8","strict")
            require(len(raw)<=MAX_ROW_BYTES,
                    "WF91_SQLITE_TEXT_TOO_LARGE")
            raw.decode("utf8","strict")
        except UnicodeError:
            raise V91MemoryCheckpointError(
                "WF91_SQLITE_CORRUPT_UTF8") from None
        return value
    if isinstance(value,bytes):
        require(len(value)<=MAX_ROW_BYTES,
                "WF91_SQLITE_BINARY_CELL_TOO_LARGE")
        return {"blob_sha256":digest(value),"bytes":len(value)}
    raise V91MemoryCheckpointError("WF91_SQLITE_UNSUPPORTED_CELL_TYPE")


def _audit_db(path,kind):
    require(kind in MEMORY_TABLES,"WF91_UNKNOWN_DATABASE_KIND")
    conn_uri="file:"+quote(str(path.resolve()),safe="/:")+"?mode=ro"
    try:
        with closing(sqlite3.connect(conn_uri,uri=True,timeout=12)) as db:
            db.execute("PRAGMA query_only=ON")
            require(db.execute("PRAGMA quick_check").fetchone()==("ok",),
                    "WF91_SQLITE_QUICK_CHECK_FAILED")
            require(db.execute("PRAGMA foreign_key_check").fetchone() is None,
                    "WF91_SQLITE_FOREIGN_KEY_FAILURE")
            schema=db.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master "
                "WHERE sql IS NOT NULL ORDER BY type,name,tbl_name").fetchall()
            names={r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            require(set(MEMORY_TABLES[kind]).issubset(names),
                    "WF91_REQUIRED_MEMORY_TABLE_MISSING")
            tables={}
            for table in MEMORY_TABLES[kind]:
                # Every name comes from the static allowlist, never the input.
                cursor=db.execute(f'SELECT * FROM "{table}" ORDER BY rowid')
                hash_state=sha256()
                count=0
                for raw_row in cursor:
                    count+=1
                    require(count<=MAX_ROWS_PER_TABLE,
                            "WF91_MEMORY_TABLE_ROW_BUDGET_EXCEEDED")
                    row=[_cell(x) for x in raw_row]
                    encoded=canonical(row)
                    require(len(encoded)<=MAX_ROW_BYTES,
                            "WF91_LOGICAL_ROW_UNBOUNDED")
                    hash_state.update(len(encoded).to_bytes(4,"big"))
                    hash_state.update(encoded)
                tables[table]={
                    "rows":count,
                    "logical_sha256":hash_state.hexdigest(),
                }
            return {
                "quick_check":"ok",
                "foreign_key_check":"ok",
                "schema_sha256":digest(canonical(schema)),
                "required_table_count":len(tables),
                "memory_table_digests":tables,
                "human_literary_accuracy_checked":False,
            }
    except sqlite3.DatabaseError:
        raise V91MemoryCheckpointError(
            "WF91_SQLITE_READONLY_RESTORE_FAILED") from None


def _read_document(path,limit):
    require(path.is_file() and not path.is_symlink()
            and 0<path.stat().st_size<=limit,
            "WF91_MANIFEST_OR_POINTER_MISSING")
    return _json_strict(path.read_bytes(),limit)


def _valid_anchors(anchors):
    require(type(anchors) is dict and set(anchors)==R2_POINTER_FIELDS
            and all(is_sha(x) for x in anchors.values()),
            "WF91_EXTERNAL_R2_ANCHORS_INVALID")


def _manifest_receipt(doc):
    require(type(doc) is dict and
            doc.get("format")==FORMAT and
            type(doc.get("schema_version")) is int and
            doc["schema_version"]==SCHEMA_VERSION and
            type(doc.get("checkpoint_id")) is str and
            ID.fullmatch(doc["checkpoint_id"]) is not None,
            "WF91_UNKNOWN_OR_UNSUPPORTED_CHECKPOINT_VERSION")
    allowed={
        "format","schema_version","checkpoint_id","previous_manifest_sha256",
        "local_sqlite_files","r2_v82_legacy_anchors",
        "live_cross_database_atomicity_proven","external_r2_verified_this_run",
        "literary_growth_independently_verified","write_skill_unlocked",
        "manifest_sha256",
    }
    require(set(doc)==allowed and
            (doc["previous_manifest_sha256"] is None or
             is_sha(doc["previous_manifest_sha256"])) and
            doc["live_cross_database_atomicity_proven"] is False and
            doc["external_r2_verified_this_run"] is False and
            doc["literary_growth_independently_verified"] is False and
            doc["write_skill_unlocked"] is False,
            "WF91_CHECKPOINT_UNKNOWN_FIELDS_OR_FAKE_PROMOTION")
    _valid_anchors(doc["r2_v82_legacy_anchors"])
    files=doc["local_sqlite_files"]
    require(type(files) is dict and set(files)==set(FILE_NAMES),
            "WF91_BUNDLE_FILES_INCOMPLETE")
    for name in FILE_NAMES:
        info=files[name]
        require(type(info) is dict and
                set(info)=={"bytes","sha256","sqlite_audit"} and
                type(info["bytes"]) is int and
                0<info["bytes"]<=MAX_DB_FILE_BYTES and
                is_sha(info["sha256"]) and
                isinstance(info["sqlite_audit"],dict),
                "WF91_BUNDLE_FILE_METADATA_INVALID")
    content={k:v for k,v in doc.items() if k!="manifest_sha256"}
    require(is_sha(doc["manifest_sha256"]) and
            digest(canonical(content))==doc["manifest_sha256"],
            "WF91_BUNDLE_MANIFEST_HASH_MISMATCH")
    return doc


def _read_pointer(root):
    file=root/"CURRENT"
    if not file.exists():
        return None
    data=_read_document(file,MAX_POINTER_BYTES)
    require(set(data)=={
        "format","checkpoint_id","manifest_sha256"} and
        data["format"]==POINTER_FORMAT and
        isinstance(data["checkpoint_id"],str) and
        ID.fullmatch(data["checkpoint_id"]) is not None and
        is_sha(data["manifest_sha256"]),
        "WF91_CURRENT_POINTER_INVALID")
    return data


def verify_checkpoint(root,*,checkpoint_id=None):
    """Separate read-only verifier. Full file SHA AND logical table digests."""
    root=Path(root)
    ptr=_read_pointer(root)
    require(ptr is not None,"WF91_NO_PUBLISHED_CHECKPOINT")
    if checkpoint_id is not None:
        require(checkpoint_id==ptr["checkpoint_id"],
                "WF91_REQUESTED_CHECKPOINT_NOT_CURRENT")
    folder=root/"checkpoints"/ptr["checkpoint_id"]
    require(folder.is_dir() and not folder.is_symlink(),
            "WF91_CHECKPOINT_DIRECTORY_NOT_FOUND")
    doc=_manifest_receipt(
        _read_document(folder/"manifest.json",MAX_MANIFEST_BYTES))
    require(doc["checkpoint_id"]==ptr["checkpoint_id"] and
            doc["manifest_sha256"]==ptr["manifest_sha256"],
            "WF91_POINTER_MANIFEST_MISMATCH")
    for name in FILE_NAMES:
        path=folder/name
        basic=_check_path(path)
        require(all(basic[key]==doc["local_sqlite_files"][name][key]
                    for key in ("sha256","bytes")),
                "WF91_CHECKPOINT_SQLITE_BYTE_SHA_CHANGED")
        audit=_audit_db(path,name)
        require(audit==doc["local_sqlite_files"][name]["sqlite_audit"],
                "WF91_CHECKPOINT_MEMORY_LOGICAL_DRIFT")
    require(_read_pointer(root)==ptr,
            "WF91_CHECKPOINT_CHANGED_DURING_COLD_READ")
    return {
        "status":"WF91_COLD_CHECKPOINT_CONTENT_VERIFIED",
        "checkpoint_id":ptr["checkpoint_id"],
        "manifest_sha256":ptr["manifest_sha256"],
        "files_verified":len(FILE_NAMES),
        "critical_tables_verified":sum(len(
            doc["local_sqlite_files"][n]["sqlite_audit"][
                "memory_table_digests"]) for n in FILE_NAMES),
        "table_row_counts":{n:{t:s["rows"] for t,s in
           doc["local_sqlite_files"][n]["sqlite_audit"][
               "memory_table_digests"].items()} for n in FILE_NAMES},
        "r2_anchors_pinned_not_fetched":True,
        "cross_db_atomicity_not_proven":True,
        "literary_quality_independently_verified":False,
        "model_calls":0,"r2_network_calls":0,"r2_writes":0,
        "raw_private_rows_exposed_in_receipt":False,
    }


def _backup_sqlite(source,destination):
    require(not source.in_transaction,"WF91_OPEN_SQLITE_TRANSACTION_REFUSED")
    with closing(sqlite3.connect(str(destination))) as copy:
        source.backup(copy,pages=64,sleep=0.01)
        copy.commit()
    _fsync_file(destination)
    _check_path(destination)


def create_checkpoint(*,root,checkpoint_id,writer:WriterForgeDB,
                      facts:FactJournal,runtime:RuntimeEngine,
                      r2_v82_anchors,failpoint=None):
    """Manifest-last local checkpoint, old CURRENT preserved on interruption.

    Requires caller-enforced quiescence and IDLE state. Two independent
    databases cannot be proved cross-database atomic by this primitive.
    """
    require(isinstance(writer,WriterForgeDB) and
            isinstance(facts,FactJournal) and
            isinstance(runtime,RuntimeEngine),
            "WF91_EXISTING_DATABASES_REQUIRED")
    runtime.require(Mode.IDLE)
    require(isinstance(checkpoint_id,str) and
            ID.fullmatch(checkpoint_id) is not None,
            "WF91_CHECKPOINT_ID_INVALID")
    _valid_anchors(r2_v82_anchors)
    require(failpoint in (None,"BEFORE_MANIFEST",
                          "AFTER_DIRECTORY_BEFORE_CURRENT"),
            "WF91_UNRECOGNIZED_TEST_FAILPOINT")
    root=Path(root)
    require(not root.is_symlink(),
            "WF91_CHECKPOINT_ROOT_SYMLINK_REFUSED")
    root.mkdir(parents=True,exist_ok=True)
    (root/"checkpoints").mkdir(exist_ok=True)
    lockfile=root/".writerforge-memory.lock"
    with lockfile.open("a+b") as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        oldptr=_read_pointer(root)
        if oldptr is not None:
            verify_checkpoint(root)
        final=root/"checkpoints"/checkpoint_id
        require(not final.exists(),
                "WF91_IMMUTABLE_CHECKPOINT_ALREADY_EXISTS")
        tmp=Path(mkdtemp(prefix=".wf91-staged-",dir=root/"checkpoints"))
        published=False
        try:
            writer_conn=writer.conn
            fact_conn=facts.db
            require(not writer_conn.in_transaction and
                    not fact_conn.in_transaction,
                    "WF91_WRITERS_NOT_QUIESCENT")
            versions=(writer_conn.execute(
                "PRAGMA data_version").fetchone()[0],
                fact_conn.execute(
                "PRAGMA data_version").fetchone()[0])
            _backup_sqlite(writer_conn,tmp/FILE_NAMES[0])
            _backup_sqlite(fact_conn,tmp/FILE_NAMES[1])
            require((writer_conn.execute(
                "PRAGMA data_version").fetchone()[0],
                fact_conn.execute(
                "PRAGMA data_version").fetchone()[0])==versions,
                "WF91_CONCURRENT_SQLITE_WRITER_DETECTED")
            audited={}
            for name in FILE_NAMES:
                audited[name]={
                    **_check_path(tmp/name),
                    "sqlite_audit":_audit_db(tmp/name,name),
                }
            manifest={
                "format":FORMAT,
                "schema_version":SCHEMA_VERSION,
                "checkpoint_id":checkpoint_id,
                "previous_manifest_sha256":
                    oldptr["manifest_sha256"] if oldptr else None,
                "local_sqlite_files":audited,
                "r2_v82_legacy_anchors":dict(r2_v82_anchors),
                "live_cross_database_atomicity_proven":False,
                "external_r2_verified_this_run":False,
                "literary_growth_independently_verified":False,
                "write_skill_unlocked":False,
            }
            manifest["manifest_sha256"]=digest(canonical(manifest))
            raw=canonical(manifest)
            require(len(raw)<=MAX_MANIFEST_BYTES,
                    "WF91_MANIFEST_BUDGET_EXCEEDED")
            if failpoint=="BEFORE_MANIFEST":
                raise V91MemoryCheckpointError(
                    "WF91_TEST_INJECTED_BEFORE_MANIFEST")
            mf=tmp/"manifest.json"
            with mf.open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            _fsync_dir(tmp)
            _manifest_receipt(manifest)
            os.rename(tmp,final)
            published=True
            _fsync_dir(root/"checkpoints")
            if failpoint=="AFTER_DIRECTORY_BEFORE_CURRENT":
                raise V91MemoryCheckpointError(
                    "WF91_TEST_INJECTED_BEFORE_POINTER")
            ptr={
                "format":POINTER_FORMAT,
                "checkpoint_id":checkpoint_id,
                "manifest_sha256":manifest["manifest_sha256"],
            }
            stage=root/(".CURRENT-"+checkpoint_id+".tmp")
            with stage.open("xb") as out:
                out.write(canonical(ptr))
                out.flush()
                os.fsync(out.fileno())
            os.replace(stage,root/"CURRENT")
            _fsync_dir(root)
            return verify_checkpoint(root,checkpoint_id=checkpoint_id)
        finally:
            if not published and tmp.exists():
                shutil.rmtree(tmp)
            fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def restore_workspace(*,root,destination):
    """Cold verified private copy. Never write into the archived checkpoint."""
    proof=verify_checkpoint(root)
    root=Path(root)
    dest=Path(destination)
    require(not dest.exists(),"WF91_RESTORE_DESTINATION_ALREADY_EXISTS")
    require(not dest.is_symlink(),"WF91_RESTORE_DESTINATION_SYMLINK")
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(mkdtemp(prefix=".wf91-restore-",dir=dest.parent))
    published=False
    try:
        source=root/"checkpoints"/proof["checkpoint_id"]
        for name in FILE_NAMES:
            shutil.copyfile(source/name,tmp/name)
            _fsync_file(tmp/name)
            require(_check_path(tmp/name)==_check_path(source/name),
                    "WF91_COLD_RESTORE_COPY_SHA_MISMATCH")
            require(_audit_db(tmp/name,name)==
                    _audit_db(source/name,name),
                    "WF91_COLD_RESTORE_LOGICAL_DIFFERENCE")
        _fsync_dir(tmp)
        os.rename(tmp,dest)
        published=True
        _fsync_dir(dest.parent)
        return {
            "status":"WF91_PRIVATE_WORKSPACE_COLD_RESTORED",
            "checkpoint_id":proof["checkpoint_id"],
            "manifest_sha256":proof["manifest_sha256"],
            "database_files":[str(dest/name) for name in FILE_NAMES],
            "source_bundle_unmodified":True,
            "no_literary_semantic_approval":True,
        }
    finally:
        if not published and tmp.exists():
            shutil.rmtree(tmp)
