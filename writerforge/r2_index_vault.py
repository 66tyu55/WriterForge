"""V72: R2 is the ONLY durable store for WF's per-book SQLite indexes.

All source files stay in the user's private R2; all indexes stay under the
separately guarded writerforge/v1/indexes/v1/ prefix. This module uploads
content-addressed <=1MiB SQLite chunks and PUBLISHES an immutable manifest
LAST. Future WF processes restore ONLY the requested index, verify every
chunk/full SQLite SHA and open SQLite in query_only mode.

Read bearer WF_API_TOKEN does NOT authorize publishing. The distinct
WF_INDEX_UPLOAD_TOKEN must be configured by the owner before real writes.
No local persistent Railway volume, GitHub Actions, model, prose logs, delete,
rename, or change to the original R2 source objects.
"""
from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.parse import quote,urlencode
from urllib.request import Request
import json
import os
import re
import sqlite3

from .r2_worker_http import WFWorkerR2Client
from .bulk_inbox import parse_key

BASE="writerforge/v1/indexes/v1/"
MANIFEST_FORMAT="writerforge.r2.index.v1"
REFS_FORMAT="writerforge.index-ref-list.v1"
SCHEMA="v68.lexical.v1"
PART_BYTES=1024*1024
MAX_SQLITE_BYTES=256*1024*1024
MAX_CHUNKS=256
MAX_MANIFEST_BYTES=64*1024
SHA=re.compile(r"[a-f0-9]{64}\Z")
BOOK=re.compile(r"b_[a-f0-9]{32}\Z")
CATEGORIES=frozenset((
    "仙侠","科幻","历史","待分类","玄幻","古典","武侠",
    "都市","悬疑","灵异","言情","游戏","军事",
    "竞技","体育","轻小说","奇幻",
))

class R2IndexError(RuntimeError):
    pass

def need(ok,reason):
    if not ok:raise R2IndexError(reason)

