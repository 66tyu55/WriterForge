"""V72 zero-write live Cloudflare Worker readiness check on Railway.

Uses the existing WF reader secret and a distinct index writer secret.
- GET a synthetic 64-zero source fingerprint's index-ref listing (safe).
- PUT deliberately mismatched SHA chunk (must reject HTTP 422 BEFORE writes).
- No source content requested, no R2 object written, no secret values logged.
Do not call publish_one unless both gates have passed.
"""
from __future__ import annotations
import json, os, sys, time, types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

def emit(data):
    print(json.dumps(data,sort_keys=True,ensure_ascii=False),flush=True)

print("WF_V72_SAFE_LIVE_ROUTE_PROBE_STARTED",flush=True)
def main():
    read=os.getenv("WF_API_TOKEN")
    writer=os.getenv("WF_INDEX_UPLOAD_TOKEN")
    if not read or not writer or read==writer:
        emit({"status":"WF_V72_SECRET_PAIR_UNAVAILABLE_OR_REUSED",
              "real_write_attempted":False,"source_downloaded":False})
        return 1
    try:
        from writerforge.r2_index_vault import R2IndexVault,R2IndexError
        vault=R2IndexVault(
            endpoint="https://wf-r2-api.3227482831.workers.dev")
        refs=vault.manifest_refs("0"*64)
        if refs:
            emit({"status":"WF_V72_SYNTHETIC_SOURCE_HASH_NOT_EMPTY",
                  "source_downloaded":False,
                  "real_write_attempted":False})
            return 1
        emit({"status":"WF_V72_READER_INDEX_REFS_ROUTE_OK",
              "no_private_object_key_retrieved":True})
        try:
            # Deliberately incorrect declared hash: the Worker MUST refuse
            # this tiny payload BEFORE put(), proving writer-token isolation,
            # SHA gating, and zero object mutation.
            vault._call(
                "/r2/index/write",
                {"key":"writerforge/v1/indexes/v1/chunks/"+("0"*64)+".bin"},
                method="PUT",body=b"invalid-sha-v72-probe-no-write",
                write=True)
        except R2IndexError as error:
            if str(error)!="WF_INDEX_SHA_REJECTED":
                emit({"status":"WF_V72_WRITER_ROUTE_PROBE_FAILED",
                      "code":str(error),"r2_object_mutation_expected":False})
                return 1
            emit({
              "status":"WF_V72_LIVE_READER_AND_WRITER_ROUTES_VERIFIED",
              "read_route":True,
              "writer_secret_accepted":True,
              "deliberate_bad_sha_rejected":True,
              "worker_index_put_expected":False,
              "source_downloaded":False,
              "actual_index_published":False,
              "source_or_secret_logged":False,
            })
            return 0
        emit({"status":"WF_V72_UNSAFE_WRITER_ACCEPTED_BAD_SHA",
              "r2_object_mutation_possible":True})
        return 1
    except Exception as error:
        code=str(error)
        if not code.startswith(("WF_INDEX_","WF_V72_")):
            code="WF_V72_UNEXPECTED_PROBE_ERROR"
        emit({"status":"WF_V72_SAFE_ROUTE_PROBE_FAILED","code":code,
              "source_or_secret_logged":False})
        return 1

result=main()
print("WF_V72_LIVE_ROUTE_PROBE_EXIT="+str(result),flush=True)
time.sleep(7)
raise SystemExit(result)
