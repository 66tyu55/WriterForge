"""Promote the ALREADY-VERIFIED private R2 星辰变 source into one new study library.

Nothing passes through ChatGPT or a public GitHub artifact. The original
13-work root archive is not used. A full separate restore proves persistence.
This is deterministic structural study, NOT LLM fine-tuning/review.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sqlite3

from writerforge import WriterForgeDB, RuntimeEngine
from writerforge.modern_source import study_modern_source
from writerforge.private_single_book_transfer import PrivateSingleBookVault, FORMAT, BOOK_ID
from writerforge.r2_storage import (
    R2Config, R2StudyVault, R2StorageError, _digest,
    MAX_LATEST_BYTES, MAX_MANIFEST_BYTES,
)

SOURCE_SHA256 = "83da08694a5d5510124711c7bfcc7522be531cdb73e01790aa0d3076932ab5f0"
SOURCE_BYTES = 8_256_014
TARGET_LIBRARY = "xingchenbian"
WORK_ID = "xingchenbian-private-original"


def main() -> None:
    config = R2Config.from_environment()
    if config.bucket != "writerforge-private-library":
        raise R2StorageError("unexpected private R2 bucket")
    source_vault = PrivateSingleBookVault(config)
    prefix = source_vault._root(BOOK_ID) + "/"
    raw_pointer = source_vault._get_small(source_vault._latest_key(BOOK_ID), MAX_LATEST_BYTES)
    pointer = json.loads(raw_pointer)
    if pointer.get("format") != FORMAT or pointer.get("book_id") != BOOK_ID:
        raise R2StorageError("private source pointer belongs to wrong book")
    version = pointer.get("snapshot")
    if not isinstance(version,str) or len(version)!=64 or pointer.get("manifest_sha256")!=version:
        raise R2StorageError("private source pointer has invalid manifest digest")
    raw_manifest = source_vault._get_small(source_vault._manifest_key(BOOK_ID, version),
                                            MAX_MANIFEST_BYTES)
    if sha256(raw_manifest).hexdigest()!=version:
        raise R2StorageError("private source manifest is corrupt")
    manifest=json.loads(raw_manifest)
    original=manifest.get("file",{})
    if (manifest.get("format")!=FORMAT or manifest.get("book_id")!=BOOK_ID
        or manifest.get("status")!="archived_unreviewed"
        or original.get("key")!=source_vault._blob_key(BOOK_ID,SOURCE_SHA256)
        or original.get("sha256")!=SOURCE_SHA256 or original.get("bytes")!=SOURCE_BYTES):
        raise R2StorageError("private source manifest differs from pinned whole-book original")
    key=original["key"]
    remote=source_vault._head(key)
    if (remote is None or int(remote.get("ContentLength",-1))!=SOURCE_BYTES
        or remote.get("Metadata",{}).get("sha256")!=SOURCE_SHA256):
        raise R2StorageError("private R2 source blob missing or does not match known original")
    with TemporaryDirectory(prefix="writerforge-modern-from-r2-") as directory:
        workdir=Path(directory)
        source=workdir/"source.txt"
        source_vault.client.download_file(config.bucket,key,str(source))
        if _digest(source)!=(SOURCE_SHA256,SOURCE_BYTES):
            raise R2StorageError("original source failed fresh R2 download SHA256")
        runtime=RuntimeEngine()
        runtime.enter_learn()
        study_db=workdir/"study.sqlite3"
        db=WriterForgeDB(study_db)
        try:
            report=study_modern_source(
                source, db, runtime,
                work_id=WORK_ID,title="星辰变",protagonist="秦羽",
                genre="玄幻修仙",source_uri="r2://"+config.bucket+"/"+key,
                min_chapters=300,max_chapters=2000,min_bytes=5*1024*1024,
                expected_sha256=SOURCE_SHA256,
            )
        finally:
            db.close()
        if not report["structure_complete"] or report["studied_chapters"]!=report["source_chapters"]:
            raise R2StorageError("not all modern chapters structurally ingested")
        report_path=workdir/"report.json"
        report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        target_vault=R2StudyVault(config)
        backup=target_vault.backup(
            database=study_db,library=TARGET_LIBRARY,
            source=source,extras={"report.json":report_path},
            edition="xingchenbian-private-structural-v1",
        )
        restored=target_vault.restore(library=TARGET_LIBRARY,destination=workdir/"fresh-r2")
        restored_root=Path(restored["storage_dir"]) if "storage_dir" in restored else None
        if restored_root is None:
            candidates=list((workdir/"fresh-r2"/TARGET_LIBRARY).glob("*/study.sqlite3"))
            if len(candidates)!=1:
                raise R2StorageError("R2 restore did not yield exactly one new DB")
            restored_root=candidates[0].parent
        if _digest(restored_root/"source.txt")!=(SOURCE_SHA256,SOURCE_BYTES):
            raise R2StorageError("R2 restored TXT differs from private source bytes")
        with sqlite3.connect(restored_root/"study.sqlite3") as con:
            if con.execute("PRAGMA quick_check").fetchone()[0]!="ok":
                raise R2StorageError("fresh R2 SQLite quick_check failed")
            actual=con.execute(
                "SELECT COUNT(*) FROM studied_chapters WHERE work_id=?",(WORK_ID,)
            ).fetchone()[0]
            units=con.execute(
                "SELECT COUNT(*) FROM source_spans WHERE work_id=?",(WORK_ID,)
            ).fetchone()[0]
            if actual!=report["source_chapters"] or units!=report["studied_units"]:
                raise R2StorageError("restored SQLite does not match source report")
        print("R2 VERIFIED MODERN STUDY: 星辰变")
        print("Original source bytes:",SOURCE_BYTES)
        print("Original source SHA256:",SOURCE_SHA256)
        print("Structurally studied chapters:",actual)
        print("Restored source spans:",units)
        print("New R2 study snapshot:",backup["snapshot"])
        print("No model training or independent criticism was performed.")
        import os
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as summary:
                summary.write("## 星辰变：私有 R2 原文 → 全书结构阅读 → 新 R2 数据库 → 全新恢复\n")
                summary.write(f"Original SHA256: {SOURCE_SHA256}\n")
                summary.write(f"Chapters: {actual}; spans: {units}\n")
                summary.write(f"Target: writerforge/v1/libraries/{TARGET_LIBRARY}/\n")
                summary.write(f"Snapshot: {backup['snapshot']}\n")
                summary.write("**Verified from separately downloaded R2 files; no LLM literary training claimed.**\n")


if __name__=="__main__":
    main()
