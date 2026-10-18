"""WF native read-only HTTP adapter to an existing Cloudflare Worker R2 API.

Calls the user's Worker endpoint directly from the WriterForge PROCESS,
not via GitHub Actions, S3 keys or ChatGPT. Never stores, prints, logs or
uploads WF_API_TOKEN. A Worker inventory counts R2 OBJECTS, not novel
chapters, learned methods or SQL rows. This adapter is not literary study.
"""
from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import json
import os
import re


class WFWorkerAPIError(RuntimeError):
    pass


class WFWorkerHTTPStatusError(WFWorkerAPIError):
    def __init__(self, code: str, metadata: dict):
        super().__init__(code)
        # Safe boolean/status diagnostics only; no URL, body or auth headers.
        self.metadata = metadata


def _safe_http_metadata(exc: HTTPError) -> dict:
    headers = exc.headers
    raw_type = (headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
    content_type = raw_type if raw_type in (
        "application/json", "text/html", "text/plain", "application/problem+json"
    ) else "other"
    cf_ray = headers.get("CF-Ray") or ""
    ray_safe = cf_ray if re.fullmatch(r"[0-9a-fA-F]{8,20}-[A-Za-z0-9]{1,10}", cf_ray) else None
    # Read a tiny bounded amount ONLY to classify common edge errors; never
    # reproduce HTML, JSON, tokens or arbitrary untrusted response text.
    try:
        body = exc.read(4096).decode("utf-8", "replace").lower()
    except Exception:
        body = ""
    return {
        "http_status": exc.code,
        "content_type": content_type,
        "server_cloudflare": (headers.get("Server") or "").lower() == "cloudflare",
        "cf_ray": ray_safe,
        "cf_mitigated_challenge": (headers.get("cf-mitigated") or "").lower() == "challenge",
        "body_mentions_cloudflare": "cloudflare" in body,
        "body_mentions_error_1020": "error 1020" in body,
        "body_mentions_error_1015": "error 1015" in body,
        "body_mentions_access_denied": "access denied" in body,
        "body_mentions_forbidden": "forbidden" in body,
    }


class _NoBearerRedirect(HTTPRedirectHandler):
    # urllib's default redirects may copy Authorization to a new URL.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class WFWorkerR2Client:
    """Reusable transport for WF's authenticated read-only Worker.

    Supported deployed Worker route now: GET /r2/inventory.
    Book/SQLite routes must be implemented in the Worker before
    WF can legitimately claim remote source or SQL access.
    """
    def __init__(self, *, endpoint: str, token: str | None = None,
                 timeout: int = 30):
        if not isinstance(endpoint, str):
            raise WFWorkerAPIError("WF_R2_HTTP_ENDPOINT_INVALID")
        uri = urlsplit(endpoint.strip())
        if (uri.scheme != "https" or not uri.hostname or uri.username
                or uri.password or uri.port not in (None, 443)
                or uri.query or uri.fragment or uri.path not in ("", "/")
                or not uri.hostname.endswith(".workers.dev")):
            raise WFWorkerAPIError("WF_R2_HTTP_HTTPS_WORKER_REQUIRED")
        self.endpoint = f"https://{uri.hostname}"
        self.hostname = uri.hostname
        self.token = (token if token is not None
                      else os.environ.get("WF_API_TOKEN"))
        if (not isinstance(self.token, str)
                or len(self.token.strip()) < 24
                or "\n" in self.token or "\r" in self.token):
            raise WFWorkerAPIError(
                "WF_R2_HTTP_TOKEN_MISSING_CONFIGURE_WF_API_TOKEN_LOCALLY")
        self.token = self.token.strip()
        if type(timeout) is not int or not 1 <= timeout <= 90:
            raise WFWorkerAPIError("WF_R2_HTTP_TIMEOUT_INVALID")
        self.timeout = timeout
        self._opener = build_opener(_NoBearerRedirect())

    def _request_json(self, *, cursor: str | None = None) -> dict:
        if cursor is not None and (not isinstance(cursor, str)
                                   or not 1 <= len(cursor) <= 2048):
            raise WFWorkerAPIError("WF_R2_HTTP_CURSOR_INVALID")
        suffix = "/r2/inventory"
        if cursor:
            suffix += "?" + urlencode({"cursor": cursor})
        req = Request(
            self.endpoint + suffix, method="GET",
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/json",
                     "User-Agent": "WriterForge-R2-Client/1.0"})
        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                if response.status != 200:
                    raise WFWorkerAPIError("WF_R2_HTTP_BAD_STATUS")
                data = response.read(131073)
        except HTTPError as exc:
            # Never copy untrusted server bodies or credential-bearing URLs.
            code = {401: "WF_R2_HTTP_UNAUTHORIZED",
                    403: "WF_R2_HTTP_FORBIDDEN",
                    404: "WF_R2_HTTP_ROUTE_NOT_DEPLOYED",
                    429: "WF_R2_HTTP_RATE_LIMIT",
                    502: "WF_R2_HTTP_R2_FAILURE"}.get(
                        exc.code, "WF_R2_HTTP_REMOTE_FAILURE")
            raise WFWorkerHTTPStatusError(code, _safe_http_metadata(exc)) from None
        except (URLError, TimeoutError, OSError):
            raise WFWorkerAPIError("WF_R2_HTTP_CONNECTION_FAILED") from None
        if len(data) > 131072:
            raise WFWorkerAPIError("WF_R2_HTTP_RESPONSE_TOO_LARGE")
        try:
            result = json.loads(data)
        except (UnicodeError, ValueError):
            raise WFWorkerAPIError("WF_R2_HTTP_RESPONSE_NOT_JSON") from None
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise WFWorkerAPIError("WF_R2_HTTP_WORKER_REPORTED_FAILURE")
        return result

    def probe_public_health_unauthenticated(self) -> dict:
        """Single diagnostic GET without token, never reveals auth material.

        Expected response is 401 from the installed Worker. 403 with the same
        metadata suggests the request never reached the Worker application.
        """
        req = Request(self.endpoint + "/health", method="GET",
                      headers={"Accept": "application/json",
                               "User-Agent": "WriterForge-R2-Client/1.0"})
        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                return {"http_status": response.status,
                        "content_type": (response.headers.get("Content-Type") or "")
                                        .split(";", 1)[0].strip().lower()}
        except HTTPError as exc:
            return _safe_http_metadata(exc)
        except (URLError, OSError, TimeoutError):
            return {"error_code": "WF_R2_HTTP_PROBE_CONNECT_FAILED"}

    def inventory(self, *, max_requests: int = 30) -> dict:
        """Retrieve complete writerforge/v1 metadata, chasing all cursors.

        The Worker currently scans up to 10 R2 pages per HTTP request.
        Stop rather than call a partial batch a complete R2 inventory.
        """
        if type(max_requests) is not int or not 1 <= max_requests <= 50:
            raise WFWorkerAPIError("WF_R2_HTTP_REQUEST_BUDGET_INVALID")
        clock_started = datetime.now(timezone.utc).isoformat()
        start = perf_counter()
        seen_cursors = set()
        cursor = None
        page_count = object_count = byte_count = 0
        worker_ms = 0
        calls = 0
        while calls < max_requests:
            doc = self._request_json(cursor=cursor)
            calls += 1
            if (doc.get("scope") != "writerforge/v1/"
                    or type(doc.get("complete")) is not bool
                    or doc.get("read_only") is not True
                    or any(type(doc.get(k)) is not int or doc[k] < 0
                           for k in ("pages_scanned", "objects_scanned",
                                     "total_bytes"))
                    or type(doc.get("query_ms")) not in (int, float)
                    or doc["query_ms"] < 0):
                raise WFWorkerAPIError("WF_R2_HTTP_INVENTORY_SCHEMA_INVALID")
            page_count += doc["pages_scanned"]
            object_count += doc["objects_scanned"]
            byte_count += doc["total_bytes"]
            worker_ms += doc["query_ms"]
            if doc["complete"]:
                if doc.get("next_cursor") is not None:
                    raise WFWorkerAPIError("WF_R2_HTTP_COMPLETE_WITH_CURSOR")
                return {
                    "format": "writerforge.r2-worker-direct-inventory.v1",
                    "invoked_by": "WRITERFORGE_PYTHON_HTTP_CLIENT",
                    "transport": "HTTPS_WORKER_R2",
                    "worker_host": self.hostname,
                    "scope": "writerforge/v1/",
                    "complete": True,
                    "objects_scanned": object_count,
                    "total_object_bytes": byte_count,
                    "r2_pages_scanned": page_count,
                    "http_requests": calls,
                    "worker_metadata_query_ms_sum": round(worker_ms, 2),
                    "wf_http_end_to_end_ms": round(
                        (perf_counter() - start) * 1000, 2),
                    "started_at_utc": clock_started,
                    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    "original_novel_text_downloaded": False,
                    "sqlite_sql_executed": False,
                    "remote_writes_performed": 0,
                    "literary_knowledge_learned": False,
                    "api_token_in_output": False,
                }
            next_cursor = doc.get("next_cursor")
            if (not isinstance(next_cursor, str)
                    or not 1 <= len(next_cursor) <= 2048
                    or next_cursor in seen_cursors):
                raise WFWorkerAPIError("WF_R2_HTTP_INVALID_NEXT_CURSOR")
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        raise WFWorkerAPIError("WF_R2_HTTP_INVENTORY_INCOMPLETE_MAX_REQUESTS")
