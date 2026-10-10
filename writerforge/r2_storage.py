"""Private Cloudflare R2 Xuehai snapshots, using the S3-compatible API.

R2 is a private, content-addressed backup vault, NOT a remotely mounted SQLite.
A live database is snapshotted via SQLite's online backup API (WAL-safe), then
small source/report files and the backup are streamed to R2 as immutable blobs.
The manifest is published LAST after upload verification; the small 'latest'
pointer is updated only after the manifest is readable and verified.

No public release, no implicit credentials in source, and no overwrite of local
or immutable remote snapshots. boto3 is an OPTIONAL dependency (writerforge[r2]).
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Mapping
import json
import os
import re
import shutil
import sqlite3

R2_FORMAT = "writerforge.r2.xuehai.v1"
MAX_DB_BYTES = 1024 * 1024 * 1024
MAX_EXTRA_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 1200 * 1024 * 1024
MAX_MANIFEST_BYTES = 128 * 1024
MAX_LATEST_BYTES = 4 * 1024
BLOCK_BYTES = 1024 * 1024
LIBRARY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
ACCOUNT_RE = re.compile(r"^[a-fA-F0-9]{32}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
EXTRA_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,47}\.(?:json|txt|md)$")
ALLOWED_REGIONS = {"default", "eu", "us", "fedramp"}


class R2StorageError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(path: Path) -> tuple[str, int]:
    hash_ = sha256()
    count = 0
    with path.open("rb") as handle:
        while block := handle.read(BLOCK_BYTES):
            count += len(block)
            hash_.update(block)
    return hash_.hexdigest(), count


def _safe_library(value: str) -> str:
    if not isinstance(value, str) or not LIBRARY_RE.fullmatch(value):
        raise R2StorageError("invalid library name: use 1..80 letters/digits/._- without slashes")
    return value


@dataclass(frozen=True)
class R2Config:
    account_id: str
    bucket: str
    access_key_id: str
    secret_access_key: str
    jurisdiction: str = "default"
    prefix: str = "writerforge/v1"

    def __post_init__(self):
        if not ACCOUNT_RE.fullmatch(self.account_id):
            raise R2StorageError("Cloudflare account ID must be 32 hexadecimal characters")
        if not BUCKET_RE.fullmatch(self.bucket):
            raise R2StorageError("invalid Cloudflare R2 bucket name")
        if not self.access_key_id or not self.secret_access_key:
            raise R2StorageError("R2 S3 access key ID and secret key are required")
        if self.jurisdiction not in ALLOWED_REGIONS:
            raise R2StorageError("unsupported R2 jurisdiction")
        if self.prefix != "writerforge/v1":
            raise R2StorageError("unsupported object prefix; prevent publishing outside the private vault")

    @property
    def endpoint(self) -> str:
        segment = "" if self.jurisdiction == "default" else self.jurisdiction + "."
        return f"https://{self.account_id}.{segment}r2.cloudflarestorage.com"

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> "R2Config":
        env = environ if environ is not None else os.environ
        required = {
            "account_id": "WRITERFORGE_R2_ACCOUNT_ID",
            "bucket": "WRITERFORGE_R2_BUCKET",
            "access_key_id": "WRITERFORGE_R2_ACCESS_KEY_ID",
            "secret_access_key": "WRITERFORGE_R2_SECRET_ACCESS_KEY",
        }
        missing = [name for name in required.values() if not env.get(name)]
        if missing:
            raise R2StorageError("R2 is not configured; missing environment keys: "+", ".join(missing))
        return cls(
            **{key: env[name] for key, name in required.items()},
            jurisdiction=env.get("WRITERFORGE_R2_JURISDICTION") or "default",
        )


def r2_configured(environ: Mapping[str, str] | None = None) -> bool:
    """Distinguish *absent* configuration from accidental partial credentials."""
    env = environ if environ is not None else os.environ
    keys = (
        "WRITERFORGE_R2_ACCOUNT_ID", "WRITERFORGE_R2_BUCKET",
        "WRITERFORGE_R2_ACCESS_KEY_ID", "WRITERFORGE_R2_SECRET_ACCESS_KEY",
    )
    present = [bool(env.get(name)) for name in keys]
    if any(present) and not all(present):
        raise R2StorageError("partial R2 configuration: refusing unverified backup")
    return all(present)


def _sqlite_audit(path: Path, *, require_study: bool = True) -> dict:
    if not path.exists() or not path.is_file() or not 0 < path.stat().st_size <= MAX_DB_BYTES:
        raise R2StorageError("missing, empty or oversized SQLite study file")
    try:
        with closing(sqlite3.connect(path)) as con:
            integrity = con.execute("PRAGMA quick_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise R2StorageError("SQLite quick_check failed")
            if require_study:
                row = con.execute(
                    """SELECT COUNT(*) FROM studied_chapters c
                       JOIN snapshots s ON s.id=c.snapshot_id
                       WHERE s.status='published'"""
                ).fetchone()
                if not row or row[0] < 1:
                    raise R2StorageError("no published, durably studied source chapters")
            chapter_count = con.execute("SELECT COUNT(*) FROM studied_chapters").fetchone()[0]
            source_units = con.execute("SELECT COUNT(*) FROM source_spans").fetchone()[0]
            retrieval_entries = con.execute("SELECT COUNT(*) FROM xuehai_entries").fetchone()[0]
            return {
                "studied_chapters": chapter_count,
                "studied_units": source_units,
                "retrieval_entries": retrieval_entries,
            }
    except sqlite3.Error as exc:
        raise R2StorageError("not a compatible WriterForge SQLite database") from exc


def _snapshot_database(source: Path, dest: Path) -> dict:
    if not source.is_file() or source.stat().st_size > MAX_DB_BYTES:
        raise R2StorageError("source database missing or beyond 1 GiB safety limit")
    # Copy from the *live* SQLite database through SQLite's online API; direct
    # copying would miss uncheckpointed WAL data or make inconsistent snapshots.
    try:
        with closing(sqlite3.connect(source, timeout=20)) as src:
            with closing(sqlite3.connect(dest, timeout=20)) as dst:
                src.backup(dst, pages=256, sleep=0.02)
    except sqlite3.Error as exc:
        raise R2StorageError("consistent SQLite online backup failed") from exc
    return _sqlite_audit(dest)


def _read_body(response: Mapping, limit: int) -> bytes:
    body = response["Body"]
    try:
        data = body.read(limit + 1)
    finally:
        close = getattr(body, "close", None)
        if callable(close):
            close()
    if len(data) > limit:
        raise R2StorageError("remote metadata exceeds memory budget")
    return data


def _is_not_found(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        return str(response.get("Error", {}).get("Code", "")) in (
            "404", "NoSuchKey", "NotFound",
        )
    return False


class R2StudyVault:
    def __init__(self, config: R2Config, *, client=None):
        self.config = config
        self._s3 = client

    @property
    def client(self):
        if self._s3 is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as exc:
                raise R2StorageError(
                    'install the optional R2 client: python -m pip install -e ".[r2]"'
                ) from exc
            self._s3 = boto3.client(
                "s3", endpoint_url=self.config.endpoint, region_name="auto",
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},
                    retries={"max_attempts":3, "mode":"standard"},
                    connect_timeout=15, read_timeout=90, max_pool_connections=3,
                ),
            )
        return self._s3

    def _root(self, library: str) -> str:
        return f"{self.config.prefix}/libraries/{_safe_library(library)}"

    def _blob_key(self, library: str, digest: str) -> str:
        return self._root(library) + "/blobs/" + digest

    def _manifest_key(self, library: str, digest: str) -> str:
        return self._root(library) + "/snapshots/" + digest + ".json"

    def _latest_key(self, library: str) -> str:
        return self._root(library) + "/latest.json"

    def _head(self, key: str):
        try:
            return self.client.head_object(Bucket=self.config.bucket, Key=key)
        except Exception as exc:
            if _is_not_found(exc):
                return None
            raise

    def _upload_blob(self, library: str, path: Path, digest: str, size: int) -> bool:
        key = self._blob_key(library, digest)
        row = self._head(key)
        if row is not None:
            meta = row.get("Metadata", {})
            if int(row["ContentLength"]) != size or meta.get("sha256") != digest:
                raise R2StorageError("immutable remote blob exists but its metadata differs")
            return False
        if path.stat().st_size != size or _digest(path)[0] != digest:
            raise R2StorageError("source changed between snapshot and R2 upload")
        try:
            from boto3.s3.transfer import TransferConfig
            transfer = TransferConfig(
                multipart_threshold=8*1024*1024,
                multipart_chunksize=8*1024*1024,
                max_concurrency=2, use_threads=False,
            )
            self.client.upload_file(
                str(path), self.config.bucket, key,
                ExtraArgs={"Metadata":{"sha256":digest}}, Config=transfer,
            )
        except ImportError:
            # A test backend may deliberately inject a minimal upload_file.
            self.client.upload_file(
                str(path), self.config.bucket, key,
                ExtraArgs={"Metadata":{"sha256":digest}},
            )
        confirmed = self._head(key)
        if confirmed is None or int(confirmed.get("ContentLength", -1)) != size or (
            confirmed.get("Metadata",{}).get("sha256") != digest
        ):
            raise R2StorageError("R2 upload missing or does not match expected SHA256 metadata")
        return True

    def _put_small_immutable(self, key: str, value: bytes, digest: str):
        if len(value) > MAX_MANIFEST_BYTES:
            raise R2StorageError("manifest exceeds bound")
        existing = self._head(key)
        if existing is None:
            self.client.put_object(
                Bucket=self.config.bucket, Key=key, Body=value,
                ContentType="application/json", Metadata={"sha256":digest},
            )
        elif (int(existing.get("ContentLength", -1)) != len(value) or
              existing.get("Metadata",{}).get("sha256") != digest):
            raise R2StorageError("remote immutable manifest collision")
        raw = self._get_small(key, MAX_MANIFEST_BYTES)
        if sha256(raw).hexdigest() != digest:
            raise R2StorageError("remote persisted manifest does not pass full readback check")

    def _get_small(self, key: str, cap: int) -> bytes:
        head = self._head(key)
        if head is None or int(head.get("ContentLength", -1)) > cap:
            raise R2StorageError("remote object missing or exceeds maximum allowed metadata size")
        return _read_body(
            self.client.get_object(Bucket=self.config.bucket, Key=key),
            cap,
        )

    def backup(
        self, *, database: str | Path, library: str, source: str | Path | None = None,
        extras: Mapping[str, str | Path] | None = None,
    ) -> dict:
        """Create one immutable, deduplicated snapshot and advance latest.

        Remote mutation happens only after the complete source DB is checked.
        Failure leaves previous latest intact; partial new blobs are harmless.
        """
        library = _safe_library(library)
        extras = dict(extras or {})
        if len(extras) > 12:
            raise R2StorageError("too many extra study artifacts")
        if any(not EXTRA_NAME_RE.fullmatch(name) for name in extras):
            raise R2StorageError("only named .json/.txt/.md extra files are allowed")
        with TemporaryDirectory(prefix="writerforge-r2-") as staging:
            folder = Path(staging)
            db_snapshot = folder/"study.sqlite3"
            stats = _snapshot_database(Path(database), db_snapshot)
            inputs: dict[str, Path] = {"study.sqlite3": db_snapshot}
            if source is not None:
                inputs["source.txt"] = Path(source)
            for name, path in extras.items():
                if name in inputs or name in ("manifest.json", "latest.json"):
                    raise R2StorageError("duplicate or reserved storage filename")
                inputs[name] = Path(path)
            if sum(p.stat().st_size for p in inputs.values()) > MAX_TOTAL_BYTES:
                raise R2StorageError("study resources exceed total R2 backup safety limit")
            files = {}
            for name, path in sorted(inputs.items()):
                if not path.is_file() or path.stat().st_size <= 0:
                    raise R2StorageError("missing or empty study resource: " + name)
                max_size = MAX_DB_BYTES if name == "study.sqlite3" else MAX_EXTRA_BYTES
                if path.stat().st_size > max_size:
                    raise R2StorageError("study resource exceeds safety cap: " + name)
                digest, size = _digest(path)
                files[name] = {"sha256":digest, "size":size}
            manifest = {
                "format":R2_FORMAT,
                "library":library,
                "study_level":"structural_evidence_not_model_finetuning",
                "stats":stats,
                "files":files,
            }
            encoded = _canonical(manifest)
            snapshot = sha256(encoded).hexdigest()
            uploaded = []
            for name, path in sorted(inputs.items()):
                if self._upload_blob(library, path, files[name]["sha256"], files[name]["size"]):
                    uploaded.append(name)
            self._put_small_immutable(self._manifest_key(library,snapshot), encoded, snapshot)
            pointer = _canonical({
                "format":R2_FORMAT, "library":library, "snapshot":snapshot,
                "manifest_sha256":snapshot,
            })
            existing = self._head(self._latest_key(library))
            if existing is None or self._get_small(self._latest_key(library),MAX_LATEST_BYTES) != pointer:
                self.client.put_object(
                    Bucket=self.config.bucket, Key=self._latest_key(library),
                    Body=pointer, ContentType="application/json",
                )
            # Prove the pointer is readable and points to the committed data.
            if self._get_small(self._latest_key(library),MAX_LATEST_BYTES) != pointer:
                raise R2StorageError("R2 latest pointer could not be read back")
            return {
                "provider":"Cloudflare R2", "bucket":self.config.bucket,
                "library":library,"snapshot":snapshot,
                "uri":f"r2://{self.config.bucket}/{self._root(library)}/snapshots/{snapshot}.json",
                "uploaded_files":uploaded, "deduplicated":len(inputs)-len(uploaded),
                "file_count":len(files), "stats":stats,
                "verified":True,
            }

    def restore(self, *, library: str, destination: str | Path,
                snapshot: str | None = None) -> dict:
        library = _safe_library(library)
        if snapshot is None:
            pointer = json.loads(self._get_small(self._latest_key(library),MAX_LATEST_BYTES))
            if pointer.get("format") != R2_FORMAT or pointer.get("library") != library:
                raise R2StorageError("remote latest pointer is invalid")
            snapshot = pointer.get("snapshot")
            if pointer.get("manifest_sha256") != snapshot:
                raise R2StorageError("remote latest pointer has inconsistent hashes")
        if not isinstance(snapshot,str) or not SHA_RE.fullmatch(snapshot):
            raise R2StorageError("invalid remote study snapshot identifier")
        encoded = self._get_small(self._manifest_key(library,snapshot),MAX_MANIFEST_BYTES)
        if sha256(encoded).hexdigest() != snapshot:
            raise R2StorageError("manifest checksum mismatch")
        manifest = json.loads(encoded)
        files = manifest.get("files")
        if (manifest.get("format") != R2_FORMAT or manifest.get("library") != library
            or not isinstance(files,dict) or "study.sqlite3" not in files
            or len(files)>14 or any(
                name not in ("study.sqlite3","source.txt")
                and (not EXTRA_NAME_RE.fullmatch(name))
                for name in files
            )):
            raise R2StorageError("remote study manifest has invalid schema or filenames")
        total = 0
        for entry in files.values():
            if (not isinstance(entry,dict) or not SHA_RE.fullmatch(str(entry.get("sha256","")))
                or not isinstance(entry.get("size"),int) or entry["size"]<=0):
                raise R2StorageError("invalid manifest content digest/size")
            total += entry["size"]
        if total > MAX_TOTAL_BYTES:
            raise R2StorageError("remote manifest would exceed local disk budget")
        target = Path(destination).expanduser().resolve()/library/snapshot[:16]
        if target.exists():
            self._verify_existing(target, files, manifest)
            return self._result(library,snapshot,target,manifest,cached=True)
        target.parent.mkdir(parents=True,exist_ok=True)
        with TemporaryDirectory(prefix=".wf-r2-restore-",dir=target.parent) as tmp:
            staging = Path(tmp)/"data"
            staging.mkdir()
            for name, metadata in sorted(files.items()):
                digest = metadata["sha256"]
                key = self._blob_key(library,digest)
                head = self._head(key)
                cap = MAX_DB_BYTES if name=="study.sqlite3" else MAX_EXTRA_BYTES
                if (head is None or int(head.get("ContentLength",-1)) != metadata["size"]
                    or int(head["ContentLength"]) > cap
                    or head.get("Metadata",{}).get("sha256") != digest):
                    raise R2StorageError("remote R2 file missing/corrupted: "+name)
                path = staging/name
                self.client.download_file(self.config.bucket,key,str(path))
                if _digest(path) != (digest, metadata["size"]):
                    raise R2StorageError("restored R2 object failed SHA256: "+name)
            audited = _sqlite_audit(staging/"study.sqlite3")
            if audited != manifest.get("stats"):
                raise R2StorageError("SQLite contents diverge from signed study stats")
            (staging/"manifest.json").write_bytes(encoded)
            # Destination is deterministic and never overwritten: safe to
            # expose only after all content and SQLite checks pass.
            if target.exists():
                raise R2StorageError("destination was created during restore, refusing overwrite")
            os.replace(staging,target)
        return self._result(library,snapshot,target,manifest,cached=False)

    @staticmethod
    def _verify_existing(target: Path, files: dict, manifest: dict) -> None:
        for name, metadata in files.items():
            path = target/name
            if not path.is_file() or _digest(path) != (metadata["sha256"],metadata["size"]):
                raise R2StorageError("cached local R2 study version was modified: "+name)
        if (not (target/"manifest.json").is_file() or
            sha256((target/"manifest.json").read_bytes()).hexdigest() !=
            sha256(_canonical(manifest)).hexdigest()):
            raise R2StorageError("cached R2 manifest changed")
        if _sqlite_audit(target/"study.sqlite3") != manifest.get("stats"):
            raise R2StorageError("cached SQLite study no longer matches manifest")

    def _result(self, library: str, snapshot: str, target: Path,
                manifest: dict, *, cached: bool) -> dict:
        return {
            "provider":"Cloudflare R2","library":library,
            "snapshot":snapshot, "restored_to":str(target),
            "db":str(target/"study.sqlite3"),
            "source":str(target/"source.txt") if "source.txt" in manifest["files"] else None,
            "verified":True, "from_local_cache":cached,
            "stats":manifest["stats"],
        }
