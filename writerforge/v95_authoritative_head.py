"""V95 strict optimistic authoritative-head protocol -- NOT YET DEPLOYED.

The old Cloudflare Worker only has immutable /r2/index/write CAS objects.
Without the NEW server-enforced /r2/learn/head conditional update route,
NO production/synthetic mutable head can be claimed. A client-side GET/PUT
sequence is NOT a lock and is always rejected.

This first iteration permits one separate SYNTHETIC_TEST_ONLY head, not
real facts or literary WRITE. Cross-process writer fencing is delegated to
the new server's R2 If-Match/If-None-Match conditional PUT (must be deployed
and verified before any real use). No model calls, no secrets in receipts.
"""
from __future__ import annotations

from hashlib import sha256
from urllib.parse import urlencode
from urllib.request import Request
from urllib.error import HTTPError, URLError
import json
import os
import re

from .r2_worker_http import WFWorkerR2Client

FORMAT="writerforge.authoritative-learn-head.v95"
VERSION=1
PROJECT="v95_synthetic_only"
KIND="SYNTHETIC_TEST_ONLY"
SHA=re.compile(r"[a-f0-9]{64}\Z")
WRITER=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,63}\Z")
FIELDS=frozenset((
    "format","schema_version","project_id","kind","generation",
    "previous_head_sha256","commit_manifest_sha256","writer_id",
    "original_prose_stored","real_fact_authority_granted",
    "writer_literary_truth_verified","skills_promotion_allowed",
    "head_sha256",
))
MAX_BYTES=2048


class HeadCommitError(ValueError):
    pass


def need(ok,code):
    if not ok: raise HeadCommitError(code)


