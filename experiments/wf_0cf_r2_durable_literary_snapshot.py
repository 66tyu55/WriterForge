"""0.CF: durably store the EXISTING 126 literary entries in existing private R2.

Only the already published public-domain and WriterForge-created original
readings from the isolated 0.CE SQLite are eligible. No private modern source
books, no paid model, no new DB schema and no changes to Canon or older R2
libraries. Do not rewrite an existing R2 namespace with different contents.

The second GitHub Actions runner performs an independent, pinned cold restore
with an application-level read-only S3 client. Neither job logs source prose.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote
import argparse
import json
import sqlite3

from writerforge import RuntimeEngine
from writerforge.r2_storage import R2Config, R2StudyVault, R2StorageError
from writerforge.xuehai import XuehaiStore

LIBRARY = "wf-0cf-xuehai-literary-126-20261029-v1"
BUCKET = "writerforge-private-library"
ROLES = (
    "original_complete_scene_unreviewed",
    "public_domain_continuous_detail_prose_unreviewed",
    "classical_original_annotation_reflection",
    "original_annotation_reflection",
)
EXPECTED = dict(zip(ROLES, (24, 24, 46, 32)))
READING_ROLES = ROLES[2:]


class _QueryOnlyDb:
    """Use XuehaiStore's existing reading method on physically read-only SQL."""
    def __init__(self, conn):
        self.conn = conn


def inspect_literary_db(path: Path) -> dict:
    """Read every full study, not only the headline 126 count."""
    if not path.is_file():
        raise ValueError("WF0CF_XUEHAI_DB_NOT_FOUND")
    uri = "file:" + quote(str(path.resolve()), safe="/:") + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        ok = conn.execute("PRAGMA quick_check").fetchone()[0]
        if ok != "ok":
            raise ValueError("WF0CF_SOURCE_SQLITE_CORRUPT")
        if (conn.execute("SELECT COUNT(*) FROM xuehai_method_cards")
                .fetchone()[0] != 0 or
            conn.execute("SELECT COUNT(*) FROM accepted_prose")
                .fetchone()[0] != 0):
            raise ValueError("WF0CF_NOT_A_PURE_UNACCEPTED_LITERATURE_STUDY")
        published = conn.execute(
            "SELECT id FROM snapshots WHERE status='published' "
            "ORDER BY id DESC LIMIT 1").fetchone()
        if published is None:
            raise ValueError("WF0CF_NO_PUBLISHED_XUEHAI")
        latest = int(published["id"])
        rows = conn.execute(
            "SELECT id,work_id,source_role,source_hash,text "
            "FROM xuehai_entries WHERE source_role IN (?,?,?,?) "
            "ORDER BY work_id,source_role,source_hash,text", ROLES
        ).fetchall()
        counts = Counter(row["source_role"] for row in rows)
        if dict(counts) != EXPECTED or len(rows) != 126:
            raise ValueError("WF0CF_126_LITERATURE_ROLES_NOT_PRESERVED")
        for row in rows:
            full = row["text"]
            normalized = " ".join(full.split()).strip()
            expected_hash = sha256(
                (row["work_id"] + "|" + normalized).encode("utf8")
            ).hexdigest()
            if not isinstance(full, str) or row["source_hash"] != expected_hash:
                raise ValueError("WF0CF_LITERATURE_SOURCE_HASH_CHANGED")
        rt = RuntimeEngine()
        rt.enter_write(latest)
        try:
            store = XuehaiStore(_QueryOnlyDb(conn), rt)
            read_n = 0
            for row in rows:
                if row["source_role"] not in READING_ROLES:
                    continue
                study = store.read_literary_reading(row["id"])
                if not study["original"].strip() or not study["reflection"].strip():
                    raise ValueError("WF0CF_ONE_THREE_PART_READING_EMPTY")
                if len(study["annotations"]) != 3:
                    raise ValueError("WF0CF_ANNOTATIONS_NOT_COMPLETE")
                read_n += 1
        finally:
            rt.exit()
        if read_n != 78:
            raise ValueError("WF0CF_FULL_78_READBACKS_MISSING")
        # Source hashes alone do not protect against swapping one entry for a
        # different, equally well-formed one: bind complete original texts.
        content = [[r["work_id"], r["source_role"], r["source_hash"],
                    r["text"]] for r in rows]
        fingerprint = sha256(json.dumps(
            content, ensure_ascii=False, separators=(",",":")
        ).encode("utf8")).hexdigest()
        return {
            "contents": len(rows),
            "complete_three_part_readings": read_n,
            "content_sha256": fingerprint,
            "canonical_writes": 0,
            "model_calls": 0,
            "private_modern_novel_excerpts_in_report": False,
        }


