"""V79 supervised, provisional R2 CAS-backed WF LEARN evidence journal.

The EXISTING successfully deployed V72 R2 index writer supports immutable
SHA-256-addressed 1 MiB objects under indexes/v1/chunks/. V79 temporarily
uses this content-addressed blob pool to store *small experimental LEARN
JSON records and restore pointers*. It DOES NOT claim the new learn/v1 Worker
endpoint was deployed, nor disguise the blobs as SQL manifests.

Every event and every checkpoint is written by WriterForge's own Railway
process and immediately read back with its independent R2 reader key. The
checkpoint SHA, without private contents, appears in Railway receipt logs,
enabling a fresh process to reconstruct the exact A/SEAL/B chain.

Limitations: the old Worker does not enforce LEARN path-level immutability
or event ordering. This class independently rejects disorder and verifies
remote bytes but is an *EXPERIMENTAL* single-writer protocol, not a substitute
for the future native LEARN journal. No source text is stored in the events.
No operations on original books or existing SQL manifests.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
import re

from .r2_index_vault import R2IndexVault,chunk_key,R2IndexError
from .r2_learn_journal import (
    WFLearnJournal,WFLearnJournalError,validation,path_for,
    hexdigest,canonical,
)

FORMAT="wf.learn.provisional.cas-checkpoint.v79"
CHECKPOINT_MAX=256*1024
EVENT_MAX=8192
MAX_FROZEN_EVENTS=320
SHA=re.compile(r"^[0-9a-f]{64}$")

def need(ok,code):
    if not ok:raise WFLearnJournalError(code)


class WFProvisionalR2CASJournal(WFLearnJournal):
    """A WFLearnJournal-compatible provisional R2 evidence backend."""

    def __init__(self,*,endpoint,read_only=False,
                 checkpoint_sha=None,progress=None,
                 reader_token=None,writer_token=None):
        super().__init__(
            endpoint=endpoint,reader_token=reader_token,
            writer_token=writer_token,
            index_writer_token=(writer_token if writer_token is not None
                                else os.environ.get("WF_INDEX_UPLOAD_TOKEN")),
            read_only=read_only,timeout=80)
        self.vault=R2IndexVault(
            endpoint=endpoint,read_token=self.reader.token,
            write_token=None if read_only else self.writer,timeout=80)
        self.progress=progress
        self.allow_prior_pilot_tail=False
        self.event_addresses={}
        self.checkpoint_sha=None
        self.previous_checkpoint_sha=None
        if checkpoint_sha is not None:
            self.restore_pointer(checkpoint_sha)

    def _announce(self,message):
        if self.progress is not None:
            self.progress(message)

    def _get_content(self,sha):
        need(isinstance(sha,str) and SHA.fullmatch(sha),
             "WF_V79_CAS_HASH_INVALID")
        key=chunk_key(sha)
        size,_=self.vault._head(key)
        need(0<size<=CHECKPOINT_MAX,
             "WF_V79_CAS_OBJECT_OVER_BUDGET")
        raw=self.vault._index_bytes(key,size)
        need(hexdigest(raw)==sha,
             "WF_V79_REMOTE_CAS_SHA_MISMATCH")
        return raw

    def _put_content(self,raw):
        need(isinstance(raw,bytes) and 0<len(raw)<=CHECKPOINT_MAX,
             "WF_V79_CAS_OBJECT_TOO_LARGE")
        need(not self.read_only and bool(self.writer),
             "WF_V79_READER_CANNOT_UPLOAD")
        sha=hexdigest(raw)
        created=self.vault._write_immutable(chunk_key(sha),raw)
        returned=self._get_content(sha)
        need(returned==raw,"WF_V79_CAS_REMOTE_ROUNDTRIP_FAILED")
        return sha,created

    def require_writer_ready(self):
        """Use the EXISTING writer API; deliberately invalid SHA -> 422.

        No private text and no R2 object are written by this probe.
        Only HTTP SHA-rejection (not unauthorized 401/route 404) is accepted.
        """
        need(not self.read_only and bool(self.writer),
             "WF_V79_CAS_WRITER_REQUIRED")
        try:
            self.vault._call(
                "/r2/index/write",
                {"key":chunk_key("0"*64)},
                method="PUT",body=b"wf-v79-deliberate-sha-mismatch",
                write=True,cap=8192,
            )
        except R2IndexError as exc:
            need(str(exc)=="WF_INDEX_SHA_REJECTED",
                 "WF_V79_CAS_WRITER_PREFLIGHT_FAILED")
            return True
        raise WFLearnJournalError(
            "WF_V79_WRITER_ACCEPTED_INVALID_SHA_UNSAFE")

    def _verify_ordering(self,doc,key):
        stage=doc["stage"]
        if (stage=="first_read" and self.allow_prior_pilot_tail and
            doc["chapter"]==1 and doc["unit"]>=4):
            # ONLY the old V79 chapter-1 pilot is extendable. Its original
            # 3-unit seal and analysis remain immutable historical evidence.
            # The V80 mixed-history full-chapter certificate must separately
            # disclose that earlier analysis preceded remaining readings.
            firstroot=key.split("/first/")[0]+"/"
            old_seal=self.event_addresses.get(firstroot+"seal.json")
            old_analysis=self.event_addresses.get(firstroot+"analysis.json")
            need(old_seal is not None and old_analysis is not None,
                 "WF_V80_INITIAL_PILOT_EVIDENCE_MISSING")
            original_seal=json.loads(self._get_content(old_seal))
            need(original_seal["units_read"]==3 and
                 original_seal["source_sha256"]==doc["source_sha256"] and
                 original_seal["chapter_body_sha256"]==
                 doc["chapter_body_sha256"],
                 "WF_V80_INITIAL_PILOT_SEAL_WRONG_SOURCE")
            earlier=path_for(source_key_sha=doc["source_key_sha256"],
                 source_sha=doc["source_sha256"],
                 chapter=1,stage="first_read",unit=doc["unit"]-1)
            need(self.event_addresses.get(earlier)==
                 doc["previous_event_sha256"],
                 "WF_V80_PILOT_CONTINUATION_CHAIN_INVALID")
            return

        root=key.rsplit("/",1)[0]+"/"
        if stage=="first_read":
            root=key.split("/first/")[0]+"/"
            need(root+"seal.json" not in self.event_addresses,
                 "WF_V79_PASS_A_ALREADY_SEALED")
            if doc["unit"]==1:
                need(doc["previous_event_sha256"] is None,
                     "WF_V79_FIRST_UNIT_PREDECESSOR_INVALID")
            else:
                previous=path_for(
                    source_key_sha=doc["source_key_sha256"],
                    source_sha=doc["source_sha256"],
                    chapter=doc["chapter"],
                    stage="first_read",unit=doc["unit"]-1)
                need(self.event_addresses.get(previous)==
                     doc["previous_event_sha256"],
                     "WF_V79_PREVIOUS_PASS_A_MISSING")
        elif stage=="seal":
            previous=path_for(
                source_key_sha=doc["source_key_sha256"],
                source_sha=doc["source_sha256"],
                chapter=doc["chapter"],
                stage="first_read",unit=doc["units_read"])
            need(self.event_addresses.get(previous)==
                 doc["last_first_read_sha256"],
                 "WF_V79_SEAL_NOT_LAST_LOCKED_UNIT")
            n=sum(1 for k in self.event_addresses
                  if k.startswith(root+"first/"))
            need(n==doc["units_read"],
                 "WF_V79_PASS_A_UNIT_COUNT_MISMATCH")
        elif stage=="analysis":
            need(self.event_addresses.get(root+"seal.json")==
                 doc["first_read_seal_sha256"],
                 "WF_V79_PASS_A_SEAL_MISSING")
            for item in doc["mechanisms"]:
                position=path_for(
                    source_key_sha=doc["source_key_sha256"],
                    source_sha=doc["source_sha256"],
                    chapter=doc["chapter"],
                    stage="first_read",unit=item["unit"])
                prior=self.event_addresses.get(position)
                need(prior is not None,
                     "WF_V79_ANALYSIS_UNREAD_SOURCE_UNIT")
                first=json.loads(self._get_content(prior))
                need(first["source_unit_sha256"]==
                     item["evidence_unit_sha256"] and
                     first["chapter_body_sha256"]==
                     doc["chapter_body_sha256"],
                     "WF_V79_ANALYSIS_SOURCE_HASH_UNMATCHED")
        else:
            raise WFLearnJournalError("WF_V79_STAGE_NOT_SUPPORTED")

    def _checkpoint(self,stage,event_sha):
        body={
            "format":FORMAT,
            "previous_checkpoint_sha256":self.checkpoint_sha,
            "event_addresses":dict(sorted(self.event_addresses.items())),
            "single_writer":True,
            "literary_mastery_verified":False,
            "native_learn_route_deployed":False,
            "storage_namespace":"indexes/v1/chunks",
        }
        raw=canonical(body)
        sha,_=self._put_content(raw)
        self.previous_checkpoint_sha=self.checkpoint_sha
        self.checkpoint_sha=sha
        self._announce({
            "status":"WF_V79_IMMUTABLE_LEARN_EVENT_CHECKPOINTED_IN_R2",
            "stage":stage,
            "event_sha256":event_sha,
            "checkpoint_sha256":sha,
            "events_stored":len(self.event_addresses),
            "native_learn_journal_deployed":False,
            "novel_text_or_secret_logged":False,
        })
        return sha

    def _http(self,method,key,payload=None):
        """Translate V75 learn-event GET/PUT into V72 immutable CAS I/O.

        R2 Writer endpoints authenticate the old index-only secret.
        This is an explicitly named *provisional* journal, not a claim
        of native Cloudflare LEARN path authorization.
        """
        need(method in ("PUT","GET") and
             key.startswith("writerforge/v1/learn/v1/"),
             "WF_V79_CAS_LEARN_KEY_OR_METHOD_REJECTED")
        if method=="GET":
            sha=self.event_addresses.get(key)
            if sha is None:
                raise WFLearnJournalError("WF_LEARN_REMOTE_EVENT_MISSING")
            body=self._get_content(sha)
            return body,{"x-wf-learn-sha256":sha}
        need(not self.read_only,"WF_V79_CAS_WRITER_DISABLED")
        need(isinstance(payload,bytes) and
             100<=len(payload)<=EVENT_MAX,
             "WF_V79_CAS_EVENT_TOO_LARGE")
        try:
            doc=json.loads(payload.decode("utf-8"))
            validation(doc)
        except (ValueError,UnicodeError):
            raise WFLearnJournalError(
                "WF_V79_CAS_JSON_EVENT_MALFORMED") from None
        expected=path_for(
            source_key_sha=doc["source_key_sha256"],
            source_sha=doc["source_sha256"],
            chapter=doc["chapter"],stage=doc["stage"],unit=doc.get("unit"))
        need(key==expected,
             "WF_V79_CAS_KEY_AND_EVENT_POSITION_DIFFER")
        sha=hexdigest(payload)
        existing=self.event_addresses.get(key)
        if existing is not None:
            need(existing==sha,
                 "WF_V79_CAS_EVENT_ALREADY_IMMUTABLE")
            return canonical({
                "ok":True,"sha256":sha,"created":False,"immutable":True,
            }),{}
        self._verify_ordering(doc,key)
        remote_sha,created=self._put_content(payload)
        need(remote_sha==sha,"WF_V79_CAS_EVENT_SHA_DISAGREED")
        self.event_addresses[key]=sha
        self._checkpoint(doc["stage"],sha)
        return canonical({
            "ok":True,"sha256":sha,"created":created,"immutable":True,
        }),{}

    def restore_pointer(self,checkpoint_sha):
        """Cold restore via the SHA pointer from previous Railway receipts."""
        raw=self._get_content(checkpoint_sha)
        try:
            doc=json.loads(raw.decode("utf8"))
        except (UnicodeError,ValueError):
            raise WFLearnJournalError(
                "WF_V79_CHECKPOINT_NOT_JSON") from None
        need(isinstance(doc,dict) and doc.get("format")==FORMAT and
             doc.get("native_learn_route_deployed") is False and
             doc.get("literary_mastery_verified") is False and
             doc.get("storage_namespace")=="indexes/v1/chunks",
             "WF_V79_CHECKPOINT_SCHEMA_INVALID")
        events=doc.get("event_addresses")
        need(isinstance(events,dict) and 1<=len(events)<=MAX_FROZEN_EVENTS and
             all(isinstance(k,str) and
                 k.startswith("writerforge/v1/learn/v1/") and
                 isinstance(v,str) and SHA.fullmatch(v)
                 for k,v in events.items()),
             "WF_V79_CHECKPOINT_REFERENCES_INVALID")
        # Validate every referenced event bytehash and full event schema.
        for key,sha in events.items():
            event_bytes=self._get_content(sha)
            try:ev=json.loads(event_bytes)
            except (ValueError,UnicodeError):
                raise WFLearnJournalError(
                    "WF_V79_CHECKPOINT_EVENT_JSON_INVALID") from None
            validation(ev)
            expected=path_for(
                source_key_sha=ev["source_key_sha256"],
                source_sha=ev["source_sha256"],
                chapter=ev["chapter"],stage=ev["stage"],
                unit=ev.get("unit"))
            need(key==expected,
                 "WF_V79_CHECKPOINT_EVENT_WRONG_SOURCE_OR_POSITION")
        self.event_addresses=dict(events)
        self.checkpoint_sha=checkpoint_sha
        self.previous_checkpoint_sha=doc.get("previous_checkpoint_sha256")
        return {
            "restored_events":len(events),
            "checkpoint_sha256":checkpoint_sha,
            "remote_sha_verified_for_all_records":True,
            "literary_mastery_verified":False,
            "native_learn_route_deployed":False,
        }
