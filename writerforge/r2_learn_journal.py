"""WriterForge V75: private-R2 immutable ordered LEARN journal (WF-owned).

PASS A is a sequence of immutable first-read observations. Every new unit
requires the R2 SHA of the previous unit. Only after all units are signed by
R2 can WF write a PASS A seal. PASS B analyses MUST reference that seal and
evidence from actual locked units. No READ/WRITE mixing and no ChatGPT
literary decisions.

The R2 storage Writer secret is separate from both the original-reader token
and the existing SQL-index writer token. Until the user deploys the candidate
V75 Cloudflare Worker AND separately sets WF_LEARN_UPLOAD_TOKEN in Cloudflare
and Railway, this module cannot mutate real R2.

Neither a record nor a model's self-evaluation proves human reader reactions,
literal chapter completeness, transfer of literary skill, or graduation.
"""
from __future__ import annotations

from hashlib import sha256
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request
from typing import Mapping
import json
import os
import re

from .r2_worker_http import WFWorkerR2Client

PREFIX="writerforge/v1/learn/v1/"
FORMAT="wf.learn.event.v1"
MODEL="deepseek-flash"
HASH=re.compile(r"^[a-f0-9]{64}$")
MAX_EVENT_BYTES=8192
MAX_CHAPTERS=2000
MAX_UNITS=2000
STAGES=frozenset(("first_read","seal","analysis"))

class WFLearnJournalError(RuntimeError):
    pass

def require(ok,code):
    if not ok:
        raise WFLearnJournalError(code)

