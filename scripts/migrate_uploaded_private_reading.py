"""One-time R2-root migration for the user-uploaded private reading archive.

The source is already in R2. Actions obtains scoped R2 secrets at runtime, streams
the existing 222 MiB object to ephemeral runner disk, then creates a versioned
snapshot under the dedicated private-reading prefix. No original content in Git,
Actions artifacts, print output or public releases.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from writerforge.r2_storage import R2Config, R2StorageError, _digest
from writerforge.private_reading_storage import PrivateReadingVault, audit_private_reading

ROOT_KEY="WriterForge_PrivateReading_13Works_20261011.sqlite3"
EXPECTED_SHA256="5b6c0fc1f564155e1ddbab4c853739722a8b422181857a7548e08fe2826e05e6"
EXPECTED_BYTES=231878656

def migrate() -> dict:
    vault=PrivateReadingVault(R2Config.from_environment())
    # The exact user-uploaded source is pinned; do not scan arbitrary R2 files.
    head=vault._head(ROOT_KEY)
    if head is None or int(head.get("ContentLength",-1))!=EXPECTED_BYTES:
        raise R2StorageError("pinned user-uploaded R2 source missing or unexpected size")
    with TemporaryDirectory(prefix="wf-reading-migrate-") as folder:
        source=Path(folder)/"source.sqlite3"
        vault.client.download_file(vault.config.bucket,ROOT_KEY,str(source))
        if _digest(source)!=(EXPECTED_SHA256,EXPECTED_BYTES):
            raise R2StorageError("R2 source SHA256 mismatch, migration stopped")
        original=audit_private_reading(source)
        upload=vault.backup(database=source)
        remote=vault.inventory()
        if not all((remote["has_latest"],remote["has_blob"],remote["has_snapshot"])):
            raise R2StorageError("target inventory lacks expected objects")
        # Critical: a completely fresh directory, not cache validation.
        restored=vault.restore(destination=Path(folder)/"fresh_restore",snapshot=upload["snapshot"])
        if restored["stats"]!=original:
            raise R2StorageError("source and restored inventory disagree")
        # Snapshot DB bytes and original live file may differ due to SQLite
        # online backup; compare logical/section integrity, and verify the
        # exact restored snapshot hash already enforced by restore().
        return {"source_r2_root_object_verified":True,"source_sha256":EXPECTED_SHA256,
            "source_bytes":EXPECTED_BYTES,"destination":upload["uri"],
            "destination_snapshot":upload["snapshot"],
            "remote_inventory":remote,
            "restored_sha256":restored["sha256"],
            "fresh_restore_complete":restored["restored_and_verified"],
            "archived_works":restored["stats"]["works"],
            "status":"archived_unreviewed",
            "semantic_training_performed":False}

if __name__=="__main__":
    print(json.dumps(migrate(),ensure_ascii=False))
