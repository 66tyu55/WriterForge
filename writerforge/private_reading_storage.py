"""Cloudflare R2 immutable vault for raw private_reading_v1 archives.

Raw reading is NOT literary comprehension, training, or a published Xuehai
snapshot. Reuses the existing S3 client, content-hash streaming uploader and
bounded manifest utilities without weakening R2StudyVault validation.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re
import sqlite3

from .r2_storage import (
    R2StudyVault, R2StorageError, _canonical, _digest, _read_body,
    MAX_DB_BYTES, MAX_MANIFEST_BYTES, MAX_LATEST_BYTES,
)

FORMAT = "writerforge.private_reading.v1"
ARCHIVE = "private_reading_v1"
EXPECTED_WORKS = 13
REQUIRED_TABLES = {"corpus_meta", "works", "sections"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def audit_private_reading(path: str | Path) -> dict:
    path=Path(path)
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_DB_BYTES:
        raise R2StorageError("missing, empty, or oversized private reading archive")
    try:
        with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as db:
            if db.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise R2StorageError("private reading SQLite quick_check failed")
            names={r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if not REQUIRED_TABLES.issubset(names):
                raise R2StorageError("private reading schema lacks required tables")
            meta=dict(db.execute("SELECT key,value FROM corpus_meta"))
            if meta.get("schema") != "private_reading_v1":
                raise R2StorageError("wrong private reading schema")
            rows=db.execute(
                """SELECT id,title,file_name,source_sha256,original_encoding,
                          original_bytes,original_chars,archived_chars,
                          section_count,status FROM works ORDER BY id"""
            ).fetchall()
            if len(rows)!=EXPECTED_WORKS:
                raise R2StorageError("expected exactly 13 individually archived works")
            total=0
            manifest_works=[]
            for (id_,title,name,digest,encoding,size,chars,archived,count,status) in rows:
                if (not isinstance(digest,str) or not HEX64.fullmatch(digest)
                    or encoding not in ("utf-8","utf-8-sig","gb18030","gbk")
                    or not isinstance(size,int) or size<=0
                    or not isinstance(chars,int) or chars<=0
                    or chars!=archived or not isinstance(count,int) or count<=0):
                    raise R2StorageError("invalid private reading source metadata")
                # Stream sections; keep only running hashes and counters in memory.
                current=0
                seen=0
                for ordinal,content,section_sha,char_count in db.execute(
                    """SELECT ordinal,content,content_sha256,char_count
                       FROM sections WHERE work_id=? ORDER BY ordinal""",(id_,)):
                    seen+=1
                    if ordinal!=seen or not isinstance(content,str):
                        raise R2StorageError("missing/out-of-order reading section")
                    if char_count!=len(content) or sha256(content.encode("utf-8")).hexdigest()!=section_sha:
                        raise R2StorageError("reading section content hash mismatch")
                    current+=char_count
                if seen!=count or current!=chars:
                    raise R2StorageError("incomplete reading section inventory")
                total+=seen
                manifest_works.append({"title":title,"file_name":name,
                    "source_sha256":digest,"original_encoding":encoding,
                    "original_bytes":size,"sections":count,"characters":chars})
            if db.execute("SELECT COUNT(*) FROM sections").fetchone()[0]!=total:
                raise R2StorageError("orphaned reading sections")
            if db.execute("SELECT COUNT(*) FROM sections s LEFT JOIN works w ON w.id=s.work_id WHERE w.id IS NULL").fetchone()[0]:
                raise R2StorageError("orphaned private reading work")
            return {"schema":"private_reading_v1","status":"archived_unreviewed",
                    "works":len(rows),"sections":total,"source_manifest":manifest_works,
                    "semantic_verified":False,"literary_training_performed":False}
    except sqlite3.Error as exc:
        raise R2StorageError("invalid private reading SQLite schema or content") from exc


class PrivateReadingVault(R2StudyVault):
    """A separate prefix, independent of the studied-works R2 namespace."""

    def _root(self, library: str) -> str:
        if library != ARCHIVE:
            raise R2StorageError("private reading library must be private_reading_v1")
        return f"{self.config.prefix}/private-reading/{ARCHIVE}"

    def backup(self, *, database: str | Path, library: str = ARCHIVE) -> dict:
        if library!=ARCHIVE:
            raise R2StorageError("wrong private reading library")
        source=Path(database)
        # Validate source before creating any remote objects.
        audit_private_reading(source)
        if source.stat().st_size>MAX_DB_BYTES:
            raise R2StorageError("reading database exceeds size bound")
        with TemporaryDirectory(prefix="writerforge-private-reading-") as tmp:
            snap=Path(tmp)/"reading.sqlite3"
            try:
                with closing(sqlite3.connect(source, timeout=20)) as src:
                    with closing(sqlite3.connect(snap, timeout=20)) as dst:
                        src.backup(dst,pages=256,sleep=0.02)
            except sqlite3.Error as exc:
                raise R2StorageError("consistent online reading snapshot failed") from exc
            stats=audit_private_reading(snap)
            digest,size=_digest(snap)
            # Stable manifest allows repeated uploads to reuse the same blob.
            manifest={"format":FORMAT,"library":ARCHIVE,"status":"archived_unreviewed",
                      "files":{"reading.sqlite3":{"sha256":digest,"size":size}},
                      "stats":stats}
            data=_canonical(manifest)
            if len(data)>MAX_MANIFEST_BYTES:
                raise R2StorageError("reading manifest exceeds safe bound")
            version=sha256(data).hexdigest()
            uploaded=self._upload_blob(ARCHIVE,snap,digest,size)
            self._put_small_immutable(self._manifest_key(ARCHIVE,version),data,version)
            pointer=_canonical({"format":FORMAT,"library":ARCHIVE,
                "snapshot":version,"manifest_sha256":version})
            latest=self._latest_key(ARCHIVE)
            existing=self._head(latest)
            if existing is None or self._get_small(latest,MAX_LATEST_BYTES)!=pointer:
                self.client.put_object(Bucket=self.config.bucket,Key=latest,
                    Body=pointer,ContentType="application/json")
            if self._get_small(latest,MAX_LATEST_BYTES)!=pointer:
                raise R2StorageError("private reading latest pointer read-back failed")
            return {"uri":f"r2://{self.config.bucket}/{self._manifest_key(ARCHIVE,version)}",
                    "snapshot":version,"status":"archived_unreviewed",
                    "uploaded":bool(uploaded),"verified_remote_metadata":True,
                    "stats":stats}

    def restore(self, *, destination: str | Path, library: str = ARCHIVE,
                snapshot: str | None = None) -> dict:
        if library!=ARCHIVE:
            raise R2StorageError("wrong private reading library")
        if snapshot is None:
            pointer=json.loads(self._get_small(self._latest_key(ARCHIVE),MAX_LATEST_BYTES))
            if (pointer.get("format")!=FORMAT or pointer.get("library")!=ARCHIVE
                or pointer.get("snapshot")!=pointer.get("manifest_sha256")):
                raise R2StorageError("bad private reading latest pointer")
            snapshot=pointer["snapshot"]
        if not isinstance(snapshot,str) or not HEX64.fullmatch(snapshot):
            raise R2StorageError("invalid private reading snapshot id")
        encoded=self._get_small(self._manifest_key(ARCHIVE,snapshot),MAX_MANIFEST_BYTES)
        if sha256(encoded).hexdigest()!=snapshot:
            raise R2StorageError("reading manifest SHA256 mismatch")
        manifest=json.loads(encoded)
        if (manifest.get("format")!=FORMAT or manifest.get("library")!=ARCHIVE
            or manifest.get("status")!="archived_unreviewed"
            or set(manifest.get("files",{}))!={"reading.sqlite3"}):
            raise R2StorageError("unexpected reading manifest")
        entry=manifest["files"]["reading.sqlite3"]
        digest,size=entry.get("sha256"),entry.get("size")
        if not isinstance(digest,str) or not HEX64.fullmatch(digest) or not isinstance(size,int) or not 0<size<=MAX_DB_BYTES:
            raise R2StorageError("invalid reading blob metadata")
        target=Path(destination).resolve()/ARCHIVE/snapshot[:16]
        if target.exists():
            raise R2StorageError("restore destination already exists; choose a new path")
        target.parent.mkdir(parents=True,exist_ok=True)
        with TemporaryDirectory(prefix=".wf-private-restore-",dir=target.parent) as tmp:
            saved=Path(tmp)/"reading.sqlite3"
            head=self._head(self._blob_key(ARCHIVE,digest))
            if (head is None or int(head.get("ContentLength",-1))!=size
                or head.get("Metadata",{}).get("sha256")!=digest):
                raise R2StorageError("private reading R2 blob missing or altered")
            self.client.download_file(self.config.bucket,self._blob_key(ARCHIVE,digest),str(saved))
            if _digest(saved)!=(digest,size):
                raise R2StorageError("restored private reading SHA256 mismatch")
            stats=audit_private_reading(saved)
            if stats!=manifest.get("stats"):
                raise R2StorageError("restored private reading inventory differs")
            target.mkdir()
            saved.replace(target/"reading.sqlite3")
            (target/"manifest.json").write_bytes(encoded)
        return {"path":str(target/"reading.sqlite3"),"snapshot":snapshot,
                "sha256":digest,"stats":stats,"restored_and_verified":True}

    def inventory(self) -> dict:
        """Read-only R2 prefix listing confirms actual objects, not CI status."""
        prefix=self._root(ARCHIVE)+"/"
        keys=[]
        token=None
        while True:
            args={"Bucket":self.config.bucket,"Prefix":prefix,"MaxKeys":1000}
            if token:
                args["ContinuationToken"]=token
            page=self.client.list_objects_v2(**args)
            keys.extend(item["Key"] for item in page.get("Contents",()))
            if len(keys)>10000:
                raise R2StorageError("private reading object inventory exceeds bound")
            if not page.get("IsTruncated"):
                break
            token=page.get("NextContinuationToken")
            if not token:
                raise R2StorageError("R2 inventory missing continuation")
        return {"prefix":prefix,"object_count":len(keys),
                "has_latest":self._latest_key(ARCHIVE) in keys,
                "has_snapshot":any("/snapshots/" in k for k in keys),
                "has_blob":any("/blobs/" in k for k in keys)}
