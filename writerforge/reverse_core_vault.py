"""Private content-addressed R2 vault for *abstract* V28 learning core receipts.

Separate from the original-source vault. Never uploads the training draft,
original novel, WriterForgeDB or local model payload. Zero credentials in logs.
"""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
import json
import re

from .r2_storage import R2Config, R2StudyVault, R2StorageError, _read_body

MAX_SNAPSHOT_BYTES = 512 * 1024
SHA = re.compile(r"[a-f0-9]{64}\Z")
ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\Z")


class ReverseCoreVault:
    def __init__(self, config: R2Config, *, client=None):
        if config.bucket != "writerforge-private-library":
            raise R2StorageError("reverse learning requires the private bucket")
        self.config=config
        self.client=client if client is not None else R2StudyVault(config).client

    def _base(self, work, project, edition):
        if not (ID.fullmatch(work) and ID.fullmatch(project) and SHA.fullmatch(edition)):
            raise R2StorageError("invalid reverse-learning R2 key")
        return f"{self.config.prefix}/reverse-craft/{work}/{project}/{edition}"

    def _read(self, key):
        response=self.client.get_object(Bucket=self.config.bucket,Key=key)
        return _read_body(response, MAX_SNAPSHOT_BYTES)

    def store_and_restore(self, payload: bytes, *, work: str,
                          project: str, edition: str) -> str:
        if not isinstance(payload, bytes) or not 50 <= len(payload) <= MAX_SNAPSHOT_BYTES:
            raise R2StorageError("invalid or oversized abstract core snapshot")
        try:
            decoded=json.loads(payload)
        except (UnicodeError,ValueError) as exc:
            raise R2StorageError("snapshot must be valid UTF8 JSON") from exc
        if (decoded.get("format")!="writerforge.reverse-core.v1" or
            decoded.get("project")!=project or not isinstance(decoded.get("tables"),dict)):
            raise R2StorageError("reverse-core manifest is not trusted")
        if set(decoded["tables"])!={
            "rc_meta","rc_units","rc_attempts","rc_cores","rc_evidence","rc_merges"
        }:
            raise R2StorageError("invalid snapshot table whitelist")
        if any(not isinstance(value,list) for value in decoded["tables"].values()):
            raise R2StorageError("snapshot tables must contain bounded records")
        if not decoded["tables"]["rc_meta"] or len(decoded["tables"]["rc_meta"])!=1:
            raise R2StorageError("snapshot has no pinned provenance")
        meta=decoded["tables"]["rc_meta"][0]
        if (meta.get("project"),meta.get("work"),meta.get("edition"))!=(project,work,edition):
            raise R2StorageError("source edition not in permitted namespace")
        encoded=json.dumps(decoded,sort_keys=True,ensure_ascii=False,
                           separators=(",",":"),allow_nan=False).encode("utf-8")
        if encoded!=payload:
            raise R2StorageError("snapshot not canonical")
        root=self._base(work,project,edition)
        digest=sha256(payload).hexdigest()
        key=f"{root}/snapshots/{digest}.json"
        try:
            info=self.client.head_object(Bucket=self.config.bucket,Key=key)
        except Exception as exc:
            if str(getattr(exc,"response",{}).get("Error",{}).get("Code","")) not in (
                "404","NoSuchKey","NotFound"
            ):
                raise
            info=None
        if info is None:
            self.client.put_object(
                Bucket=self.config.bucket,Key=key,Body=payload,
                ContentType="application/json",Metadata={"sha256":digest})
        elif int(info.get("ContentLength",-1))!=len(payload) or info.get("Metadata",{}).get("sha256")!=digest:
            raise R2StorageError("immutable reverse-core snapshot collision")
        # A *new GET* validates both payload bytes and full SHA, not only HEAD metadata.
        fresh=self._read(key)
        if fresh!=payload or sha256(fresh).hexdigest()!=digest:
            raise R2StorageError("fresh private R2 roundtrip mismatch")
        # A content-addressed receipt makes crash restart idempotent: callers
        # keep the SHA in their durable SQLite transaction, not a mutable
        # latest pointer that could race another writer.
        return digest

    def restore_verified(self, *, work:str, project:str, edition:str,
                         snapshot_sha:str) -> bytes:
        if not isinstance(snapshot_sha,str) or not SHA.fullmatch(snapshot_sha):
            raise R2StorageError("invalid requested core snapshot")
        root=self._base(work,project,edition)
        data=self._read(f"{root}/snapshots/{snapshot_sha}.json")
        if sha256(data).hexdigest()!=snapshot_sha:
            raise R2StorageError("core snapshot on R2 failed hash validation")
        # Repeat the edition/schema checks, including canonical JSON.
        decoded=json.loads(data)
        meta=decoded.get("tables",{}).get("rc_meta",[])
        if (decoded.get("format")!="writerforge.reverse-core.v1"
            or decoded.get("project")!=project or len(meta)!=1
            or (meta[0].get("project"),meta[0].get("work"),meta[0].get("edition"))!=(project,work,edition)):
            raise R2StorageError("restored core has incorrect source identity")
        return data
