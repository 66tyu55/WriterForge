"""V77: zero-write live check of shared R2 index/LEARN writer.

Run ONLY after user updates their existing Cloudflare Worker to V77.
No new token: WF_INDEX_UPLOAD_TOKEN authorizes append-only learn/v1 events
and existing indexes/v1 chunks. WF_API_TOKEN remains source reader only.
This probe does not send book text, use DeepSeek, or write any R2 object.
"""
from __future__ import annotations
import json
import os
import sys
import time
import types
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,build_opener

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
pkg=types.ModuleType("writerforge")
pkg.__path__=[str(ROOT/"writerforge")]
pkg.__package__="writerforge"
sys.modules["writerforge"]=pkg
from writerforge.r2_learn_journal import WFLearnJournal,WFLearnJournalError
from writerforge.r2_worker_http import _NoBearerRedirect

URL="https://wf-r2-api.3227482831.workers.dev"

def report(v):
    print(json.dumps(v,ensure_ascii=False,sort_keys=True),flush=True)

print("WF_V77_SHARED_WRITER_ZERO_WRITE_PROBE_STARTED",flush=True)

def main():
    reader=os.environ.get("WF_API_TOKEN")
    index=os.environ.get("WF_INDEX_UPLOAD_TOKEN")
    if not reader or not index or reader==index:
        report({"status":"WF_V77_EXISTING_TWO_R2_TOKENS_INVALID",
                "model_calls":0,"r2_writes":0})
        return 1
    try:
        journal=WFLearnJournal(endpoint=URL)
        if not journal.require_writer_ready():
            raise WFLearnJournalError(
                "WF_V77_SHARED_WRITER_READINESS_FAILED")
        # Reader must never authenticate to LEARN writer preflight.
        opener=build_opener(_NoBearerRedirect())
        req=Request(URL+"/r2/learn/writer-ready",method="GET",
                    headers={"Authorization":"Bearer "+reader})
        try:
            with opener.open(req,timeout=25):
                raise WFLearnJournalError(
                    "WF_V77_SOURCE_READER_WRITER_BYPASS_DETECTED")
        except HTTPError as error:
            if error.code!=401:
                raise WFLearnJournalError(
                    "WF_V77_READER_DENIAL_STATUS_UNEXPECTED") from None
        checker=WFLearnJournal(endpoint=URL,read_only=True)
        if checker.writer is not None or not checker.read_only:
            raise WFLearnJournalError(
                "WF_V77_EXAMINER_NOT_STRICTLY_READ_ONLY")
        report({
            "status":"WF_V77_EXISTING_THREE_SECRETS_SHARED_WRITER_READY",
            "index_writer_authenticates_for_learn_only":True,
            "reader_denied_writer_endpoint":True,
            "examiner_read_only_mode_verified":True,
            "fourth_r2_secret_required":False,
            "existing_original_source_write_privilege":False,
            "real_private_source_bytes_read":0,
            "deepseek_model_calls":0,
            "r2_writes":0,
            "paid_literary_training_started":False,
        })
        return 0
    except (WFLearnJournalError,URLError,OSError) as exc:
        code=str(exc)
        if not code.startswith(("WF_LEARN_","WF_V77_","WF_R2_HTTP_")):
            code="WF_V77_LIVE_WORKER_NOT_READY_OR_NETWORK_ERROR"
        report({"status":"WF_V77_SHARED_WRITER_READY_CHECK_FAILED",
                "error_code":code,"r2_writes":0,
                "deepseek_model_calls":0,
                "private_text_or_token_logged":False})
        return 1

result=main()
print("WF_V77_SHARED_WRITER_PROBE_EXIT="+str(result),flush=True)
time.sleep(6)
raise SystemExit(result)