def canonical(doc: Mapping) -> bytes:
    return json.dumps(doc,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf-8")

def hexdigest(b:bytes)->str:
    return sha256(b).hexdigest()

def validsha(s):
    return isinstance(s,str) and HASH.fullmatch(s) is not None

def path_for(*,source_key_sha,source_sha,chapter,stage,unit=None):
    require(validsha(source_key_sha) and validsha(source_sha) and
            type(chapter) is int and 1<=chapter<=MAX_CHAPTERS and
            stage in STAGES,
            "WF_LEARN_SOURCE_CHAPTER_OR_STAGE_INVALID")
    base=(PREFIX+source_key_sha+"/"+source_sha+"/"+
          f"{chapter:06d}/")
    if stage=="first_read":
        require(type(unit) is int and 1<=unit<=MAX_UNITS,
                "WF_LEARN_UNIT_OUT_OF_BUDGET")
        return base+f"first/{unit:06d}.json"
    require(unit is None,"WF_LEARN_NON_UNIT_PATH_HAS_UNIT")
    return base+stage+".json"

def identity(*,source_key,source_sha,chapter,chapter_body_sha):
    require(isinstance(source_key,str) and
            source_key.startswith("writerforge/v1/private-reading/") and
            validsha(source_sha) and validsha(chapter_body_sha) and
            type(chapter) is int and 1<=chapter<=MAX_CHAPTERS,
            "WF_LEARN_SOURCE_IDENTITY_NOT_VERIFIED")
    return {
        "source_key_sha256":hexdigest(source_key.encode("utf-8")),
        "source_sha256":source_sha,
        "chapter":chapter,
        "chapter_body_sha256":chapter_body_sha,
    }

def reaction_schema(value):
    if not isinstance(value,dict) or set(value)!={
        "attention","curiosity","confusion","tension",
        "urge_to_continue","question","prediction","what_changed",
    }:
        return False
    return (all(type(value[k]) is int and 0<=value[k]<=5
                for k in ("attention","curiosity","confusion",
                          "tension","urge_to_continue"))
            and all(isinstance(value[k],str) and len(value[k])<=160
                    and not any(ord(c)<32 and c not in "\t\n\r"
                                for c in value[k])
                    for k in ("question","prediction","what_changed")))

def mechanism_schema(x):
    return (isinstance(x,dict) and set(x)=={
        "unit","evidence_unit_sha256","mechanism",
        "reader_effect","uncertainty",
        }
        and type(x["unit"]) is int and 1<=x["unit"]<=MAX_UNITS
        and validsha(x["evidence_unit_sha256"])
        and all(isinstance(x[k],str) and len(x[k])<=160
                for k in ("mechanism","reader_effect","uncertainty")))

def validation(doc):
    require(isinstance(doc,dict) and
            doc.get("format")==FORMAT and
            doc.get("stage") in STAGES and
            validsha(doc.get("source_key_sha256")) and
            validsha(doc.get("source_sha256")) and
            validsha(doc.get("chapter_body_sha256")) and
            type(doc.get("chapter")) is int and
            1<=doc["chapter"]<=MAX_CHAPTERS and
            doc.get("model_id")==MODEL and
            doc.get("literary_mastery_verified") is False,
            "WF_LEARN_EVENT_ENVELOPE_INVALID")
    common={
        "format","stage","source_key_sha256","source_sha256",
        "chapter","chapter_body_sha256","model_id",
        "literary_mastery_verified",
    }
    stage=doc["stage"]
    if stage=="first_read":
        expected=common|{
            "unit","source_unit_sha256","previous_event_sha256",
            "future_source_seen","reaction",
        }
        require(set(doc)==expected and
                type(doc["unit"]) is int and 1<=doc["unit"]<=MAX_UNITS and
                validsha(doc["source_unit_sha256"]) and
                (doc["previous_event_sha256"] is None if doc["unit"]==1
                 else validsha(doc["previous_event_sha256"])) and
                doc["future_source_seen"] is False and
                reaction_schema(doc["reaction"]),
                "WF_LEARN_FIRST_READ_SCHEMA_INVALID")
    elif stage=="seal":
        expected=common|{
            "units_read","last_first_read_sha256","future_source_seen",
        }
        require(set(doc)==expected and
                type(doc["units_read"]) is int and
                1<=doc["units_read"]<=MAX_UNITS and
                validsha(doc["last_first_read_sha256"]) and
                doc["future_source_seen"] is False,
                "WF_LEARN_SEAL_SCHEMA_INVALID")
    elif stage=="analysis":
        expected=common|{
            "first_read_seal_sha256","mechanisms","independent_reviewed",
        }
        require(set(doc)==expected and
                validsha(doc["first_read_seal_sha256"]) and
                doc["independent_reviewed"] is False and
                isinstance(doc["mechanisms"],list) and
                1<=len(doc["mechanisms"])<=6 and
                all(mechanism_schema(x) for x in doc["mechanisms"]),
                "WF_LEARN_ANALYSIS_SCHEMA_INVALID")
    encoded=canonical(doc)
    require(100<=len(encoded)<=MAX_EVENT_BYTES,
            "WF_LEARN_EVENT_BYTE_BUDGET")
    return encoded

def event_doc(*,stage,ident,**fields):
    doc={
        "format":FORMAT,"stage":stage,"model_id":MODEL,
        "literary_mastery_verified":False,
        **ident,**fields,
    }
    validation(doc)
    return doc

class WFLearnJournal:
    """Append-only R2 journal. Client sees current locked R2 state."""

    def __init__(self,*,endpoint,reader_token=None,writer_token=None,
                 index_writer_token=None,timeout=60,transport=None):
        self.reader=WFWorkerR2Client(
            endpoint=endpoint,token=reader_token,timeout=timeout)
        self.writer=(writer_token if writer_token is not None else
                     os.environ.get("WF_LEARN_UPLOAD_TOKEN"))
        index=(index_writer_token if index_writer_token is not None else
               os.environ.get("WF_INDEX_UPLOAD_TOKEN"))
        if self.writer is not None:
            require(isinstance(self.writer,str) and
                    24<=len(self.writer)<=1024 and
                    "\r" not in self.writer and "\n" not in self.writer and
                    self.writer!=self.reader.token and self.writer!=index,
                    "WF_LEARN_WRITER_TOKEN_NOT_SEPARATE")
        self._transport=transport or self.reader._opener.open

    def _http(self,method,key,payload=None):
        require(key.startswith(PREFIX) and
                method in ("GET","PUT"),
                "WF_LEARN_HTTP_SCOPE_OR_METHOD_INVALID")
        require(method=="GET" or bool(self.writer),
                "WF_LEARN_WRITER_KEY_NOT_CONFIGURED")
        url=self.reader.endpoint+"/r2/learn/event?"+urlencode({"key":key})
        req=Request(url,method=method,data=payload,
           headers={
              "Authorization":"Bearer "+(
                 self.reader.token if method=="GET" else self.writer),
              "Content-Type":"application/json",
              "Accept":"application/json",
              "User-Agent":"WF-LEARN-Immutable-R2-V75/1",
           })
        try:
            with self._transport(req,timeout=self.reader.timeout) as response:
                require(response.status==200,
                        "WF_LEARN_HTTP_UNEXPECTED_STATUS")
                raw=response.read(MAX_EVENT_BYTES+1)
                require(len(raw)<=MAX_EVENT_BYTES,
                        "WF_LEARN_HTTP_RESPONSE_EXCEEDED")
                return raw,{str(k).lower():v for k,v in response.headers.items()}
        except HTTPError as err:
            code={
              400:"WF_LEARN_REMOTE_SCHEMA_REJECTED",
              401:"WF_LEARN_REMOTE_AUTH_DENIED",
              403:"WF_LEARN_REMOTE_SCOPE_DENIED",
              404:"WF_LEARN_REMOTE_EVENT_MISSING",
              409:"WF_LEARN_REMOTE_LOCK_OR_ORDER_CONFLICT",
              413:"WF_LEARN_REMOTE_EVENT_TOO_LARGE",
              502:"WF_LEARN_REMOTE_STORAGE_FAILED",
              503:"WF_LEARN_REMOTE_WRITER_SECRET_UNCONFIGURED",
            }.get(err.code,"WF_LEARN_REMOTE_HTTP_ERROR")
            raise WFLearnJournalError(code) from None
        except (URLError,TimeoutError,OSError):
            raise WFLearnJournalError("WF_LEARN_REMOTE_TRANSPORT_FAILED") from None

    def _store(self,doc):
        raw=validation(doc)
        key=path_for(
            source_key_sha=doc["source_key_sha256"],
            source_sha=doc["source_sha256"],
            chapter=doc["chapter"],stage=doc["stage"],
            unit=doc.get("unit"),
        )
        response,_=self._http("PUT",key,raw)
        try:
            reply=json.loads(response)
        except (ValueError,UnicodeError):
            raise WFLearnJournalError("WF_LEARN_WRITE_REPLY_INVALID") from None
        expected=hexdigest(raw)
        require(isinstance(reply,dict) and
                reply.get("ok") is True and
                reply.get("sha256")==expected and
                reply.get("immutable") is True and
                type(reply.get("created")) is bool,
                "WF_LEARN_R2_IMMUTABLE_RECEIPT_INVALID")
        self.read(doc,expect_sha=expected)
        return {
            "event_sha256":expected,
            "stage":doc["stage"],
            "unit":doc.get("unit"),
            "created":reply["created"],
            "r2_reader_readback_verified":True,
            "literary_quality_graduated":False,
        }

    def read(self,doc,expect_sha=None):
        rawdoc=validation(doc)
        key=path_for(
            source_key_sha=doc["source_key_sha256"],
            source_sha=doc["source_sha256"],
            chapter=doc["chapter"],stage=doc["stage"],
            unit=doc.get("unit"),
        )
        raw,headers=self._http("GET",key)
        h=hexdigest(raw)
        require((expect_sha is None or h==expect_sha) and
                headers.get("x-wf-learn-sha256")==h,
                "WF_LEARN_R2_EVENT_SHA_FAILED")
        try:out=json.loads(raw)
        except (ValueError,UnicodeError):
            raise WFLearnJournalError("WF_LEARN_RESTORED_JSON_INVALID") from None
        validation(out)
        require(out==doc,"WF_LEARN_RESTORED_EVENT_DIFFERS")
        return out

    def append_first_read(self,*,ident,unit,source_unit_sha,
                          previous_record_sha,reaction):
        doc=event_doc(
            stage="first_read",ident=ident,unit=unit,
            source_unit_sha256=source_unit_sha,
            previous_event_sha256=previous_record_sha,
            future_source_seen=False,reaction=reaction,
        )
        return self._store(doc)

    def seal_first_read(self,*,ident,units,last_record_sha):
        doc=event_doc(
            stage="seal",ident=ident,units_read=units,
            last_first_read_sha256=last_record_sha,
            future_source_seen=False,
        )
        return self._store(doc)

    def append_analysis(self,*,ident,first_read_seal_sha,
                        mechanisms):
        doc=event_doc(
            stage="analysis",ident=ident,
            first_read_seal_sha256=first_read_seal_sha,
            mechanisms=mechanisms,
            independent_reviewed=False,
        )
        return self._store(doc)
