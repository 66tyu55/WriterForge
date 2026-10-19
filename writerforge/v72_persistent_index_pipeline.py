"""V72 WF pipeline: from private R2 novel to durable R2 SQL index.

The existing V71 system proves a one-book ephemeral SQL smoke. This stage
does not create a Railway volume: the only durable artifacts are immutable
SQLite chunks+manifest in the SAME private R2 bucket under /indexes/v1/.

A real publish will run only after the user configures a separate
WF_INDEX_UPLOAD_TOKEN in both Cloudflare Worker and Railway; until then it
fails closed without attempting any remote write.
"""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import sqlite3

from .bulk_inbox import BulkCatalog
from .private_reading_remote import WFPrivateReadingClient
from .private_reading_topology import analyze_private_topology
from .private_r2_sql_smoke import (
    choose_one_source,download_one_verified,SourceIndexSmokeError,
)
from .source_encoding_guard import (
    detect_decoding_for_index,SourceEncodingError,
)
from .r2_index_vault import R2IndexVault,key_sha,R2IndexError

WORKER_ENDPOINT="https://wf-r2-api.3227482831.workers.dev"

def publish_one(*,endpoint=WORKER_ENDPOINT,read_token=None,
                write_token=None,progress=None):
    def report(stage):
        if progress is not None:progress(stage)
    # Build transport before any remote request to enforce least privilege.
    vault=R2IndexVault(endpoint=endpoint,read_token=read_token,
                      write_token=write_token)
    if not vault.write_token:
        raise R2IndexError("WF_INDEX_UPLOAD_TOKEN_NOT_CONFIGURED")
    client=WFPrivateReadingClient(
        endpoint=endpoint,token=vault.reader.token,timeout=60)
    report("WF_V72_METADATA_SCAN_STARTED")
    with TemporaryDirectory(prefix="wf-v72-build-") as directory:
        folder=Path(directory)
        cat=BulkCatalog(folder/"catalog.sqlite3")
        try:
            info=client.inventory_to_catalog(cat)
            if info["all_folders_complete"] is not True:
                raise SourceIndexSmokeError("WF_V72_INVENTORY_INCOMPLETE")
            shape=analyze_private_topology(cat,complete=True)
            record,_=choose_one_source(cat)
            original_key=record["object_key"]
            ref={"key":original_key,"size":record["size_bytes"],
                 "etag":record["etag"]}
            report("WF_V72_METADATA_SCAN_VERIFIED")
            existing=vault.find_matching(ref)
            if len(existing)>1:
                raise R2IndexError("WF_V72_MULTIPLE_PUBLISHED_VERSIONS_NEED_PIN")
            if len(existing)==1:
                # No raw TXT download, no re-indexing, no write call.
                report("WF_V72_EXISTING_INDEX_VERIFIED")
                with vault.restore(ref,existing[0]["manifest_sha256"]) as (db,manifest):
                    count=db.execute("SELECT COUNT(*) FROM units").fetchone()[0]
                    if count != manifest["units"]:
                        raise R2IndexError("WF_V72_EXISTING_INDEX_COUNTS_WRONG")
                    return {
                      "status":"WF_V72_ALREADY_INDEXED_IN_PRIVATE_R2",
                      "source_category":record["category"],
                      "manifest_sha256":existing[0]["manifest_sha256"],
                      "source_key_sha256":key_sha(original_key),
                      "indexed_units":count,
                      "original_downloaded":False,
                      "reindex_performed":False,
                      "index_is_durable_in_r2":True,
                      "sql_read_only_restore_verified":True,
                      "original_novel_edited":False,
                      "r2_writes_this_run":0,
                      "literary_model_calls":0,
                      "literary_quality_verified":False,
                    }
            report("WF_V72_NO_INDEX_YET_BUILD_STARTED")
            source_file=folder/"source.txt"
            original=download_one_verified(client,record,source_file)
            charset=detect_decoding_for_index(source_file)
            report("WF_V72_ORIGINAL_BYTES_AND_ENCODING_CHECKED")
            parsed=cat.index_text_file(
               original_key,source_file,folder/"shards",
               encoding=charset["encoding"])
            if parsed["source_sha256"] != original["source_sha256"]:
                raise R2IndexError("WF_V72_INDEX_SOURCE_INCONSISTENT")
            shard=folder/"shards"/(parsed["book_id"]+".sqlite3")
            report("WF_V72_SQLITE_TEMPORARY_BUILT")
            receipt=vault.publish(
                index_file=shard,
                original_key=original_key,
                source_sha256=original["source_sha256"],
                source_size=record["size_bytes"],
                source_etag=record["etag"],
                category=record["category"],
                encoding=charset["encoding"],
                provisional_legacy=charset["provisional_legacy_decoding"],
                units=parsed["units_indexed"],
                chapters=parsed["chapters_detected"],
            )
            report("WF_V72_CHUNKS_AND_MANIFEST_PUBLISHED")
            # Critical: verify using the R2 reader route, not the upload reply.
            with vault.restore(ref,receipt["manifest_sha256"]) as (db,manifest):
                count=db.execute("SELECT COUNT(*) FROM units").fetchone()[0]
                if count != receipt["units"]:
                    raise R2IndexError("WF_V72_REMOTE_RESTORE_COUNT_MISMATCH")
                check=db.execute("PRAGMA query_only").fetchone()[0]
                if check!=1:
                    raise R2IndexError("WF_V72_RESTORED_DB_NOT_READ_ONLY")
            report("WF_V72_REMOTE_MANIFEST_COLD_READBACK_VERIFIED")
            return {
              "status":"WF_V72_INDEX_PERSISTED_IN_PRIVATE_R2",
              "source_category":record["category"],
              "source_key_sha256":key_sha(original_key),
              "original_source_sha256":original["source_sha256"],
              "original_source_bytes":original["bytes"],
              "index_sha256":receipt["index_sha256"],
              "index_bytes":receipt["index_bytes"],
              "index_units":count,
              "chapters_header_detected":parsed["chapters_detected"],
              "parts":receipt["chunks"],
              "uploaded_new_parts":receipt["new_chunks"],
              "manifest_sha256":receipt["manifest_sha256"],
              "provisional_legacy_charset":charset["provisional_legacy_decoding"],
              "sql_read_only_restore_verified":True,
              "persistent_on_railway_volume":False,
              "index_is_durable_in_r2":True,
              "original_novel_edited":False,
              "literary_model_calls":0,
              "literary_quality_verified":False,
            }
        finally:
            cat.close()