def canonical(doc):
    return json.dumps(doc,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")


def digest(raw):
    return sha256(raw).hexdigest()


def is_sha(value):
    return isinstance(value,str) and SHA.fullmatch(value) is not None


def parse_strict(raw):
    need(type(raw) is bytes and 0<len(raw)<=MAX_BYTES,
         "WF95_HEAD_BOUNDED_RAW_JSON_REQUIRED")
    try:
        s=raw.decode("utf8","strict")
        need("\ufffd" not in s,"WF95_HEAD_ENCODING_REPLACEMENT")
        def pairs(values):
            out={}
            for k,v in values:
                if k in out:
                    raise ValueError("duplicate field")
                out[k]=v
            return out
        value=json.loads(s,object_pairs_hook=pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(
                             ValueError("nonfinite")))
        canonical(value)
    except (ValueError,UnicodeError,OverflowError,TypeError):
        raise HeadCommitError("WF95_HEAD_JSON_GARBLED") from None
    need(type(value) is dict,"WF95_HEAD_NOT_OBJECT")
    return value


def make_head(*,generation,previous_head_sha256,
              commit_manifest_sha256,writer_id,
              project_id=PROJECT):
    need(project_id==PROJECT and
         type(generation) is int and 1<=generation<=10000000 and
         ((generation==1 and previous_head_sha256 is None) or
          (generation>1 and is_sha(previous_head_sha256))) and
         is_sha(commit_manifest_sha256) and
         isinstance(writer_id,str) and WRITER.fullmatch(writer_id) is not None,
         "WF95_AUTHORITATIVE_HEAD_INPUT_INVALID")
    data={
        "format":FORMAT,"schema_version":VERSION,
        "project_id":PROJECT,"kind":KIND,
        "generation":generation,
        "previous_head_sha256":previous_head_sha256,
        "commit_manifest_sha256":commit_manifest_sha256,
        "writer_id":writer_id,
        "original_prose_stored":False,
        "real_fact_authority_granted":False,
        "writer_literary_truth_verified":False,
        "skills_promotion_allowed":False,
    }
    data["head_sha256"]=digest(canonical(data))
    return data


def verify_head(doc):
    need(type(doc) is dict and set(doc)==FIELDS,
         "WF95_HEAD_SCHEMA_UNKNOWN_OR_FIELDS_MISSING")
    expected=make_head(
        generation=doc.get("generation"),
        previous_head_sha256=doc.get("previous_head_sha256"),
        commit_manifest_sha256=doc.get("commit_manifest_sha256"),
        writer_id=doc.get("writer_id"),
        project_id=doc.get("project_id"))
    need(doc==expected,"WF95_HEAD_HASH_OR_AUTHORITY_TAMPERED")
    return doc


def verify_capabilities(reply):
    need(type(reply) is dict and set(reply)=={
        "ok","protocol","atomic_r2_conditional_put",
        "real_production_facts_allowed","synthetic_only",
    } and
    reply["ok"] is True and
    reply["protocol"]=="wf95-authoritative-head" and
    reply["atomic_r2_conditional_put"] is True and
    reply["real_production_facts_allowed"] is False and
    reply["synthetic_only"] is True,
    "WF95_ATOMIC_HEAD_CAPABILITY_NOT_DEPLOYED")
    return True


class WorkerHeadTransport:
    """Live HTTP adapter to the conditional-head Worker, fails closed.

    GET capability discovery first. A stale version/connection failure
    must NOT be retried automatically: a prior write may still complete.
    The endpoint must keep the old Reader and separate index Writer keys.
    """
    def __init__(self,*,endpoint,read_token=None,write_token=None,timeout=30):
        reader=WFWorkerR2Client(
            endpoint=endpoint,token=read_token,timeout=timeout)
        secret=(write_token if write_token is not None else
                os.environ.get("WF_INDEX_UPLOAD_TOKEN"))
        need(isinstance(secret,str) and len(secret)>=24 and
             secret!=reader.token and "\r" not in secret and
             "\n" not in secret,
             "WF95_SEPARATE_INDEX_WRITER_REQUIRED")
        self.reader=reader
        self.writer_secret=secret
        self._opener=reader._opener

    def _request(self,method,path,*,body=None,etag=None):
        need(method in ("GET","PUT") and
             path in ("/r2/learn/head/capabilities",
                      "/r2/learn/head"),
             "WF95_HEAD_ROUTE_METHOD_NOT_ALLOWED")
        url=self.reader.endpoint+path
        if path=="/r2/learn/head":
            url+="?"+urlencode({"project":PROJECT})
        writer=method=="PUT"
        headers={
            "Authorization":"Bearer "+(
                self.writer_secret if writer else self.reader.token),
            "Accept":"application/json",
            "User-Agent":"WriterForge-V95-Head/1.0",
        }
        if writer:
            need(body is not None and etag is not False,
                 "WF95_NO_UNCONDITIONAL_HEAD_WRITES")
            headers["Content-Type"]="application/json"
            if etag is None:
                headers["If-None-Match"]="*"
            else:
                need(isinstance(etag,str) and
                     3<=len(etag)<=160 and
                     etag.startswith('"') and etag.endswith('"'),
                     "WF95_INVALID_PARENT_ETAG")
                headers["If-Match"]=etag
        request=Request(url,method=method,data=body,headers=headers)
        try:
            with self._opener.open(request,timeout=self.reader.timeout) as rsp:
                need(rsp.status==200,"WF95_HEAD_WORKER_STATUS_INVALID")
                result=rsp.read(MAX_BYTES+1)
                need(len(result)<=MAX_BYTES,
                     "WF95_HEAD_HTTP_RESPONSE_UNBOUNDED")
                return rsp.headers,result
        except HTTPError as exc:
            reason={
                401:"WF95_HEAD_UNAUTHORIZED",
                403:"WF95_HEAD_FORBIDDEN",
                404:"WF95_HEAD_ROUTE_OR_HEAD_NOT_PRESENT",
                409:"WF95_ATOMIC_CONFLICT_STALE_HEAD",
                412:"WF95_ATOMIC_CONFLICT_STALE_HEAD",
                422:"WF95_HEAD_METADATA_INVALID",
                503:"WF95_HEAD_WRITER_NOT_CONFIGURED",
            }.get(exc.code,"WF95_HEAD_REMOTE_ERROR")
            raise HeadCommitError(reason) from None
        except (OSError,URLError,TimeoutError):
            raise HeadCommitError(
                "WF95_HEAD_UNKNOWN_NETWORK_OUTCOME_NO_AUTOMATIC_RETRY") from None

    def capability(self):
        _,body=self._request("GET","/r2/learn/head/capabilities")
        return verify_capabilities(parse_strict(body))

    def read(self):
        headers,raw=self._request("GET","/r2/learn/head")
        etag=headers.get("ETag")
        need(isinstance(etag,str) and
             3<=len(etag)<=160 and etag[0]=='"' and etag[-1]=='"',
             "WF95_HEAD_GET_MISSING_ETAG")
        doc=verify_head(parse_strict(raw))
        return etag,doc

    def atomic_update(self,head,etag):
        verify_head(head)
        headers,raw=self._request(
            "PUT","/r2/learn/head",body=canonical(head),etag=etag)
        result=parse_strict(raw)
        need(result.get("ok") is True and
             result.get("generation")==head["generation"] and
             result.get("head_sha256")==head["head_sha256"] and
             result.get("atomic_conditional_commit") is True and
             result.get("synthetic_only") is True,
             "WF95_HEAD_WORKER_DID_NOT_ATTEST_CONDITIONAL_COMMIT")
        return result


def commit_synthetic_head(transport, *,new_manifest_sha256,writer_id,
                          prior_etag=None,prior_head=None):
    """Require server capability + expected parent; never last-writer-wins.

    For the initial head, a trusted operator must explicitly call with
    prior_head=None,etag=None. For later heads, the caller MUST supply the
    previously read ETag and exact parent document.
    """
    need(transport.capability() is True,
         "WF95_HEAD_ROUTE_NOT_ACTIVE")
    if prior_head is None:
        need(prior_etag is None,"WF95_INITIAL_HEAD_WITH_STALE_ETAG")
        head=make_head(
            generation=1,previous_head_sha256=None,
            commit_manifest_sha256=new_manifest_sha256,writer_id=writer_id)
    else:
        verify_head(prior_head)
        need(isinstance(prior_etag,str) and
             prior_etag.startswith('"') and prior_etag.endswith('"'),
             "WF95_EXPECTED_PREVIOUS_ETAG_MISSING")
        head=make_head(
            generation=prior_head["generation"]+1,
            previous_head_sha256=prior_head["head_sha256"],
            commit_manifest_sha256=new_manifest_sha256,writer_id=writer_id)
    # The Worker is responsible for atomic etag comparison and checking
    # that this commit's manifest CAS exists. The client CANNOT emulate it.
    result=transport.atomic_update(head,prior_etag)
    # Read-after-write on the server. A later concurrent winner may have
    # advanced the head: never misreport current authority.
    observed_etag,observed=transport.read()
    need(observed["head_sha256"]==head["head_sha256"] and
         observed["generation"]==head["generation"],
         "WF95_HEAD_CHANGED_AFTER_COMMIT_REQUIRES_RECONCILIATION")
    return {
        "status":"WF95_SYNTHETIC_HEAD_CONDITIONALLY_COMMITTED",
        "head_sha256":head["head_sha256"],
        "generation":head["generation"],
        "observed_etag":observed_etag,
        "previous_head_sha256":head["previous_head_sha256"],
        "real_facts_admitted":False,
        "real_production_route_enabled":False,
        "model_calls":0,"r2_immutable_experiences_modified":False,
    }


def require_head_supported(client):
    """Used by future LEARN intake before R2 writes; never assume route."""
    need(client.capability() is True,
         "WF95_HEAD_CAPABILITY_UNAVAILABLE_FAIL_CLOSED")
    return True
