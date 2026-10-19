"""V69 private-reading/R2 source inventory transport; authenticated, read-only.

WF Python, not GPT, requests ONLY metadata for these four existing R2
folders: single-works/, 仙侠/, 历史/, 科幻/. Does not print names, source prose,
Bearer token, or raw Worker response bodies. Metadata is not literary study.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request
import json
import re

from .bulk_inbox import BulkCatalog, PRIVATE_FOLDERS, PRIVATE_READING, parse_key
from .r2_worker_http import WFWorkerAPIError, WFWorkerR2Client

FOLDERS = ("single-works", "仙侠", "历史", "科幻")
MAX_PAGES_PER_FOLDER = 64
MAX_OBJECTS = 10_000
MAX_JSON_BYTES = 192 * 1024
MAX_OBJECT_SIZE = 256 * 1024 * 1024
MAX_KEY_UTF8 = 1536

class PrivateReadingError(WFWorkerAPIError):
    pass

def require(condition, code):
    if not condition:
        raise PrivateReadingError(code)

def error_for_status(status):
    return {400:"WF_PRIVATE_QUERY_REJECTED",
            401:"WF_PRIVATE_NOT_AUTHORIZED",
            403:"WF_PRIVATE_FORBIDDEN",
            404:"WF_PRIVATE_ROUTE_NOT_DEPLOYED",
            405:"WF_PRIVATE_METHOD_NOT_ALLOWED",
            413:"WF_PRIVATE_OBJECT_TOO_LARGE",
            416:"WF_PRIVATE_RANGE_NOT_ALLOWED",
            429:"WF_PRIVATE_RATE_LIMITED",
            502:"WF_PRIVATE_R2_ERROR"}.get(
                status, "WF_PRIVATE_HTTP_ERROR")

class WFPrivateReadingClient(WFWorkerR2Client):
    def _request(self, path, params, *, method="GET", cap=MAX_JSON_BYTES):
        require(path in ("/r2/private-reading/list",
                         "/r2/private-reading/object"),
                "WF_PRIVATE_PATH_NOT_ALLOWED")
        require(method in ("GET","HEAD"),"WF_PRIVATE_METHOD_NOT_ALLOWED")
        req=Request(self.endpoint+path+"?"+urlencode(params),
            method=method,
            headers={"Authorization":"Bearer "+self.token,
                     "Accept":"application/json" if path.endswith("list")
                              else "application/octet-stream",
                     "User-Agent":"WF-Private-Reading-V69/1"})
        try:
            with self._opener.open(req,timeout=self.timeout) as response:
                expected=(206 if "offset" in params else 200)
                require(response.status==expected,
                        "WF_PRIVATE_HTTP_RESPONSE_UNEXPECTED")
                headers=response.headers
                raw=response.read(cap+1) if method=="GET" else b""
                require(len(raw)<=cap,"WF_PRIVATE_RESPONSE_TOO_LARGE")
                return headers, raw
        except HTTPError as exc:
            raise PrivateReadingError(error_for_status(exc.code)) from None
        except (URLError,TimeoutError,OSError):
            raise PrivateReadingError("WF_PRIVATE_NETWORK_FAILED") from None

    def list_page(self,folder,*,cursor=None):
        require(folder in PRIVATE_FOLDERS,
                "WF_PRIVATE_FOLDER_NOT_ALLOWED")
        require(cursor is None or
                (isinstance(cursor,str) and 1<=len(cursor)<=2048 and
                 all(ord(c)>=32 for c in cursor)),
                "WF_PRIVATE_CURSOR_INVALID")
        p={"folder":folder}
        if cursor is not None:p["cursor"]=cursor
        _,raw=self._request("/r2/private-reading/list",p)
        try:
            body=json.loads(raw)
        except (ValueError,UnicodeError):
            raise PrivateReadingError("WF_PRIVATE_LIST_JSON_INVALID") from None
        require(isinstance(body,dict) and body.get("ok") is True and
                body.get("read_only") is True and
                body.get("format")=="wf.private-reading-list.v1" and
                body.get("folder")==folder and
                isinstance(body.get("objects"),list) and
                len(body["objects"])<=64 and
                type(body.get("complete")) is bool,
                "WF_PRIVATE_LIST_SCHEMA_INVALID")
        next_cursor=body.get("next_cursor")
        require((body["complete"] and next_cursor is None) or
                (not body["complete"] and isinstance(next_cursor,str) and
                 1<=len(next_cursor)<=2048 and next_cursor!=cursor),
                "WF_PRIVATE_LIST_PAGINATION_INCONSISTENT")
        records=[]
        for obj in body["objects"]:
            require(isinstance(obj,dict),"WF_PRIVATE_ENTRY_NOT_DICT")
            key=obj.get("key")
            require(isinstance(key,str) and
                    len(key.encode("utf8"))<=MAX_KEY_UTF8 and
                    key.startswith(PRIVATE_READING+folder+"/"),
                    "WF_PRIVATE_ENTRY_OUTSIDE_FOLDER")
            # parse_key is a separate source of path validation. Nothing
            # resembling slash traversal, encoding ambiguity or executables
            # is allowed to become a searchable novel.
            info=parse_key(key)
            require(info["folder"]==folder,"WF_PRIVATE_ENTRY_SCOPE_ERROR")
            size=obj.get("size")
            require(type(size) is int and 0<=size<=10*1024**3,
                    "WF_PRIVATE_ENTRY_SIZE_INVALID")
            etag=obj.get("etag")
            require(etag is None or isinstance(etag,str) and
                    0<len(etag)<=256 and "\n" not in etag
                    and "\r" not in etag,
                    "WF_PRIVATE_ENTRY_ETAG_INVALID")
            records.append({"key":key,"size":size,"etag":etag})
        return records,next_cursor,body

    def check_ranged_read(self, record):
        """One-byte GET, never emit original byte; prove content path deployed."""
        key=record["key"]
        info=parse_key(key)
        require(info["ext"] in (".txt",".md",".epub",".zip",".rar",".7z",".pdf"),
                "WF_PRIVATE_PROBE_UNSUPPORTED_FILE")
        size=record["size"]
        require(type(size) is int and 0<size<=MAX_OBJECT_SIZE,
                "WF_PRIVATE_PROBE_TOO_LARGE")
        params={"key":key}
        head,empty=self._request("/r2/private-reading/object",params,method="HEAD")
        require(not empty,"WF_PRIVATE_HEAD_BODY_NONEMPTY")
        require(head.get("X-WF-Object-Size")==str(size) and
                head.get("Content-Length")==str(size),
                "WF_PRIVATE_HEAD_SIZE_MISMATCH")
        head_tag=head.get("ETag")
        expected=record.get("etag")
        if expected is not None:
            require(head_tag==expected,"WF_PRIVATE_HEAD_ETAG_CHANGED")
        require(isinstance(head_tag,str) and bool(head_tag),
                "WF_PRIVATE_HEAD_ETAG_MISSING")
        headers,data=self._request("/r2/private-reading/object",
            {"key":key,"offset":0,"length":1},cap=1)
        require(len(data)==1 and
                headers.get("Content-Range")==f"bytes 0-0/{size}" and
                headers.get("X-WF-Object-Size")==str(size) and
                headers.get("ETag")==head_tag,
                "WF_PRIVATE_RANGE_PROBE_INVALID")
        return {"verified":True,"bytes_fetched":1,"remote_write_requests":0}

    def inventory_to_catalog(self,catalog,max_objects=MAX_OBJECTS):
        require(isinstance(catalog,BulkCatalog) and
                type(max_objects) is int and 1<=max_objects<=MAX_OBJECTS,
                "WF_PRIVATE_INVENTORY_CONFIGURATION_INVALID")
        scan={"format":"wf.private-reading-metadata-scan.v1",
              "remote_write_requests":0,"literary_model_calls":0,
              "original_prose_exposed_in_report":False,
              "index_sql_created":False,
              "all_folders_complete":False,
              "folder_summary":{},
              "total_objects":0,"total_bytes":0,"total_pages":0,
              "catalog_is_snapshot":True,
              "newly_uploaded_objects_proven":False}
        samples={}
        for folder in FOLDERS:
            cursor=None
            seen=set()
            seen_object_keys=set()
            counted=0
            total=0
            pages=0
            extensions=Counter()
            states=Counter()
            first=None
            while pages<MAX_PAGES_PER_FOLDER:
                records,continuation,_=self.list_page(folder,cursor=cursor)
                pages+=1
                for rec in records:
                    if rec["key"] in seen_object_keys:
                        raise PrivateReadingError("WF_PRIVATE_DUPLICATE_LIST_KEY")
                    seen_object_keys.add(rec["key"])
                    counted+=1
                    total+=rec["size"]
                    info=parse_key(rec["key"])
                    extensions[info["ext"] or "(none)"]+=1
                    states[info["status"]]+=1
                    if first is None and rec["size"]>0 and rec["size"]<=MAX_OBJECT_SIZE and \
                           info["ext"] in (".txt",".md",".epub",".zip",".rar",".7z",".pdf"):
                        first=rec
                scan["total_objects"]+=len(records)
                scan["total_bytes"]+=sum(r["size"] for r in records)
                scan["total_pages"]+=1
                require(scan["total_objects"]<=max_objects,
                        "WF_PRIVATE_OBJECT_BUDGET_EXCEEDED")
                # Database only records metadata. Full novels stay in R2.
                catalog.register(records)
                if continuation is None:break
                require(continuation not in seen,
                        "WF_PRIVATE_REPEATED_CURSOR")
                seen.add(continuation)
                cursor=continuation
            else:
                raise PrivateReadingError("WF_PRIVATE_PAGE_BUDGET_EXCEEDED")
            scan["folder_summary"][folder]={
                "objects":counted,"bytes":total,"pages":pages,
                "extensions":dict(extensions),
                "states":dict(states),
            }
            samples[folder]=first
        scan["all_folders_complete"]=True
        scan["catalog"]=catalog.summary()
        # Query one byte from one source per folder, proving R2 READ
        # without downloading a novel or logging private paths/content.
        probes={}
        for folder,rec in samples.items():
            if rec is None:
                probes[folder]={"status":"NO_SUPPORTED_FILE_WITHIN_LIMIT"}
                continue
            try:
                self.check_ranged_read(rec)
                probes[folder]={"status":"ONE_BYTE_READ_OK"}
            except PrivateReadingError as exc:
                probes[folder]={"status":"FAILED","code":str(exc)}
        scan["ranged_read_probes"]=probes
        scan["ranged_read_probes_passed"]=sum(
            p["status"]=="ONE_BYTE_READ_OK" for p in probes.values())
        return scan

def run_ephemeral_inventory(endpoint):
    """Existing Railway has no volume: no misleading durability claims."""
    client=WFPrivateReadingClient(endpoint=endpoint)
    with TemporaryDirectory(prefix="wf-private-readonly-") as temp:
        catalog=BulkCatalog(Path(temp)/"metadata.sqlite3")
        try:
            result=client.inventory_to_catalog(catalog)
        finally:
            catalog.close()
    result["catalog_persisted_after_process_exit"]=False
    result["r2_objects_modified"]=0
    return result
