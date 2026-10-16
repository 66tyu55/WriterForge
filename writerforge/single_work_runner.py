"""One reusable, fail-closed private R2 single-work transfer executor.

Uses the already-present R2 source archive and GitHub Actions secrets.
No reading data is committed to GitHub or stored between runs.
"""
from __future__ import annotations
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sqlite3

from .private_reading_storage import audit_private_reading
from .private_single_book_transfer import SOURCE_R2_KEY, SOURCE_R2_SHA256, SOURCE_R2_BYTES
from .r2_storage import R2StudyVault, R2StorageError, _canonical, _digest, MAX_LATEST_BYTES, MAX_MANIFEST_BYTES

# Exact source title selection, not substring matches in novel text.
WORKS = {
    "qiumo": ("求魔", ("求魔",)),
    "xianni": ("仙逆", ("仙逆",)),
    "xingchenbian": ("星辰变", ("星辰变", "星辰變")),
    "fanrenxiuxian": ("凡人修仙传", ("凡人修仙传",)),
    "wudongqiankun": ("武动乾坤", ("武动乾坤",)),
    "zhetian": ("遮天", ("遮天",)),
    "wanmeishijie": ("完美世界", ("完美世界",)),
    "manghuangji": ("莽荒纪", ("莽荒纪",)),
    "yuanzun": ("元尊", ("元尊",)),
    "dazhuzai": ("大主宰", ("大主宰",)),
    "taigushenwang": ("太古神王", ("太 古 神 王", "太古神王")),
    "doupo": ("斗破", ("斗破", "斗破苍穹")),
    "xuanjianxianzu": ("玄鉴仙族", ("玄鉴仙族",)),
}
FORMAT="writerforge.private_single_work.v1"
MAX_SINGLE_BYTES=80*1024*1024


