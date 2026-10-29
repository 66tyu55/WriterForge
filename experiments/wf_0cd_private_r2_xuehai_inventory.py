"""0.CD: metadata-only read of the EXISTING private Cloudflare R2 Xuehai.

No original passage, title, object key, SQL row or credential is printed.
This does not create Xuehai entries, turn a lexical index into a close reading,
or authorize source transfer to any LLM. Only standard R2 listing and vetted
public-classic snapshot manifest reads; never PUT/DELETE.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json

from writerforge.r2_storage import R2Config, R2StudyVault, R2StorageError

BUCKET="writerforge-private-library"
CATEGORIES={
    "private_source_objects":"writerforge/v1/private-reading/",
    "verified_study_snapshots":"writerforge/v1/libraries/",
    "source_sql_index_objects":"writerforge/v1/indexes/v1/",
    "source_learning_journal_objects":"writerforge/v1/learn/v1/",
    "narrative_memory_objects":"writerforge/v1/narrative-memory/v1/",
}
PAGE_SIZE=200
MAX_PAGES=4


def inventory_metadata(client, *, bucket=BUCKET):
    """Bounded per-prefix R2 ListObjectsV2; no source download, no mutation."""
    if bucket != BUCKET:
        raise R2StorageError("WF0CD_PRIVATE_BUCKET_MISMATCH")
    summaries={}
    for label,prefix in CATEGORIES.items():
        counted=0
        bytes_total=0
        pages=0
        cursor=None
        kinds=Counter()
        seen=set()
        complete=False
        while pages<MAX_PAGES:
            opts={"Bucket":bucket,"Prefix":prefix,"MaxKeys":PAGE_SIZE}
            if cursor is not None:
                opts["ContinuationToken"]=cursor
            response=client.list_objects_v2(**opts)
            pages+=1
            for obj in response.get("Contents",[]):
                key=obj["Key"]
                size=obj["Size"]
                if (not isinstance(key,str) or not key.startswith(prefix)
                    or key in seen or type(size) is not int or size<0):
                    raise R2StorageError("WF0CD_UNTRUSTED_OR_REPEAT_R2_METADATA")
                seen.add(key)
                counted+=1
                bytes_total+=size
                # Classify by suffix ONLY. The name/title/key is never logged.
                ext=Path(key).suffix.lower()
                kinds[
                    "text" if ext in (".txt",".md")
                    else "archive" if ext in (".rar",".zip",".7z",".epub")
                    else "sqlite" if ext in (".sqlite",".sqlite3",".db")
                    else "manifest" if ext==".json"
                    else "other"
                ]+=1
            if not response.get("IsTruncated"):
                complete=True
                break
            new_cursor=response.get("NextContinuationToken")
            if (not isinstance(new_cursor,str) or not new_cursor
                or new_cursor in seen):
                raise R2StorageError("WF0CD_INVALID_R2_CONTINUATION")
            cursor=new_cursor
        summaries[label]={
            "object_count_observed":counted,
            "total_bytes_observed":bytes_total,
            "pages":pages,
            "prefix_scan_complete":complete,
            "kind_counts":dict(sorted(kinds.items())),
            "literary_books_admitted":False,
        }
    return {
        "status":"EXISTING_R2_METADATA_READONLY_OBSERVED",
        "r2_bucket_known_not_newly_created":True,
        "source_listing":summaries,
        "all_requested_prefixes_completely_scanned":all(
            x["prefix_scan_complete"] for x in summaries.values()),
        "private_source_names_or_text_in_output":False,
        "source_index_is_not_literary_reading":True,
        "new_xuehai_readings_created":0,
        "model_calls":0,
        "r2_source_reads":0,
        "r2_writes":0,
        "railway_deployments":0,
        "literary_quality_improvement_verified":False,
    }


def main():
    config=R2Config.from_environment()
    if config.bucket!=BUCKET:
        raise R2StorageError("WF0CD_WRONG_CONFIGURED_PRIVATE_BUCKET")
    vault=R2StudyVault(config)
    report=inventory_metadata(vault.client)
    # Existing source book catalog reads only immutable manifest metadata.
    # Unknown/private editions are NEVER assigned literary-rights approval.
    ready=vault.corpus_readiness(threshold=50,max_libraries=256)
    report["vetted_public_classic_study_libraries"]=(
        ready["complete_distinct_works"])
    report["public_catalog_candidates_seen"]=ready["catalog_candidates_seen"]
    report["private_or_unreviewed_books_count_as_approved"]=False
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    return report


if __name__=="__main__":
    main()