def canonical(doc):
    return json.dumps(doc,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf-8")

def digest(raw):
    return sha256(raw).hexdigest()

def digest_file(file):
    h=sha256()
    with Path(file).open("rb") as reader:
        for block in iter(lambda:reader.read(PART_BYTES),b""):
            h.update(block)
    return h.hexdigest()

def key_sha(original_key):
    need(isinstance(original_key,str) and
         original_key.startswith("writerforge/v1/private-reading/"),
         "WF_INDEX_ORIGINAL_NOT_PRIVATE_READING")
    parse_key(original_key)
    return digest(original_key.encode("utf-8"))

def chunk_key(hash_):
    need(isinstance(hash_,str) and SHA.fullmatch(hash_),
         "WF_INDEX_CHUNK_HASH_INVALID")
    return BASE+"chunks/"+hash_+".bin"

def manifest_key(original_key_hash,manifest_digest):
    need(isinstance(original_key_hash,str) and SHA.fullmatch(original_key_hash)
         and isinstance(manifest_digest,str) and SHA.fullmatch(manifest_digest),
         "WF_INDEX_MANIFEST_KEY_INVALID")
    return BASE+"refs/"+original_key_hash+"/"+manifest_digest+".json"

def validate_manifest(doc,original_key=None):
    need(isinstance(doc,dict) and
         set(doc)=={
          "format","source_key_sha256","source_sha256","source_size",
          "source_etag","book_id","parser_version","index_sha256",
          "index_bytes","chunks","units","chapters","encoding",
          "provisional_legacy","literary_verified","category",
         }, "WF_INDEX_MANIFEST_FIELDS_INVALID")
    need(doc["format"]==MANIFEST_FORMAT and
         doc["parser_version"]==SCHEMA and
         isinstance(doc["source_key_sha256"],str) and
         SHA.fullmatch(doc["source_key_sha256"]) and
         isinstance(doc["source_sha256"],str) and
         SHA.fullmatch(doc["source_sha256"]) and
         isinstance(doc["index_sha256"],str) and
         SHA.fullmatch(doc["index_sha256"]) and
         doc["book_id"]=="b_"+doc["source_sha256"][:32] and
         type(doc["source_size"]) is int and
         0<doc["source_size"]<=MAX_SQLITE_BYTES and
         isinstance(doc["source_etag"],str) and
         2<=len(doc["source_etag"])<=200 and
         type(doc["index_bytes"]) is int and
         0<doc["index_bytes"]<=MAX_SQLITE_BYTES and
         type(doc["units"]) is int and doc["units"]>0 and
         type(doc["chapters"]) is int and doc["chapters"]>=0 and
         doc["encoding"] in ("utf-8","utf-8-sig","utf-16","gb18030") and
         type(doc["provisional_legacy"]) is bool and
         doc["literary_verified"] is False and
         doc["category"] in CATEGORIES and
         isinstance(doc["chunks"],list) and
         1<=len(doc["chunks"])<=MAX_CHUNKS,
         "WF_INDEX_MANIFEST_SCHEMA_INVALID")
    if original_key is not None:
        need(doc["source_key_sha256"]==key_sha(original_key),
             "WF_INDEX_MANIFEST_OTHER_SOURCE")
    amount=0
    for piece in doc["chunks"]:
        need(isinstance(piece,dict) and
             set(piece)=={"sha256","size"} and
             isinstance(piece["sha256"],str) and
             SHA.fullmatch(piece["sha256"]) and
             type(piece["size"]) is int and
             0<piece["size"]<=PART_BYTES,
             "WF_INDEX_MANIFEST_PART_INVALID")
        amount+=piece["size"]
    need(amount==doc["index_bytes"],
         "WF_INDEX_MANIFEST_SIZE_SUM_MISMATCH")
    return doc

class R2IndexVault:
    """Immutable per-book indexes accessed via the authenticated WF Worker."""

    def __init__(self,*,endpoint,read_token=None,write_token=None,timeout=60):
        self.reader=WFWorkerR2Client(
            endpoint=endpoint, token=read_token,timeout=timeout)
        self._opener=self.reader._opener
        self.write_token=(write_token if write_token is not None
                          else os.environ.get("WF_INDEX_UPLOAD_TOKEN"))
        if self.write_token is not None:
            need(isinstance(self.write_token,str) and
                 len(self.write_token)>=24 and
                 "\n" not in self.write_token and
                 "\r" not in self.write_token and
                 self.write_token != self.reader.token,
                 "WF_INDEX_WRITE_TOKEN_UNSAFE_OR_SHARED")

    def _call(self,path,args,*,method="GET",body=None,
              write=False,cap=MAX_MANIFEST_BYTES):
        need(path in ("/r2/index/write","/r2/index/object","/r2/index/refs"),
             "WF_INDEX_UNKNOWN_HTTP_ROUTE")
        need(method in ("GET","HEAD","PUT") and
             ((method=="PUT")==write),"WF_INDEX_METHOD_AUTHORITY_INVALID")
        need(not write or bool(self.write_token),
             "WF_INDEX_UPLOAD_TOKEN_NOT_CONFIGURED")
        token=self.write_token if write else self.reader.token
        req=Request(self.reader.endpoint+path+"?"+urlencode(args),
                    method=method,data=body,
                    headers={"Authorization":"Bearer "+token,
                             "Accept":"application/json"
                             if path.endswith(("refs","write"))
                             else "application/octet-stream",
                             "User-Agent":"WriterForge-IndexVault/1.0"})
        try:
            with self._opener.open(req,timeout=self.reader.timeout) as response:
                expected=(206 if "offset" in args else 200)
                need(response.status==expected,
                     "WF_INDEX_HTTP_UNEXPECTED_STATUS")
                headers=response.headers
                raw=response.read(cap+1) if method!="HEAD" else b""
                need(len(raw)<=cap,"WF_INDEX_RESPONSE_TOO_LARGE")
                return headers,raw
        except HTTPError as exc:
            code={
                400:"WF_INDEX_BAD_REQUEST",
                401:"WF_INDEX_PERMISSION_DENIED",
                403:"WF_INDEX_FORBIDDEN",
                404:"WF_INDEX_ROUTE_OR_OBJECT_NOT_DEPLOYED",
                409:"WF_INDEX_IMMUTABLE_CONFLICT",
                413:"WF_INDEX_OBJECT_TOO_LARGE",
                416:"WF_INDEX_RANGE_REJECTED",
                422:"WF_INDEX_SHA_REJECTED",
                429:"WF_INDEX_THROTTLED",
                502:"WF_INDEX_REMOTE_READ_FAILURE",
                503:"WF_INDEX_WRITER_SECRET_UNAVAILABLE",
            }.get(exc.code,"WF_INDEX_REMOTE_FAILURE")
            raise R2IndexError(code) from None
        except (URLError,OSError,TimeoutError):
            raise R2IndexError("WF_INDEX_NETWORK_FAILURE") from None

    def _json(self,path,args,*,write=False,body=None):
        _,raw=self._call(path,args,method="PUT" if write else "GET",
                         write=write,body=body,cap=MAX_MANIFEST_BYTES)
        try: result=json.loads(raw.decode("utf-8"))
        except (ValueError,UnicodeError):
            raise R2IndexError("WF_INDEX_RESPONSE_NOT_JSON") from None
        need(isinstance(result,dict) and result.get("ok") is True,
             "WF_INDEX_RESPONSE_SCHEMA_INVALID")
        return result

    def _head(self,key):
        headers,_=self._call("/r2/index/object",{"key":key},method="HEAD")
        try: size=int(headers.get("X-WF-Object-Size",""))
        except ValueError:
            raise R2IndexError("WF_INDEX_HEAD_NO_SIZE") from None
        etag=headers.get("ETag")
        need(type(size) is int and size>0 and
             headers.get("Content-Length")==str(size) and
             isinstance(etag,str) and len(etag)>=2,
             "WF_INDEX_HEAD_INVALID")
        return size,etag

    def _index_bytes(self,key,length):
        size,etag=self._head(key)
        need(size==length and 0<length<=PART_BYTES,
             "WF_INDEX_OBJECT_LENGTH_MISMATCH")
        headers,data=self._call("/r2/index/object",
                               {"key":key,"offset":0,"length":length},
                               cap=PART_BYTES)
        need(len(data)==length and
             headers.get("Content-Range")==f"bytes 0-{length-1}/{length}" and
             headers.get("ETag")==etag and
             headers.get("X-WF-Object-Size")==str(length),
             "WF_INDEX_CONTENT_RANGE_INVALID")
        return data

    def _manifest_bytes(self,key):
        size,etag=self._head(key)
        need(size<=MAX_MANIFEST_BYTES,"WF_INDEX_MANIFEST_SIZE_INVALID")
        headers,raw=self._call("/r2/index/object",{"key":key},
                               cap=MAX_MANIFEST_BYTES)
        need(len(raw)==size and
             headers.get("ETag")==etag,
             "WF_INDEX_MANIFEST_HEAD_CHANGED")
        return raw

    def manifest_refs(self,source_key_hash):
        need(isinstance(source_key_hash,str) and
             SHA.fullmatch(source_key_hash),"WF_INDEX_SOURCE_KEY_HASH_INVALID")
        cursor=None
        seen=set()
        sha_list=[]
        for page in range(32):
            args={"source_key_sha":source_key_hash}
            if cursor:args["cursor"]=cursor
            result=self._json("/r2/index/refs",args)
            need(result.get("format")==REFS_FORMAT and
                 result.get("read_only") is True and
                 result.get("source_key_sha256")==source_key_hash and
                 type(result.get("complete")) is bool and
                 isinstance(result.get("manifests"),list) and
                 len(result["manifests"])<=32,
                 "WF_INDEX_REF_PAGE_INVALID")
            for ref in result["manifests"]:
                sha_value=ref.get("manifest_sha256") if isinstance(ref,dict) else None
                need(isinstance(sha_value,str) and SHA.fullmatch(sha_value)
                     and sha_value not in sha_list,
                     "WF_INDEX_REF_DUPLICATE_OR_INVALID")
                sha_list.append(sha_value)
            if result["complete"]:
                need(result.get("next_cursor") is None,
                     "WF_INDEX_COMPLETE_PAGE_WITH_CURSOR")
                return sha_list
            nxt=result.get("next_cursor")
            need(isinstance(nxt,str) and 1<=len(nxt)<=2048
                 and nxt not in seen,"WF_INDEX_BAD_REF_CURSOR")
            seen.add(nxt)
            cursor=nxt
        raise R2IndexError("WF_INDEX_REF_PAGE_BUDGET_EXCEEDED")

    def read_manifest(self,original_key,manifest_hash):
        need(isinstance(manifest_hash,str) and SHA.fullmatch(manifest_hash),
             "WF_INDEX_MANIFEST_SHA_INVALID")
        key=manifest_key(key_sha(original_key),manifest_hash)
        raw=self._manifest_bytes(key)
        need(digest(raw)==manifest_hash,
             "WF_INDEX_MANIFEST_SHA_MISMATCH")
        try:doc=json.loads(raw.decode("utf-8"))
        except (UnicodeError,ValueError):
            raise R2IndexError("WF_INDEX_MANIFEST_NOT_JSON") from None
        return validate_manifest(doc,original_key=original_key)

    def find_matching(self,record):
        """No full novel fetch; match current R2 object key+etag+size only.

        Multiple valid manifests for the same source are intentionally
        ambiguous until a specific content SHA is pinned by the caller.
        """
        original_key=record["key"]
        matches=[]
        for h in self.manifest_refs(key_sha(original_key)):
            manifest=self.read_manifest(original_key,h)
            if (manifest["source_etag"]==record.get("etag") and
                manifest["source_size"]==record.get("size") and
                manifest["parser_version"]==SCHEMA):
                matches.append({"manifest_sha256":h,
                                "index_sha256":manifest["index_sha256"],
                                "units":manifest["units"],
                                "provisional_legacy":manifest["provisional_legacy"]})
        return matches

    def _write_immutable(self,key,raw):
        need(isinstance(raw,bytes) and
             0<len(raw)<=PART_BYTES,
             "WF_INDEX_LOCAL_PART_TOO_LARGE")
        expected=digest(raw)
        need(key.endswith("/"+expected+".bin") or
             key.endswith("/"+expected+".json"),
             "WF_INDEX_WRITE_CONTENT_ADDRESS_INVALID")
        result=self._json("/r2/index/write",{"key":key},
                          write=True,body=raw)
        need(result.get("sha256")==expected and
             result.get("size")==len(raw) and
             result.get("immutable") is True and
             type(result.get("created")) is bool,
             "WF_INDEX_UPLOAD_RECEIPT_INVALID")
        return bool(result["created"])

    def publish(self,*,index_file,original_key,source_sha256,
                source_size,source_etag,category,encoding,
                provisional_legacy,units,chapters):
        """Upload only the SQLite index, never the original novel body."""
        need(bool(self.write_token),
             "WF_INDEX_UPLOAD_TOKEN_NOT_CONFIGURED")
        index=Path(index_file)
        need(index.is_file() and
             0<index.stat().st_size<=MAX_SQLITE_BYTES,
             "WF_INDEX_INPUT_SHARD_SIZE_INVALID")
        need(isinstance(source_sha256,str) and SHA.fullmatch(source_sha256)
             and type(source_size) is int and 0<source_size<=MAX_SQLITE_BYTES
             and isinstance(source_etag,str) and 2<=len(source_etag)<=200
             and category in CATEGORIES and
             encoding in ("utf-8","utf-8-sig","utf-16","gb18030") and
             type(provisional_legacy) is bool and
             type(units) is int and units>0 and
             type(chapters) is int and chapters>=0,
             "WF_INDEX_SOURCE_RECEIPT_INVALID")
        original_hash=key_sha(original_key)
        parts=[]
        created=0
        with index.open("rb") as handle:
            while block:=handle.read(PART_BYTES):
                need(len(parts)<MAX_CHUNKS,"WF_INDEX_PART_BUDGET_EXCEEDED")
                h=digest(block)
                created+=int(self._write_immutable(chunk_key(h),block))
                parts.append({"sha256":h,"size":len(block)})
        payload={
          "format":MANIFEST_FORMAT,"source_key_sha256":original_hash,
          "source_sha256":source_sha256,"source_size":source_size,
          "source_etag":source_etag,"book_id":"b_"+source_sha256[:32],
          "parser_version":SCHEMA,"index_sha256":digest_file(index),
          "index_bytes":index.stat().st_size,"chunks":parts,
          "units":units,"chapters":chapters,"encoding":encoding,
          "provisional_legacy":provisional_legacy,
          "literary_verified":False,"category":category,
        }
        validate_manifest(payload,original_key=original_key)
        raw=canonical(payload)
        need(len(raw)<=MAX_MANIFEST_BYTES,
             "WF_INDEX_MANIFEST_LOCAL_TOO_LARGE")
        h=digest(raw)
        manifest_created=self._write_immutable(
            manifest_key(original_hash,h),raw)
        return {
          "status":"R2_INDEX_MANIFEST_PUBLISHED",
          "manifest_sha256":h,
          "source_key_sha256":original_hash,
          "source_sha256":source_sha256,
          "index_sha256":payload["index_sha256"],
          "index_bytes":payload["index_bytes"],
          "units":units,"chapters":chapters,
          "chunks":len(parts),"new_chunks":created,
          "manifest_created":manifest_created,
          "literary_verified":False,
          "source_original_modified":False,
          "stored_in_r2":True,
          "sqlite_stored_on_railway_volume":False,
        }

    @contextmanager
    def restore(self,record,manifest_hash):
        """Download ONLY one indexed book, verify every chunk and full SQL.

        A source ETag mismatch requires rescanning original provenance before
        using this index; source identity is not certified by index hashes.
        """
        key=record["key"]
        manifest=self.read_manifest(key,manifest_hash)
        need(manifest["source_size"]==record.get("size") and
             manifest["source_etag"]==record.get("etag"),
             "WF_INDEX_ORIGINAL_OBJECT_CHANGED")
        with TemporaryDirectory(prefix="wf-r2-index-") as temp:
            shard=Path(temp)/"index.sqlite3"
            filehash=sha256()
            try:
                with shard.open("xb") as out:
                    for part in manifest["chunks"]:
                        b=self._index_bytes(
                            chunk_key(part["sha256"]),part["size"])
                        need(digest(b)==part["sha256"],
                             "WF_INDEX_PART_SHA_FAILED")
                        out.write(b)
                        filehash.update(b)
                need(shard.stat().st_size==manifest["index_bytes"]
                     and filehash.hexdigest()==manifest["index_sha256"],
                     "WF_INDEX_SQLITE_FULL_SHA_FAILED")
                db=sqlite3.connect(
                    "file:"+quote(str(shard.resolve()),safe="/")+"?mode=ro",
                    uri=True,cached_statements=32)
                try:
                    db.execute("PRAGMA query_only=ON")
                    db.execute("PRAGMA cache_size=-2048")
                    need(db.execute("PRAGMA quick_check").fetchone()[0]=="ok",
                         "WF_INDEX_SQLITE_CORRUPTED")
                    tags=dict(db.execute("SELECT key,value FROM meta"))
                    need(tags.get("source_sha256")==manifest["source_sha256"]
                         and tags.get("book_id")==manifest["book_id"]
                         and tags.get("parser_version")==SCHEMA
                         and int(tags.get("units","-1"))==manifest["units"],
                         "WF_INDEX_SQLITE_IDENTITY_MISMATCH")
                    yield db,manifest
                finally:
                    db.close()
            except BaseException:
                raise
