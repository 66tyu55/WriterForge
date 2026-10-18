"""Railway ONE-SHOT executable for WriterForge V67's real read-only study.

Run only after the user's existing Cloudflare Worker has /r2/object deployed.
No GitHub Actions, no public listener, no model, no hardcoded exam keywords,
no whole-R2 sync or persistent cache, and no API token in logs.
"""
from __future__ import annotations

import json
import os
import sys
import time
import types
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
module = types.ModuleType("writerforge")
module.__path__ = [str(ROOT / "writerforge")]
module.__package__ = "writerforge"
sys.modules["writerforge"] = module

ENDPOINT = "https://wf-r2-api.3227482831.workers.dev"
print("WF_V67_READONLY_LIBRARY_STARTED", flush=True)


def emit(data):
    print(json.dumps(data, ensure_ascii=False, sort_keys=True), flush=True)


def main():
    prefix = {
        "component": "writerforge.worker_readonly_library",
        "invoked_by": "WRITERFORGE_PYTHON_PROCESS",
        "runtime": "RAILWAY_PYTHON",
        "deployment_id": os.getenv("RAILWAY_DEPLOYMENT_ID"),
        "github_commit": os.getenv("RAILWAY_GIT_COMMIT_SHA"),
    }
    if not os.getenv("WF_API_TOKEN"):
        emit({**prefix, "status": "WAITING_FOR_ALREADY_CONFIGURED_WF_API_TOKEN",
              "remote_requests": 0})
        return 1
    started = perf_counter()
    try:
        from writerforge.worker_readonly_library import (
            WFWorkerLibraryClient, open_verified_study,
        )
        client = WFWorkerLibraryClient(endpoint=ENDPOINT)
        with open_verified_study(client) as book:
            # No source excerpts or question terms are printed by this probe.
            result = {
                "status": "WF_V67_LIBRARY_VERIFIED_READONLY",
                "library": book.library,
                "snapshot_sha256": book.snapshot,
                "work_id": book.work_id,
                "counts": book.counts,
                "verified_transferred_bytes": book.bytes_read,
                "catalog_edition_independently_verified": True,
                "sqlite_mode_ro": True,
                "sqlite_query_only": True,
                "remote_write_requests": 0,
                "all_bucket_objects_downloaded": False,
                "exam_question_seen_by_wf": False,
                "literary_judgment_tested": False,
                "model_calls": 0,
                "end_to_end_ms": round((perf_counter() - started) * 1000, 2),
            }
            emit({**prefix, **result})
            return 0
    except Exception as exc:
        # Safe code only. Never print exception tracebacks, object names,
        # token, original prose, HTTP response bodies or SQL query parameters.
        code = str(exc)
        if not (code.startswith("WF_LIBRARY_") or
                code.startswith("WF_R2_HTTP_")):
            code = "WF_V67_UNEXPECTED_FAILURE"
        emit({**prefix, "status": "WF_V67_LIBRARY_READ_FAILED",
              "error_code": code,
              "token_printed": False,
              "source_text_printed": False})
        return 1


exit_code = main()
print(f"WF_V67_READONLY_EXIT_CODE={exit_code}", flush=True)
time.sleep(8)
raise SystemExit(exit_code)
