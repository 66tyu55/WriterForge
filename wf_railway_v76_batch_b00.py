"""V76 B00 real, strict, no-paid-call preliminary batch on Railway.

This one-shot runner exercises WriterForge itself (not GPT) against the
already authorised private R2 Worker using *read-only* WF_API_TOKEN.
Selects max 2 source candidates each for three pre-registered categories,
total <=6 downloads and <=48MiB. Doesn't read private titles into logs.

No DeepSeek key or any R2 writer token available to this process. The
experimental batch does not yet start literary reading because a dedicated
immutable LEARN Worker route/token is not deployed.
"""
from __future__ import annotations

import json
import os
import sys
import time
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
# No model/WF writer privileges in pure source-admission stage.
for forbidden in (
    "DEEPSEEK_API_KEY","DISCOVERY_API_KEY",
    "WF_INDEX_UPLOAD_TOKEN","WF_LEARN_UPLOAD_TOKEN",
):
    os.environ.pop(forbidden,None)

pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

def emit(doc):
    print(json.dumps(doc,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V76_BATCH_B00_READ_ONLY_START",flush=True)
def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_B00_PRIVATE_R2_READER_MISSING",
              "actual_remote_calls":0,"literary_model_calls":0})
        return 1
    try:
        from writerforge.wf_batch_supervisor import (
            preflight_one_batch,BatchPlan,WFBatchAuditError,
        )
        data=preflight_one_batch(
            progress=lambda state:emit({"status":state,
             "novel_prose_logged":False,"model_calls":0,
             "r2_writes":0}),
            plan=BatchPlan())
        emit(data)
        return 0
    except Exception as exc:
        code=str(exc)
        if not code.startswith((
            "WF_BATCH_","WF_ADMISSION_",
            "WF_PRIVATE_","BULK_","WF_V71_",
        )):
            code="WF_B00_UNEXPECTED_PREFLIGHT_FAILURE"
        emit({"status":"WF_B00_PREFLIGHT_STOPPED",
              "error_code":code,
              "private_source_or_token_logged":False,
              "literary_model_calls":0,
              "remote_r2_writes":0,
              "learned_chapters_claimed":0})
        return 1

exitcode=main()
print("WF_V76_BATCH_B00_EXIT="+str(exitcode),flush=True)
time.sleep(6)
raise SystemExit(exitcode)
