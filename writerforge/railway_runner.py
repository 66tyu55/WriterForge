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
    if os.environ.get("WF_TASK") == "literary_exam_v67":
        # Examination question is separate from WF's search implementation.
        # The answer is NEVER supplied by evaluator code or an LLM.
        from pathlib import Path
        from .r2_literary_exam import run_literary_retrieval_exam
        exam_path = Path("eval/v67_literary_source_question.json")
        emit({**label, "status": "WF_LITERARY_EXAM_QUESTION_RECEIVED",
              "exam_id": "V67-LAOCAN-FIRST-ORIGINAL-OCCURRENCE",
              "token_present": True, "token_printed": False})
        try:
            client = WFWorkerR2Client(endpoint=ENDPOINT)
            result = run_literary_retrieval_exam(client, question_path=exam_path)
        except WFWorkerAPIError as exc:
            emit({**label, "status": "WF_LITERARY_EXAM_RETRIEVAL_FAILED",
                  "error_code": str(exc),
                  "safe_http_diagnostic": getattr(exc, "metadata", None),
                  "answer_generated": False, "token_printed": False})
            return 2
        except Exception:
            emit({**label, "status": "WF_LITERARY_EXAM_SOURCE_OR_PARSER_FAILED",
                  "answer_generated": False, "token_printed": False})
            return 2
        emit({**label, "status": "WF_LITERARY_EXAM_SUCCESS",
              "result": result, "token_printed": False})
        return 0

    emit({**label, "status": "WF_HTTP_REQUEST_STARTED", "token_present": True, "token_printed": False})
    client = None
    try:
        client = WFWorkerR2Client(endpoint=ENDPOINT)
        result = client.inventory()
    except WFWorkerAPIError as exc:
        diagnostic = getattr(exc, "metadata", None)
        # If the inventory route is absent, try the independently deployed
        # one-object /r2/status probe. Do NOT claim full inventory success.
        if client and str(exc) == "WF_R2_HTTP_ROUTE_NOT_DEPLOYED":
            try:
                status = client.r2_status()
                emit({**label,
                      "status": "WF_R2_STATUS_SUCCESS_INVENTORY_ROUTE_MISSING",
                      "inventory_error": str(exc),
                      "result": status,
                      "token_printed": False})
                return 0
            except WFWorkerAPIError as status_exc:
                status_diag = {
                    "inventory_error": str(exc),
                    "inventory_http": diagnostic,
                    "r2_status_error": str(status_exc),
                    "r2_status_http": getattr(status_exc, "metadata", None),
                }
                try:
                    status_diag["authenticated_health"] = client.authenticated_health()
                except WFWorkerAPIError as health_exc:
                    status_diag["health_error"] = str(health_exc)
                    status_diag["health_http"] = getattr(health_exc, "metadata", None)
                emit({**label, "status": "WF_WORKER_ROUTE_DIAGNOSTIC_FAILED",
                      "safe_http_diagnostic": status_diag,
                      "token_printed": False})
                return 1
        if isinstance(diagnostic, dict) and diagnostic.get("http_status") == 403 and client:
            diagnostic = {**diagnostic,
                          "without_token_health": client.probe_public_health_unauthenticated()}
        emit({**label, "status": "WF_R2_HTTP_FAILED",
              "error_code": str(exc),
              "safe_http_diagnostic": diagnostic,
              "token_printed": False})
        return 1
    except Exception:
        emit({**label, "status": "WF_R2_HTTP_UNEXPECTED_ERROR",
              "token_printed": False})
        return 1
    emit({**label, "status": "WF_R2_HTTP_SUCCESS", "result": result})
    return 0


if __name__ == "__main__":
    sys.exit(main())
