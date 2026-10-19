"""V71: one bounded real R2 novel -> temporary SHA-verifiable SQLite index.

The WF Python process, not ChatGPT, reads via existing authenticated Worker.
It chooses one source solely from verified folder topology and byte budget,
then streams the entire TXT using Range requests into a short-lived Railway
tempfile. The source/SQLite are NEVER printed, sent to GPT, or sent to GitHub.
This is an engineering READ/index smoke test, not literary comprehension,
learning, or a persistent 50-book corpus.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
import re
import sqlite3
from urllib.parse import quote

from .bulk_inbox import BulkCatalog, PRIVATE_READING, parse_key
from .private_reading_remote import (
    WFPrivateReadingClient, PrivateReadingError, FOLDERS,
)
from .private_reading_topology import analyze_private_topology

MAX_ONE_FILE_BYTES = 16 * 1024 * 1024
MIN_ONE_FILE_BYTES = 10 * 1024
CHUNK_BYTES = 1024 * 1024
MAX_TOTAL_REQUESTS = 17

class SourceIndexSmokeError(PrivateReadingError):
    pass

def require(ok, code):
    if not ok:
        raise SourceIndexSmokeError(code)

def choose_one_source(catalog: BulkCatalog):
    """Only unambiguous, single-TXT, non-archive parent folders.

    No keyword matching, no model ranking and no inspection of novel titles.
    This function does NOT prove that the TXT holds a complete novel.
    """
    require(isinstance(catalog,BulkCatalog),"WF_V71_CATALOG_REQUIRED")
    all_rows=[dict(r) for r in catalog.conn.execute(
        "SELECT object_key,category,folder,ext,size_bytes,etag "
        "FROM assets ORDER BY object_key")]
    groups={}
    for row in all_rows:
        key=row["object_key"]
        if not key.startswith(PRIVATE_READING):
            raise SourceIndexSmokeError("WF_V71_UNEXPECTED_OBJECT_SCOPE")
        group=key.rsplit("/",1)[0]
        groups.setdefault(group,[]).append(row)
    candidates=[]
    for files in groups.values():
        if len(files)!=1:
            continue
        row=files[0]
        if (row["folder"] not in ("仙侠","历史","科幻")
            or row["ext"]!=".txt"
            or not MIN_ONE_FILE_BYTES<=row["size_bytes"]<=MAX_ONE_FILE_BYTES):
            continue
        info=parse_key(row["object_key"])
        # Candidate must be under a subdirectory, never a root metadata object.
        if len(row["object_key"][len(PRIVATE_READING):].split("/"))!=3:
            continue
        require(info["folder"]==row["folder"],"WF_V71_FOLDER_MISMATCH")
        candidates.append(row)
    if not candidates:
        raise SourceIndexSmokeError("WF_V71_NO_SAFE_SINGLE_SOURCE_IN_BUDGET")
    # Stable smallest-first by size, then content-independent key digest.
    candidates.sort(key=lambda r:(
        r["size_bytes"],sha256(r["object_key"].encode("utf8")).hexdigest()))
    return candidates[0],len(candidates)

def download_one_verified(client: WFPrivateReadingClient, row, target):
    """ETag/length consistency + full local SHA256. No remote write."""
    require(isinstance(client,WFPrivateReadingClient),
            "WF_V71_CLIENT_REQUIRED")
    require(type(row.get("size_bytes")) is int and
            MIN_ONE_FILE_BYTES<=row["size_bytes"]<=MAX_ONE_FILE_BYTES,
            "WF_V71_FILE_SIZE_NOT_PERMITTED")
    require(row.get("ext")==".txt","WF_V71_TEXT_ONLY")
    path=Path(target)
    require(not path.exists(),"WF_V71_NO_OVERWRITE")
    key=row["object_key"]
    expected=row["size_bytes"]
    check,empty=client._request(
        "/r2/private-reading/object",{"key":key},method="HEAD")
    require(empty==b"" and check.get("Content-Length")==str(expected)
            and check.get("X-WF-Object-Size")==str(expected),
            "WF_V71_HEAD_CHANGED")
    original_tag=check.get("ETag")
    require(isinstance(original_tag,str) and bool(original_tag),
            "WF_V71_ETAG_MISSING")
    listed=row.get("etag")
    if listed is not None:
        require(original_tag==listed,"WF_V71_ETAG_MISMATCH_FROM_LIST")
    t0=perf_counter()
    total=0
    requests=0
    digest=sha256()
    try:
        with path.open("xb") as handle:
            while total<expected:
                count=min(CHUNK_BYTES,expected-total)
                requests+=1
                require(requests<=MAX_TOTAL_REQUESTS,
                        "WF_V71_HTTP_REQUEST_BUDGET_EXCEEDED")
                headers,raw=client._request(
                    "/r2/private-reading/object",
                    {"key":key,"offset":total,"length":count},
                    cap=CHUNK_BYTES)
                require(len(raw)==count and
                        headers.get("Content-Length")==str(count) and
                        headers.get("X-WF-Object-Size")==str(expected) and
                        headers.get("Content-Range")==(
                            f"bytes {total}-{total+count-1}/{expected}") and
                        headers.get("ETag")==original_tag,
                        "WF_V71_RANGE_RESPONSE_INCONSISTENT")
                handle.write(raw)
                digest.update(raw)
                total+=len(raw)
        require(total==expected and path.stat().st_size==expected,
                "WF_V71_INCOMPLETE_DOWNLOAD")
        # Content hash protects the local parsing/indexing phase. No R2
        # content SHA claim is made unless R2 itself had a pinned SHA.
        return {"source_sha256":digest.hexdigest(),
                "bytes":total,"requests":requests+1,
                "read_ms":round((perf_counter()-t0)*1000,2)}
    except BaseException:
        path.unlink(missing_ok=True)
        raise

def _locally_check_search(catalog,book_id,category,shards):
    """Self-hit smoke check, NOT blind retrieval/relevance evaluation."""
    path=Path(shards)/(book_id+".sqlite3")
    require(path.is_file(),"WF_V71_SQL_SHARD_MISSING")
    # Internally derive a query from a real indexed unit. Do not print the
    # unit or keyword, and do not pretend this is independent literary proof.
    conn=sqlite3.connect(
        "file:"+quote(str(path.resolve()),safe="/")+"?mode=ro",
        uri=True)
    try:
        from_row=conn.execute(
            "SELECT normalized FROM units WHERE length(normalized)>=4 "
            "ORDER BY id LIMIT 100").fetchall()
    finally:
        conn.close()
    needle=None
    for (t,) in from_row:
        m=re.search(r"[\u3400-\u9fff]{4,10}",t)
        if not m:m=re.search(r"[a-zA-Z0-9]{4,10}",t)
        if m:
            needle=m.group(0)[:4]
            break
    if not needle:
        return {"status":"NO_SAFE_INTERNAL_PROBE_TERM","hits":0,
                "real_source_excerpt_returned":False}
    result=catalog.search(
        category=category,book_id=book_id,text=needle,
        shard_dir=shards,limit=4)
    require(result["status"]=="LEXICAL_RESULTS_ONLY" and
            len(result["matches"])>=1,
            "WF_V71_INTERNAL_LEXICAL_READBACK_FAILED")
    return {"status":"SELF_DERIVED_LEXICAL_HIT",
            "hits":len(result["matches"]),
            "query_keyword_emitted":False,
            "real_source_excerpt_returned":False,
            "independent_relevance_or_literary_understanding_proven":False}

def index_one_real_source(endpoint):
    """Total transfer <=16MiB from ONE source. Every file ephemeral."""
    client=WFPrivateReadingClient(endpoint=endpoint,timeout=60)
    with TemporaryDirectory(prefix="wf-v71-one-book-") as scratch:
        root=Path(scratch)
        cat=BulkCatalog(root/"catalog.sqlite3")
        try:
            metadata=client.inventory_to_catalog(cat)
            require(metadata.get("all_folders_complete") is True,
                    "WF_V71_INVENTORY_INCOMPLETE")
            shape=analyze_private_topology(cat,complete=True)
            row,eligible=choose_one_source(cat)
            target=root/"source.txt"
            transferred=download_one_verified(client,row,target)
            started=perf_counter()
            result=cat.index_text_file(
                row["object_key"],target,root/"shards")
            building_ms=round((perf_counter()-started)*1000,2)
            require(result.get("source_sha256")==transferred["source_sha256"],
                    "WF_V71_SQL_INDEX_SOURCE_HASH_CHANGED")
            lookup=_locally_check_search(cat,result["book_id"],
                                         row["category"],root/"shards")
            return {
              "format":"wf.private-r2-one-book-sql-smoke.v1",
              "transport":"WF_RAILWAY_PYTHON_TO_WORKER_TO_R2",
              "inventory_metadata_sha256":shape["metadata_only_sha256"],
              "complete_four_folder_inventory":True,
              "selected_without_reading_title_or_keyword":True,
              "selected_category":row["category"],
              "candidate_sources_within_bytes_budget":eligible,
              "selected_key_sha256":sha256(
                  row["object_key"].encode("utf8")).hexdigest(),
              "download_integrity_checked":True,
              "independent_source_origin_verified":False,
              "source_sha256":transferred["source_sha256"],
              "source_bytes":transferred["bytes"],
              "source_request_count":transferred["requests"],
              "source_download_ms":transferred["read_ms"],
              "sql_build_ms":building_ms,
              "sql_chapters_header_detected_not_completeness_proof":
                  result["chapters_detected"],
              "sql_units_indexed":result["units_indexed"],
              "index_engine":result["search_engine"],
              "internal_readback":lookup,
              "source_files_persisted_after_exit":False,
              "sql_persisted_after_exit":False,
              "original_source_prose_in_result":False,
              "r2_source_or_index_write_requests":0,
              "model_calls":0,
              "literary_understanding_tested":False,
            }
        finally:
            cat.close()
