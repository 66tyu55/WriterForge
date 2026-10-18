"""V52 LIVE: verify existing author's private R2 Xuehai, read-only.

No source text / manuscript, credentials, cloud account details, or full JSON
responses are printed. No model, paid LLM, R2 upload or deletion is performed.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

from writerforge.classics_catalog import get_book
from writerforge.r2_retrieval import R2SourceGateway

EXPECTED_ORIGINAL_SHA="273f4cbaecb4c4d396ecec7103b4761e62bde0c0f368185a1697c1880cfe9cf7"

def run():
    book=get_book("laocanyouji")
    gateway=R2SourceGateway.from_environment()
    if gateway.vault.config.bucket!="writerforge-private-library":
        raise ValueError("INCORRECT_PRIVATE_BUCKET")
    destination=Path(os.environ["RUNNER_TEMP"])/"verified-private-r2-lookup"
    # Query a term which occurs in actual original late-Qing Chinese prose.
    first=gateway.search(library=book.library,snapshot=None,
                         terms=("老殘",),cache_dir=destination,limit=6)
    if not first.matches:
        raise ValueError("REAL_R2_XUEHAI_DID_NOT_FIND_GROUNDED_CHINESE_TERM")
    if not all(r["work_id"]==book.work_id for r in first.matches):
        raise ValueError("WRONG_WORK_ID_IN_REAL_R2_EVIDENCE")
    if not all(r["work_original_sha256"]==EXPECTED_ORIGINAL_SHA
               for r in first.matches):
        raise ValueError("REAL_SOURCE_SHA_MISMATCH_PINNED_CHINESE_EDITION")
    if first.from_local_cache:
        raise ValueError("FIRST_LIVE_R2_RESTORE_SHOULD_DOWNLOAD")
    second=gateway.search(library=book.library,snapshot=first.snapshot,
                          terms=("老殘",),cache_dir=destination,limit=6)
    if (not second.from_local_cache or
        second.matches!=first.matches or second.snapshot!=first.snapshot):
        raise ValueError("R2_CACHED_SNAPSHOT_CANNOT_BE_REPLAYED_IDENTICALLY")
    # Full bibliographic study and source bytes are part of the existing
    # immutable R2 verified manifest. Never upload back or log source text.
    result={
        "format":"writerforge.v52-live-private-source-retrieval.v1",
        "library":book.library,
        "work_id":book.work_id,
        "r2_snapshot_sha256":first.snapshot,
        "original_text_sha256":EXPECTED_ORIGINAL_SHA,
        "verified_exact_chinese_source_matches":len(first.matches),
        "verified_fresh_r2_restore":True,
        "verified_cached_sha_replay":True,
        "original_literary_semantics_verified":False,
        "new_model_calls":0,
        "remote_storage_writes":0,
        "r2_credentials_logged":False,
        "source_text_logged":False,
    }
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return result

if __name__=="__main__":
    run()