class _ReadOnlyS3:
    """Cold reader never acquires an API method capable of remote mutation."""
    _allowed = frozenset(("head_object", "get_object", "download_file"))
    def __init__(self, underlying):
        self._underlying = underlying

    def __getattr__(self, key):
        if key not in self._allowed:
            raise R2StorageError("WF0CF_COLD_READER_REMOTE_MUTATION_DISALLOWED")
        return getattr(self._underlying, key)


def _vault(*, cold_only=False) -> R2StudyVault:
    config = R2Config.from_environment()
    if config.bucket != BUCKET:
        raise R2StorageError("WF0CF_WRONG_PRIVATE_BUCKET")
    client = R2StudyVault(config)
    return (R2StudyVault(config, client=_ReadOnlyS3(client.client))
            if cold_only else client)


def publish(db: Path) -> dict:
    expected = inspect_literary_db(db)
    vault = _vault()
    # If this independent prefix already exists, never overwrite its latest
    # pointer with another snapshot. Read and compare instead.
    prior = vault._head(vault._latest_key(LIBRARY))
    with TemporaryDirectory(prefix="wf0cf-postupload-") as scratch:
        if prior is not None:
            restored = vault.restore(library=LIBRARY, destination=scratch)
            current = inspect_literary_db(Path(restored["db"]))
            if current["content_sha256"] != expected["content_sha256"]:
                raise R2StorageError("WF0CF_EXISTING_REMOTE_LIBRARY_DIFFERENT_NO_OVERWRITE")
            snapshot = restored["snapshot"]
            wrote = False
        else:
            saved = vault.backup(database=db, library=LIBRARY)
            snapshot = saved["snapshot"]
            restored = vault.restore(
                library=LIBRARY, snapshot=snapshot, destination=scratch)
            current = inspect_literary_db(Path(restored["db"]))
            if current["content_sha256"] != expected["content_sha256"]:
                raise R2StorageError("WF0CF_R2_SAME_PROCESS_CONTENT_MISMATCH")
            wrote = True
    return {
        "status": "WF0CF_EXISTING_R2_LITERATURE_SNAPSHOT_DURABLE",
        **expected,
        "snapshot_sha256": snapshot,
        "library": LIBRARY,
        "new_library_prefix_only": True,
        "first_publish_or_existing_equal": "NEW" if wrote else "UNCHANGED",
        "prior_private_library_modified": False,
        "r2_uploaded_new_version": wrote,
        "source_originals_copied_to_public_logs": False,
        "writer_literary_quality_verified": False,
    }


def cold_restore(*, expected_snapshot: str, expected_content: str) -> dict:
    if not (isinstance(expected_snapshot,str) and
            len(expected_snapshot)==64 and
            isinstance(expected_content,str) and
            len(expected_content)==64):
        raise ValueError("WF0CF_EXPECTED_DIGESTS_MISSING")
    vault = _vault(cold_only=True)
    with TemporaryDirectory(prefix="wf0cf-independent-cold-reader-") as scratch:
        restored = vault.restore(
            library=LIBRARY,snapshot=expected_snapshot,destination=scratch)
        actual = inspect_literary_db(Path(restored["db"]))
    if actual["content_sha256"]!=expected_content:
        raise R2StorageError("WF0CF_INDEPENDENT_COLD_CONTENT_MISMATCH")
    if restored["snapshot"]!=expected_snapshot:
        raise R2StorageError("WF0CF_INDEPENDENT_R2_MANIFEST_MISMATCH")
    return {
        "status":"WF0CF_INDEPENDENT_R2_126_LITERATURE_COLD_RESTORE_VERIFIED",
        **actual,
        "snapshot_sha256":restored["snapshot"],
        "read_only_s3_methods_only":True,
        "new_writer_or_model_requests":0,
        "r2_writes_from_reader":0,
        "literary_gain_proven":False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action",choices=("publish","cold-restore"))
    ap.add_argument("--db",type=Path)
    ap.add_argument("--expected-snapshot")
    ap.add_argument("--expected-content")
    ap.add_argument("--github-output",type=Path)
    args = ap.parse_args()
    if args.action=="publish":
        if args.db is None:
            ap.error("publish needs --db")
        report = publish(args.db)
        if args.github_output is not None:
            with args.github_output.open("a",encoding="utf8") as output:
                output.write("snapshot="+report["snapshot_sha256"]+"\n")
                output.write("content_sha="+report["content_sha256"]+"\n")
    else:
        report = cold_restore(expected_snapshot=args.expected_snapshot,
                              expected_content=args.expected_content)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
