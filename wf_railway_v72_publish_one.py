"""V72 SINGLE-PASS genuine R2 index publisher; NEVER run before owner setup.

Required:
  Cloudflare existing Worker deploys V72 index routes and stores a separate
  WF_INDEX_UPLOAD_TOKEN Secret. Railway has that SAME secret variable.
  The existing WF_API_TOKEN remains source/index READ ONLY.

One eligible <=16MiB TXT per invocation. No GitHub Actions, no local volume,
no original upload, no repeated model calls. Output is scrubbed.
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

def emit(obj):
    print(json.dumps(obj,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V72_R2_PERSISTENCE_ONE_BOOK_START",flush=True)
def main():
    reader=os.getenv("WF_API_TOKEN")
    writer=os.getenv("WF_INDEX_UPLOAD_TOKEN")
    if not writer or not reader or writer==reader:
        emit({
          "status":"WF_V72_INDEX_WRITE_PERMISSION_NOT_CONFIGURED",
          "network_attempted":False,
          "writer_token_printed":False,
          "no_raw_source_modified":True,
        })
        return 1
    try:
        from writerforge.v72_persistent_index_pipeline import publish_one
        result=publish_one(progress=lambda step:emit({
            "status":step,"source_body_logged":False,"token_logged":False,
        }))
        emit(result)
        return 0
    except Exception as error:
        code=str(error)
        if not code.startswith((
          "WF_V72_","WF_INDEX_","WF_PRIVATE_","BULK_",
          "WF_R2_HTTP_","WF_V71_")):
            code="WF_V72_UNEXPECTED_INDEX_FAILURE"
        emit({"status":"WF_V72_INDEX_PUBLISH_FAILED",
              "error_code":code,
              "raw_original_logged":False,
              "original_object_write_attempts":0})
        return 1

ret=main()
print("WF_V72_R2_PUBLISH_EXIT="+str(ret),flush=True)
time.sleep(8)
raise SystemExit(ret)
