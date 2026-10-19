"""Independent WF process: cold-restores ONE published index with READ token.

This is intentionally a separate one-shot Railway deployment from the index
publisher. No original novel bytes fetched; only one content-addressed SQL
index is downloaded from private R2 and verified in ephemeral storage.
"""
from __future__ import annotations
import json,os,sys,time,types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

def emit(doc):
    print(json.dumps(doc,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V72_COLD_READ_ONLY_RESTORE_START",flush=True)
def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V72_READ_TOKEN_MISSING","network_attempted":False})
        return 1
    try:
        from tempfile import TemporaryDirectory
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.private_r2_sql_smoke import candidate_sources
        from writerforge.r2_index_vault import R2IndexVault,key_sha,R2IndexError
        from writerforge.private_reading_topology import analyze_private_topology
        reader=WFPrivateReadingClient(
            endpoint="https://wf-r2-api.3227482831.workers.dev")
        vault=R2IndexVault(
            endpoint="https://wf-r2-api.3227482831.workers.dev")
        with TemporaryDirectory(prefix="wf-v72-fresh-process-") as scratch:
            cat=BulkCatalog(Path(scratch)/"book_catalog.sqlite3")
            try:
                stats=reader.inventory_to_catalog(cat)
                if stats["all_folders_complete"] is not True:
                    raise R2IndexError("WF_V72_INVENTORY_INCOMPLETE")
                for record in candidate_sources(cat):
                    ref={"key":record["object_key"],
                         "size":record["size_bytes"],"etag":record["etag"]}
                    matches=vault.find_matching(ref)
                    if len(matches)>1:
                        raise R2IndexError(
                            "WF_V72_AMBIGUOUS_LIVE_REF_NEEDS_PIN")
                    if not matches:continue
                    manifest_hash=matches[0]["manifest_sha256"]
                    with vault.restore(ref,manifest_hash) as (db,manifest):
                        count=db.execute("SELECT COUNT(*) FROM units").fetchone()[0]
                        if count!=manifest["units"]:
                            raise R2IndexError(
                                "WF_V72_COLD_RESTORE_COUNT_MISMATCH")
                        row=db.execute(
                            "SELECT normalized FROM units "
                            "WHERE length(normalized)>=4 "
                            "ORDER BY id LIMIT 1").fetchone()
                        if row is None:
                            raise R2IndexError("WF_V72_SQLITE_NO_SOURCE_UNITS")
                        word=row[0][:4]
                        hits=db.execute(
                            "SELECT COUNT(*) FROM units WHERE instr(normalized,?)>0",
                            (word,)).fetchone()[0]
                        if hits<1:raise R2IndexError(
                            "WF_V72_SQLITE_INTERNAL_QUERY_FAILURE")
                    emit({
                      "status":"WF_V72_COLD_RESTART_RESTORE_VERIFIED",
                      "fresh_railway_process":True,
                      "metadata_source_objects":stats["total_objects"],
                      "source_key_sha256":key_sha(ref["key"]),
                      "manifest_sha256":manifest_hash,
                      "source_bytes_downloaded":0,
                      "index_bytes_downloaded":manifest["index_bytes"],
                      "read_only_sqlite":True,
                      "index_units":count,
                      "independent_literary_comprehension_proven":False,
                      "sql_internal_self_hit":True,
                      "source_text_returned_in_report":False,
                      "railway_persistent_volume_used":False,
                      "r2_writes":0,
                      "writer_token_required":False,
                    })
                    return 0
            finally:
                cat.close()
        emit({"status":"WF_V72_NO_MATCHING_PUBLISHED_INDEX",
              "original_source_downloaded":False,"r2_writes":0})
        return 1
    except Exception as err:
        code=str(err)
        if not code.startswith((
            "WF_V72_","WF_INDEX_","WF_PRIVATE_",
            "WF_R2_HTTP_","WF_V71_","BULK_")):
            code="WF_V72_UNEXPECTED_RESTORE_FAILURE"
        emit({"status":"WF_V72_COLD_RESTORE_FAILED","error_code":code,
              "private_source_or_token_logged":False})
        return 1

ret=main()
print("WF_V72_COLD_RESTORE_EXIT="+str(ret),flush=True)
time.sleep(8)
raise SystemExit(ret)
