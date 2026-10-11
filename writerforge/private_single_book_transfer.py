"""Private one-book smoke transfer from the ALREADY-UPLOADED R2 archive.

No Google Drive OAuth, no public GitHub artifact, no re-upload of 13 works.
The source is the exact 13-work SQLite object already present in the author's
R2 bucket. Extract ONLY 星辰变, hash its complete archived UTF-8 text,
upload it as an immutable private blob, confirm the actual object inventory,
download to a FRESH directory, and independently verify byte SHA-256.

Important: the source archive stores decoded section text plus the source
encoding/hash metadata. This checks the reconstructed UTF-8 book's bytes, not
an unjustified assertion that the historical GBK file bytes are identical.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re
import sqlite3

from .private_reading_storage import audit_private_reading
from .r2_storage import (
    R2Config, R2StudyVault, R2StorageError, _canonical, _digest,
    MAX_LATEST_BYTES, MAX_MANIFEST_BYTES,
)

SOURCE_R2_KEY = "WriterForge_PrivateReading_13Works_20261011.sqlite3"
SOURCE_R2_SHA256 = "5b6c0fc1f564155e1ddbab4c853739722a8b422181857a7548e08fe2826e05e6"
SOURCE_R2_BYTES = 231878656

BOOK_ID = "xingchenbian"
BOOK_LABEL = "星辰变"
BOOK_ALIASES = ("星辰变", "星辰變")
FORMAT = "writerforge.private_single_work.v1"
MAX_BOOK_BYTES = 80 * 1024 * 1024
MAX_SOURCE_ARCHIVE_BYTES = 300 * 1024 * 1024


def _select_book(con: sqlite3.Connection) -> tuple:
    rows=con.execute(
        """SELECT id,title,file_name,source_sha256,original_encoding,
                  original_bytes,original_chars,archived_chars,
                  section_count,status
           FROM works ORDER BY id"""
    ).fetchall()
    matches=[]
    for r in rows:
        label=str(r[1] or "")+" "+str(r[2] or "")
        # Never choose a book merely because its text mentions 星辰变.
        # Confirm the edition's own title or filename.
        if any(name in label for name in BOOK_ALIASES):
            matches.append(r)
    if len(matches)!=1:
        raise R2StorageError(
            "expected one unique 星辰变 title in the 13-work private archive; "
            f"found {len(matches)}; refusing ambiguous transfer"
        )
    selected=matches[0]
    if selected[9]!="archived_unreviewed":
        raise R2StorageError("unexpected source work status")
    return selected


def extract_one_book(archive: Path, output: Path) -> dict:
    """Read existing, verified 13-book archive, then stream a SINGLE work."""
    audit=audit_private_reading(archive)
    if audit["works"]!=13 or audit["semantic_verified"] or audit["literary_training_performed"]:
        raise R2StorageError("source is not a 13-book unreviewed reading archive")
    output.parent.mkdir(parents=True,exist_ok=True)
    hasher=sha256()
    byte_count=char_count=section_count=0
    with closing(sqlite3.connect(
        "file:"+archive.resolve().as_posix()+"?mode=ro",uri=True
    )) as con:
        book=_select_book(con)
        work_id,title,file_name,original_hash,encoding,original_bytes,original_chars,archived_chars,expected_sections,status=book
        with output.open("xb") as dest:
            for ordinal,content,content_hash,declared_chars in con.execute(
                """SELECT ordinal,content,content_sha256,char_count FROM sections
                   WHERE work_id=? ORDER BY ordinal""",(work_id,)
            ):
                section_count+=1
                if ordinal!=section_count or not isinstance(content,str):
                    raise R2StorageError("private book section ordering invalid")
                encoded=content.encode("utf-8")
                if (len(content)!=declared_chars or
                    sha256(encoded).hexdigest()!=content_hash):
                    raise R2StorageError("private book section content/hash mismatch")
                byte_count+=len(encoded)
                char_count+=len(content)
                if byte_count>MAX_BOOK_BYTES:
                    raise R2StorageError("single-book UTF-8 text exceeds safety cap")
                hasher.update(encoded)
                dest.write(encoded)
        if (not section_count or section_count!=expected_sections
            or char_count!=archived_chars or char_count!=original_chars):
            raise R2StorageError("incomplete single-book reconstruction")
    digest=hasher.hexdigest()
    if _digest(output)!=(digest,byte_count):
        raise R2StorageError("freshly extracted book differs from source sections")
    return {
        "book_id":BOOK_ID,"label":BOOK_LABEL,
        "source_archive_key":SOURCE_R2_KEY,
        "source_archive_sha256":SOURCE_R2_SHA256,
        "original_filename_sha256_declared":original_hash,
        "original_encoding_declared":encoding,
        "original_bytes_declared":original_bytes,
        "section_count":section_count,"characters":char_count,
        "utf8_sha256":digest,"utf8_bytes":byte_count,
        "source_archive_record_verified":True,
        "semantics_reviewed":False,
        "training_performed":False,
    }


class PrivateSingleBookVault(R2StudyVault):
    """Tiny specialization of the existing S3 client, NOT another account."""

    def _root(self, library: str) -> str:
        if library!=BOOK_ID:
            raise R2StorageError("only the single approved private test book is allowed")
        return f"{self.config.prefix}/private-reading/single-works/{BOOK_ID}"

    def smoke_transfer(self, *, source_key: str = SOURCE_R2_KEY,
                       source_hash: str = SOURCE_R2_SHA256,
                       source_bytes: int = SOURCE_R2_BYTES) -> dict:
        if source_key!=SOURCE_R2_KEY or source_hash!=SOURCE_R2_SHA256 or source_bytes!=SOURCE_R2_BYTES:
            raise R2StorageError("only the pinned prior R2 source archive is accepted")
        head=self._head(source_key)
        if head is None or int(head.get("ContentLength",-1))!=source_bytes:
            raise R2StorageError("existing R2-root source archive missing/wrong size")
        with TemporaryDirectory(prefix="writerforge-r2-one-book-") as tmp:
            directory=Path(tmp)
            archive=directory/"source-13.sqlite3"
            # This download is from SAME R2 bucket/credentials as the upload.
            self.client.download_file(self.config.bucket,source_key,str(archive))
            if _digest(archive)!=(source_hash,source_bytes):
                raise R2StorageError("source archive FAILED pinned SHA256")
            only_book=directory/"xingchenbian.utf8.txt"
            details=extract_one_book(archive,only_book)
            content_hash=details["utf8_sha256"]
            content_size=details["utf8_bytes"]
            key=self._blob_key(BOOK_ID,content_hash)
            uploaded=self._upload_blob(BOOK_ID,only_book,content_hash,content_size)
            manifest={
                "format":FORMAT,
                "privacy":"private-r2-only",
                "book_id":BOOK_ID,"status":"archived_unreviewed",
                "source_archive_sha256":source_hash,
                "file":{"key":key,"sha256":content_hash,"bytes":content_size},
                "sections":details["section_count"],
                "characters":details["characters"],
                "original_encoding":details["original_encoding_declared"],
                "original_file_sha256_recorded_not_rederived":details["original_filename_sha256_declared"],
                "semantic_training_performed":False,
            }
            raw=_canonical(manifest)
            version=sha256(raw).hexdigest()
            self._put_small_immutable(self._manifest_key(BOOK_ID,version),raw,version)
            pointer=_canonical({
                "format":FORMAT,"book_id":BOOK_ID,
                "snapshot":version,"manifest_sha256":version,
            })
            latest_key=self._latest_key(BOOK_ID)
            previous=self._head(latest_key)
            if previous is None or self._get_small(latest_key,MAX_LATEST_BYTES)!=pointer:
                self.client.put_object(
                    Bucket=self.config.bucket,Key=latest_key,Body=pointer,
                    ContentType="application/json",
                )
            if self._get_small(latest_key,MAX_LATEST_BYTES)!=pointer:
                raise R2StorageError("private book latest pointer not readable")
            # Actual STRONGLY CONSISTENT R2 listing; a workflow green check is
            # not evidence of an object in the intended bucket.
            listed=self.client.list_objects_v2(
                Bucket=self.config.bucket,Prefix=self._root(BOOK_ID)+"/",MaxKeys=1000,
            )
            if listed.get("IsTruncated"):
                raise R2StorageError("single-book inventory exceeded bounded listing")
            known={obj["Key"] for obj in listed.get("Contents",())}
            desired={key,self._manifest_key(BOOK_ID,version),latest_key}
            if not desired.issubset(known):
                raise R2StorageError("uploaded private book missing from actual R2 inventory")
            # Fresh download, not local cache and not the original temp file.
            fresh=directory/"fresh"
            fresh.mkdir()
            restored=fresh/"xingchenbian.new-download.txt"
            self.client.download_file(self.config.bucket,key,str(restored))
            if _digest(restored)!=(content_hash,content_size):
                raise R2StorageError("fresh R2 re-download differs by SHA256/bytes")
            # Confirm manifest content, not merely existence of an S3 object.
            checked=self._get_small(self._manifest_key(BOOK_ID,version),MAX_MANIFEST_BYTES)
            if checked!=raw or sha256(checked).hexdigest()!=version:
                raise R2StorageError("remote single-book manifest checksum mismatch")
            if restored.read_bytes()!=only_book.read_bytes():
                # small bounded (<80 MiB) extra byte equality check; hash
                # already independently computed using streamed disk reads.
                raise R2StorageError("round-trip text bytes changed")
            return {
                "book":BOOK_LABEL,
                "source":"previously uploaded private R2 13-work SQLite archive",
                "target_bucket_matches_expected":self.config.bucket=="writerforge-private-library",
                "target_prefix":self._root(BOOK_ID)+"/",
                "source_archive_sha256_verified":True,
                "only_one_book_extracted":True,
                "uploaded":bool(uploaded),
                "remote_objects_present":len(desired),
                "fresh_download_sha256_verified":True,
                "utf8_sha256":content_hash,
                "utf8_bytes":content_size,
                "section_count":details["section_count"],
                "characters":details["characters"],
                "snapshot":version,
                "classification_performed":False,
                "training_performed":False,
                "other_12_works_unchanged":True,
            }
