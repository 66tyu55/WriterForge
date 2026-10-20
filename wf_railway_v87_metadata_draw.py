"""V87 phase 1: only private R2 /list metadata, anonymous random precommit.

No model or writer secrets in this process. No novel text, full source byte
or titles are printed, downloaded or saved. No seed supplied after seeing
source metadata. The result is pinned in GitHub BEFORE any text extraction.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
for name in ("DEEPSEEK_API_KEY","WF_INDEX_UPLOAD_TOKEN",
             "WF_LEARN_UPLOAD_TOKEN","DISCOVERY_API_KEY"):
    os.environ.pop(name,None)

def emit(doc):
    print(json.dumps(doc,sort_keys=True,ensure_ascii=False),flush=True)

def main():
    if not os.getenv("WF_API_TOKEN"):
        emit({"status":"WF87_READER_CREDENTIAL_NAME_MISSING",
              "model_calls":0,"r2_writes":0})
        return 1
    try:
        from writerforge.bulk_inbox import BulkCatalog
        from writerforge.private_reading_remote import WFPrivateReadingClient
        from writerforge.v87_random_holdout import (
            metadata_only_plan,inventory_metadata_only,canonical,
        )
        with TemporaryDirectory(prefix="wf87-anonymous-draw-") as folder:
            c=BulkCatalog(Path(folder)/"metadata.sqlite3")
            try:
                client=WFPrivateReadingClient(
                    endpoint="https://wf-r2-api.3227482831.workers.dev",
                    timeout=70)
                scanned=inventory_metadata_only(client,c)
                plan=metadata_only_plan(c)
                emit({
                    "status":"WF87_REAL_R2_RANDOM_METADATA_PLAN_FROZEN",
                    "metadata_scan":scanned,
                    "plan":plan,
                    "paid_model_calls":0,
                    "r2_writes":0,
                    "whole_novel_prose_exposed":False,
                    "novel_originals_opened":0,
                    "automatically_run_chapter_training":False,
                    "literary_grade_unchanged":True,
                })
                return 0
            finally:
                c.close()
    except Exception as exc:
        error=str(exc)
        if not error.startswith(("WF87_","WF_PRIVATE_","BULK_",
                                "WF_V71_","WF_BATCH_")):
            error="WF87_DRAW_UNEXPECTED_ERROR"
        emit({
            "status":"WF87_RANDOM_METADATA_DRAW_FAILED",
            "reason_code":error,
            "paid_model_calls":0,"r2_writes":0,
            "private_titles_prose_or_keys_logged":False,
        })
        return 1

print("WF87_METADATA_RANDOM_DRAW_START",flush=True)
ret=main()
print("WF87_METADATA_RANDOM_DRAW_EXIT="+str(ret),flush=True)
time.sleep(3)
raise SystemExit(ret)
