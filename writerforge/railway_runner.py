"""Railway one-shot WF worker runner.

Boots the actual WriterForge Python package and runs its native authenticated
Cloudflare Worker R2 inventory client. No HTTP listener, GitHub Actions, SQL,
corpus download, persistence, token logs or scheduled recurring requests.
"""
from __future__ import annotations

import json
import os
import sys

from .r2_worker_http import WFWorkerAPIError, WFWorkerR2Client

ENDPOINT = "https://wf-r2-api.3227482831.workers.dev"


def emit(doc: dict) -> None:
    print(json.dumps(doc, ensure_ascii=False, sort_keys=True), flush=True)


def main() -> int:
    label = {
        "component": "writerforge.railway_runner",
        "runtime": "RAILWAY_PYTHON",
        "invoked_by": "WRITERFORGE_PROCESS",
        "deployment_id": os.environ.get("RAILWAY_DEPLOYMENT_ID"),
        "github_commit": os.environ.get("RAILWAY_GIT_COMMIT_SHA"),
    }
    # Missing secret is a safe idle waiting state, NOT a real R2 failure.
    # Setting WF_API_TOKEN in Railway Variables causes a fresh deployment.
    if not os.environ.get("WF_API_TOKEN"):
        emit({**label, "status": "WAITING_FOR_RAILWAY_WF_API_TOKEN",
              "attempted_remote_request": False,
              "no_github_actions": True})
        return 0
    try:
        result = WFWorkerR2Client(endpoint=ENDPOINT).inventory()
    except WFWorkerAPIError as exc:
        emit({**label, "status": "WF_R2_HTTP_FAILED",
              "error_code": str(exc), "token_printed": False})
        return 1
    except Exception:
        emit({**label, "status": "WF_R2_HTTP_UNEXPECTED_ERROR",
              "token_printed": False})
        return 1
    emit({**label, "status": "WF_R2_HTTP_SUCCESS", "result": result})
    return 0


if __name__ == "__main__":
    sys.exit(main())