class SingleWorkVault(R2StudyVault):
    def __init__(self, config, *, work_id: str, client=None):
        if work_id not in WORKS:
            raise R2StorageError("work ID not in explicit single-work catalog")
        super().__init__(config,client=client)
        self.work_id=work_id

    def _root(self, library: str) -> str:
        if library!=self.work_id:
            raise R2StorageError("cross-work R2 path is prohibited")
        return f"{self.config.prefix}/private-reading/single-works/{library}"

    def verify_existing_single_work(self) -> dict | None:
        """Restore an already archived private book, without the lost 13-book root.

        This does NOT create new books or count a prior snapshot as an upload.
        If the existing latest/manifest/blob is tampered, stop rather than
        silently falling back to an unrelated source.
        """
        latest = self._latest_key(self.work_id)
        if self._head(latest) is None:
            return None
        raw_pointer = self._get_small(latest, MAX_LATEST_BYTES)
        try:
            pointer = json.loads(raw_pointer)
        except ValueError as exc:
            raise R2StorageError("existing per-book R2 latest pointer invalid JSON") from exc
        version = pointer.get("snapshot")
        if (pointer.get("format") != FORMAT or pointer.get("book_id") != self.work_id
            or not isinstance(version, str) or len(version) != 64
            or any(c not in "0123456789abcdef" for c in version)
            or pointer.get("manifest_sha256") != version):
            raise R2StorageError("existing per-book R2 pointer belongs to wrong work or is corrupt")
        raw_manifest = self._get_small(
            self._manifest_key(self.work_id, version), MAX_MANIFEST_BYTES
        )
        if sha256(raw_manifest).hexdigest() != version:
            raise R2StorageError("existing per-book R2 manifest hash mismatch")
        try:
            manifest = json.loads(raw_manifest)
        except ValueError as exc:
            raise R2StorageError("existing per-book R2 manifest invalid JSON") from exc
        file = manifest.get("file", {})
        if not isinstance(file, dict):
            raise R2StorageError("existing per-book R2 file manifest missing")
        digest, count = file.get("sha256"), file.get("bytes")
        if (manifest.get("format") != FORMAT
            or manifest.get("book_id") != self.work_id
            or manifest.get("status") != "archived_unreviewed"
            or not isinstance(digest, str) or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
            or type(count) is not int or not 0 < count <= MAX_SINGLE_BYTES
            or file.get("key") != self._blob_key(self.work_id, digest)):
            raise R2StorageError("existing per-book source manifest is inconsistent")
        source_key = file["key"]
        head = self._head(source_key)
        if (head is None or int(head.get("ContentLength", -1)) != count
            or head.get("Metadata", {}).get("sha256") != digest):
            raise R2StorageError("existing per-book source blob missing or wrong metadata")
        inventory = self.client.list_objects_v2(
            Bucket=self.config.bucket, Prefix=self._root(self.work_id) + "/",
            MaxKeys=1000,
        )
        if inventory.get("IsTruncated"):
            raise R2StorageError("per-book R2 listing truncated; cannot verify source")
        keys = {item["Key"] for item in inventory.get("Contents", ())}
        needed = {latest, self._manifest_key(self.work_id, version), source_key}
        if not needed.issubset(keys):
            raise R2StorageError("existing per-book R2 inventory incomplete")
        with TemporaryDirectory(prefix="wf-private-existing-") as tmp:
            fresh = Path(tmp) / "fresh-r2-download.txt"
            self.client.download_file(self.config.bucket, source_key, str(fresh))
            if _digest(fresh) != (digest, count):
                raise R2StorageError("existing per-book fresh download SHA256 mismatch")
        return {
            "work_id": self.work_id,
            "title": WORKS[self.work_id][0],
            "target_prefix": self._root(self.work_id) + "/",
            "source_origin": "existing_private_per_book_r2",
            "source_integrity_verified": True,
            "source_archive_sha256_verified": False,
            "already_archived": True,
            "uploaded_new_blob": False,
            "utf8_bytes": count,
            "utf8_sha256": digest,
            "source_sections": manifest.get("sections"),
            "remote_objects_present": len(needed),
            "fresh_download_sha256_verified": True,
            "snapshot": version,
            "status": "archived_unreviewed",
            "training_performed": False,
        }

    def execute(self) -> dict:
        if self.config.bucket!="writerforge-private-library":
            raise R2StorageError("not the expected private R2 bucket")
        # A verified independent per-book R2 object is sufficient for restart.
        # The legacy 231 MiB master archive is NOT required in this case.
        already = self.verify_existing_single_work()
        if already is not None:
            return already
        # Only use the known R2 source archive. If its original root key
        # moved, discover it by an exact basename under the controlled
        # writerforge prefix, and still require the pinned size and SHA256.
        source_key=SOURCE_R2_KEY
        head=self._head(source_key)
        if head is None or int(head.get("ContentLength",-1))!=SOURCE_R2_BYTES:
            candidates=[]
            token=None
            for _ in range(10):
                params={"Bucket":self.config.bucket,"Prefix":"writerforge/","MaxKeys":1000}
                if token:
                    params["ContinuationToken"]=token
                page=self.client.list_objects_v2(**params)
                candidates.extend((obj["Key"],obj["Size"]) for obj in page.get("Contents",())
                    if obj["Key"].split("/")[-1]==SOURCE_R2_KEY)
                if not page.get("IsTruncated"):
                    break
                token=page.get("NextContinuationToken")
                if not token:
                    raise R2StorageError("R2 source search pagination incomplete")
            else:
                raise R2StorageError("R2 source inventory exceeded 10000 objects")
            candidates=[key for key,size in candidates if size==SOURCE_R2_BYTES]
            if len(candidates)!=1:
                original_size=(int(head.get("ContentLength",-1)) if head else None)
                raise R2StorageError(
                    f"pinned R2 source not found with expected size; root_size={original_size}; "
                    f"matching_size_candidates={len(candidates)}; no upload attempted; "
                    "NO SOURCE IN THIS BUCKET for requested work. "
                    "Provide a verified independent source, not another retry.")
            source_key=candidates[0]
            head=self._head(source_key)
            if head is None or int(head.get("ContentLength",-1))!=SOURCE_R2_BYTES:
                raise R2StorageError("discovered archive failed HEAD recheck")
        with TemporaryDirectory(prefix="wf-single-work-") as tmp:
            root=Path(tmp)
            archive=root/"source.sqlite3"
            self.client.download_file(self.config.bucket,source_key,str(archive))
            if _digest(archive)!=(SOURCE_R2_SHA256,SOURCE_R2_BYTES):
                raise R2StorageError("pinned source archive SHA256 mismatch")
            audit=audit_private_reading(archive)
            if audit["works"]!=13:
                raise R2StorageError("unexpected source work count")
            label,aliases=WORKS[self.work_id]
            with closing(sqlite3.connect(f"file:{archive.as_posix()}?mode=ro",uri=True)) as db:
                works=db.execute("""SELECT id,title,file_name,source_sha256,original_encoding,
                    original_bytes,original_chars,archived_chars,section_count,status
                    FROM works ORDER BY id""").fetchall()
                selected=[r for r in works if any(a in str(r[1]) or a in str(r[2]) for a in aliases)]
                if len(selected)!=1:
                    raise R2StorageError("missing or ambiguous work title")
                work=selected[0]
                (wid,title,filename,source_sha,source_encoding,source_bytes,
                    original_chars,archived_chars,expected_sections,source_status)=work
                target=root/"only-work.utf8.txt"
                n=total_chars=total_bytes=0
                previous=None
                h=sha256()
                with target.open("xb") as dest:
                    for ordinal,body,digest,chars in db.execute(
                        """SELECT ordinal,content,content_sha256,char_count
                        FROM sections WHERE work_id=? ORDER BY ordinal""",(wid,)
                    ):
                        if type(ordinal) is not int or ordinal<0 or (previous is not None and ordinal<=previous):
                            raise R2StorageError("section ordinals invalid")
                        previous=ordinal
                        if not isinstance(body,str) or len(body)!=chars:
                            raise R2StorageError("section length invalid")
                        chunk=body.encode("utf-8")
                        if sha256(chunk).hexdigest()!=digest:
                            raise R2StorageError("section content checksum mismatch")
                        total_bytes+=len(chunk)
                        if total_bytes>MAX_SINGLE_BYTES:
                            raise R2StorageError("one work exceeds byte budget")
                        total_chars+=chars
                        n+=1
                        dest.write(chunk)
                        h.update(chunk)
                if n!=expected_sections or total_chars!=original_chars or total_chars!=archived_chars:
                    raise R2StorageError("incomplete reconstructed source")
            checksum=h.hexdigest()
            if _digest(target)!=(checksum,total_bytes):
                raise R2StorageError("local source checksum mismatch")
            key=self._blob_key(self.work_id,checksum)
            uploaded=self._upload_blob(self.work_id,target,checksum,total_bytes)
            manifest={"format":FORMAT,"book_id":self.work_id,"title":label,
                      "status":"archived_unreviewed",
                      "source_archive_sha256":SOURCE_R2_SHA256,
                      "original_file_sha256_recorded_not_rederived":source_sha,
                      "original_encoding":source_encoding,
                      "original_bytes_recorded":source_bytes,
                      "sections":n,"characters":total_chars,
                      "file":{"key":key,"sha256":checksum,"bytes":total_bytes},
                      "semantic_training_performed":False}
            raw=_canonical(manifest)
            version=sha256(raw).hexdigest()
            self._put_small_immutable(self._manifest_key(self.work_id,version),raw,version)
            pointer=_canonical({"format":FORMAT,"book_id":self.work_id,
                                "snapshot":version,"manifest_sha256":version})
            latest=self._latest_key(self.work_id)
            current=self._head(latest)
            if current is None or self._get_small(latest,MAX_LATEST_BYTES)!=pointer:
                self.client.put_object(Bucket=self.config.bucket,Key=latest,
                                       Body=pointer,ContentType="application/json")
            if self._get_small(latest,MAX_LATEST_BYTES)!=pointer:
                raise R2StorageError("latest pointer readback mismatch")
            listing=self.client.list_objects_v2(
                Bucket=self.config.bucket,Prefix=self._root(self.work_id)+"/",MaxKeys=1000)
            if listing.get("IsTruncated"):
                raise R2StorageError("R2 inventory truncated")
            keys={row["Key"] for row in listing.get("Contents",())}
            if not {key,latest,self._manifest_key(self.work_id,version)}.issubset(keys):
                raise R2StorageError("R2 missing single-work objects")
            fresh=root/"fresh"
            fresh.mkdir()
            downloaded=fresh/"recovered.txt"
            self.client.download_file(self.config.bucket,key,str(downloaded))
            if _digest(downloaded)!=(checksum,total_bytes):
                raise R2StorageError("fresh R2 download SHA256 differs")
            checked=self._get_small(self._manifest_key(self.work_id,version),MAX_MANIFEST_BYTES)
            if checked!=raw or sha256(checked).hexdigest()!=version:
                raise R2StorageError("remote manifest bytes invalid")
            return {"work_id":self.work_id,"title":label,
                    "target_prefix":self._root(self.work_id)+"/",
                    "source_archive_sha256_verified":True,
                    "source_integrity_verified":True,
                    "source_origin":"verified_legacy_13work_archive",
                    "already_archived":False,
                    "uploaded_new_blob":bool(uploaded),"utf8_bytes":total_bytes,
                    "utf8_sha256":checksum,"source_sections":n,
                    "remote_objects_present":3,
                    "fresh_download_sha256_verified":True,
                    "snapshot":version,"status":"archived_unreviewed",
                    "training_performed":False}
