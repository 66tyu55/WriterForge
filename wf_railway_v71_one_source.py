"""Real one-shot WF V71 private R2 -> temporary SQLite engineering trial.

One TXT <=16MiB chosen by metadata topology only. Never logs titles,
private keys, query term, excerpt, token or original text. No R2 writes.
Results are explicitly ephemeral, not 50-book persistence or literary skill.
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

print("WF_V71_ONE_SOURCE_SQL_RUN_STARTED",flush=True)
def emit(o):
    print(json.dumps(o,ensure_ascii=False,sort_keys=True),flush=True)

def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF_V71_TOKEN_MISSING",
              "network_attempted":False})
        return 1
    try:
        from writerforge.private_r2_sql_smoke import index_one_real_source
        data=index_one_real_source("https://wf-r2-api.3227482831.workers.dev")
        emit({"status":"WF_V71_REAL_R2_ONE_SOURCE_INDEXED_TEMPORARILY",**data})
        return 0
    except Exception as exc:
        reason=str(exc)
        if not reason.startswith((
            "WF_V71_","WF_PRIVATE_","WF_V70_","BULK_","WF_R2_HTTP_")):
            reason="WF_V71_UNEXPECTED_ERROR"
        emit({"status":"WF_V71_REAL_R2_INDEX_FAILED",
              "error_code":reason,
              "original_source_text_logged":False,
              "private_key_logged":False,
              "api_token_logged":False})
        return 1

status=main()
print("WF_V71_SQL_RUN_EXIT_CODE="+str(status),flush=True)
time.sleep(8)
raise SystemExit(status)
