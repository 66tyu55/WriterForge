"""V69 one-shot REAL metadata-only private-reading R2 inventory.

Starts WF's Python client with existing Railway WF_API_TOKEN. No models or
source text enter console output. Queries four approved real R2 folders and
one byte from one valid source object in each folder.
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
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg

print("WF_V69_PRIVATE_READING_SCAN_STARTED",flush=True)
def safe_report(d):
    print(json.dumps(d,ensure_ascii=False,sort_keys=True),flush=True)

def main():
    if not os.getenv("WF_API_TOKEN"):
        safe_report({"status":"WF_V69_TOKEN_NOT_CONFIGURED",
                     "remote_requests_attempted":False})
        return 1
    try:
        from writerforge.private_reading_remote import run_ephemeral_inventory
        result=run_ephemeral_inventory(
            "https://wf-r2-api.3227482831.workers.dev")
        safe_report({"status":"WF_V69_REMOTE_SCAN_SUCCESS", **result})
        return 0
    except Exception as exc:
        code=str(exc)
        if not code.startswith(("WF_PRIVATE_","BULK_","WF_R2_HTTP_")):
            code="WF_V69_UNEXPECTED_ERROR"
        safe_report({"status":"WF_V69_REMOTE_SCAN_FAILED",
                     "error_code":code,"source_text_printed":False,
                     "token_printed":False})
        return 1

answer=main()
print("WF_V69_SCAN_EXIT_CODE="+str(answer),flush=True)
time.sleep(8)
raise SystemExit(answer)
