"""One-file, pinned public-web TXT -> private R2, directly in GitHub Actions.

No ChatGPT, Google Drive credential, 13-work master, public GitHub artifact, or
unverified assumptions about modern-novel chapter numbering.

This is PRIVATE ORIGINAL ARCHIVING, not model training or proof that the
user's Google Drive file matches the independently found web edition.
"""
from __future__ import annotations

from hashlib import sha1, sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
import argparse
import json
import os
import re

from writerforge.r2_storage import (
    R2Config, R2StorageError, _canonical, _digest, MAX_LATEST_BYTES,
)
from writerforge.single_work_runner import SingleWorkVault, FORMAT

WORK_ID="fanrenxiuxian"
TITLE="凡人修仙传"
SOURCE_REPO="qiuliw/Books"
SOURCE_COMMIT="cfff249d7191af16cde9e89bc1447d3203d04629"
SOURCE_NAME="《凡人修仙传》（校对版全本+番外）作者：忘语.txt"
SOURCE_GIT_BLOB="05bbc28304d231a630e7e7442ab2e5055f707436"
SOURCE_SIZE=15_079_878
MAX_BYTES=32*1024*1024
SOURCE_URL=(
    "https://raw.githubusercontent.com/"
    +SOURCE_REPO+"/"+SOURCE_COMMIT+"/"+quote(SOURCE_NAME)
)
CHAPTER_HEADING=re.compile(
    r"^\s*第[零〇○一二三四五六七八九十百千萬万兩两0-9]{1,16}章"
)


class SourceArchiveError(R2StorageError):
    pass


def validate_downloaded(path:Path)->dict:
    if not path.is_file() or path.stat().st_size!=SOURCE_SIZE:
        raise SourceArchiveError("WEB_EDITION_SIZE_MISMATCH: different or incomplete download")
    digest=sha256()
    git=sha1()
    git.update(f"blob {SOURCE_SIZE}\0".encode("ascii"))
    with path.open("rb") as reader:
        while block:=reader.read(1024*1024):
            git.update(block)
            digest.update(block)
    if git.hexdigest()!=SOURCE_GIT_BLOB:
        raise SourceArchiveError("WEB_EDITION_GIT_BLOB_MISMATCH: source has changed")
    # Count actual chapter headings; do not depend on whole-book sequential
    # ordering until each volume's true chapter grammar is independently read.
    last_error=None
    for encoding in ("utf-8-sig","gb18030"):
        try:
            with path.open("r",encoding=encoding) as f:
                prelude=f.read(180_000)
                if TITLE not in prelude or "忘语" not in prelude:
                    raise SourceArchiveError("WEB_EDITION_TITLE_AUTHOR_MISMATCH")
                f.seek(0)
                headings=0
                protagonist=False
                for line in f:
                    if CHAPTER_HEADING.match(line):
                        headings+=1
                    if not protagonist and "韩立" in line:
                        protagonist=True
            if not protagonist or headings<1800:
                raise SourceArchiveError(
                    "WEB_EDITION_CONTENT_INCOMPLETE_OR_UNEXPECTED_HEADING_STYLE"
                    +f": headings={headings}, protagonist_present={protagonist}"
                )
            return {"bytes":SOURCE_SIZE,"sha256":digest.hexdigest(),
                    "git_blob_sha1":git.hexdigest(),"encoding":encoding,
                    "chapter_heading_occurrences":headings,
                    "source_revision":SOURCE_COMMIT,
                    "full_edition_cross_checked_against_owner_drive":False,
                    "structural_study_performed":False,"model_training_performed":False}
        except UnicodeError as exc:
            last_error=exc
    raise SourceArchiveError("WEB_EDITION_TEXT_DECODING_FAILED") from last_error


def fetch_pinned_original(destination:Path)->dict:
    if destination.exists():
        raise SourceArchiveError("refusing to replace existing source")
    parsed=urlsplit(SOURCE_URL)
    if parsed.scheme!="https" or parsed.netloc!="raw.githubusercontent.com":
        raise SourceArchiveError("unexpected web source host")
    part=destination.with_name(destination.name+".partial")
    received=0
    try:
        req=Request(SOURCE_URL,headers={"User-Agent":"WriterForge-private-single-source/1"})
        with urlopen(req,timeout=90) as response, part.open("xb") as out:
            final=urlsplit(response.geturl())
            if (response.status!=200 or final.scheme!="https"
                or final.netloc!="raw.githubusercontent.com"):
                raise SourceArchiveError("unexpected raw GitHub source redirect/status")
            while block:=response.read(1024*1024):
                received+=len(block)
                if received>MAX_BYTES:
                    raise SourceArchiveError("web download exceeds 32 MiB limit")
                out.write(block)
        if received!=SOURCE_SIZE:
            raise SourceArchiveError(
                f"WEB_EDITION_DOWNLOAD_SIZE_MISMATCH: expected {SOURCE_SIZE}, got {received}"
            )
        receipt=validate_downloaded(part)
        part.replace(destination)
        return receipt
    finally:
        part.unlink(missing_ok=True)


def archive_to_private_r2(vault:SingleWorkVault,path:Path,source:dict)->dict:
    if vault.work_id!=WORK_ID or vault.config.bucket!="writerforge-private-library":
        raise SourceArchiveError("WRONG_R2_BUCKET_OR_WORK")
    if _digest(path)!=(source["sha256"],source["bytes"]):
        raise SourceArchiveError("source has changed since pinned verification")
    previous=vault.verify_existing_single_work()
    if previous is not None:
        if (previous["utf8_bytes"],previous["utf8_sha256"]) != (
            source["bytes"],source["sha256"]
        ):
            raise SourceArchiveError("EXISTING_R2_EDITION_DIFFERENT: do not overwrite")
        return {**previous,"source_origin":"pinned_public_web",
                "new_private_archive":False,"fresh_roundtrip":True}

    key=vault._blob_key(WORK_ID,source["sha256"])
    uploaded=vault._upload_blob(WORK_ID,path,source["sha256"],source["bytes"])
    manifest={
        "format":FORMAT,"book_id":WORK_ID,"title":TITLE,
        "status":"archived_unreviewed","source_origin":"pinned_public_web",
        "source_repo":SOURCE_REPO,"source_commit":SOURCE_COMMIT,
        "source_git_blob_sha1":SOURCE_GIT_BLOB,
        "file":{"key":key,"bytes":source["bytes"],"sha256":source["sha256"]},
        "chapter_heading_occurrences_unverified":source["chapter_heading_occurrences"],
        "semantic_training_performed":False,
    }
    canonical=_canonical(manifest)
    manifest_sha=sha256(canonical).hexdigest()
    vault._put_small_immutable(vault._manifest_key(WORK_ID,manifest_sha),
                              canonical,manifest_sha)
    latest=vault._latest_key(WORK_ID)
    pointer=_canonical({"format":FORMAT,"book_id":WORK_ID,
                         "snapshot":manifest_sha,"manifest_sha256":manifest_sha})
    if vault._head(latest) is not None:
        raise SourceArchiveError("latest changed concurrently: refusing overwrite")
    vault.client.put_object(Bucket=vault.config.bucket,Key=latest,
                            Body=pointer,ContentType="application/json")
    if vault._get_small(latest,MAX_LATEST_BYTES)!=pointer:
        raise SourceArchiveError("new R2 latest pointer failed readback")
    fresh=vault.verify_existing_single_work()
    if fresh is None or fresh["utf8_sha256"]!=source["sha256"]:
        raise SourceArchiveError("FRESH_R2_DOWNLOAD_SHA256_FAILED")
    return {**fresh,"source_origin":"pinned_public_web",
            "new_private_archive":True,"uploaded_new_blob":bool(uploaded),
            "fresh_roundtrip":True}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--validate-only",action="store_true",
                   help="no secrets or R2 writes; verify actual public TXT")
    args=p.parse_args(argv)
    with TemporaryDirectory(prefix="wf-website-to-r2-") as tmp:
        source=Path(tmp)/"web-original.txt"
        info=fetch_pinned_original(source)
        if args.validate_only:
            result={"stage":"source_verified_only",**info,"new_private_archive":False}
        else:
            vault=SingleWorkVault(R2Config.from_environment(),work_id=WORK_ID)
            uploaded=archive_to_private_r2(vault,source,info)
            result={
                "stage":"private_r2_fresh_restored",
                "work_id":WORK_ID,"source_bytes":info["bytes"],
                "source_sha256":info["sha256"],
                "source_git_blob_sha1":SOURCE_GIT_BLOB,
                "source_revision":SOURCE_COMMIT,
                "chapter_heading_occurrences":info["chapter_heading_occurrences"],
                "library_prefix":uploaded["target_prefix"],
                "new_private_archive":uploaded["new_private_archive"],
                "new_blob_uploaded":uploaded["uploaded_new_blob"],
                "fresh_roundtrip":uploaded["fresh_roundtrip"],
                "snapshot":uploaded["snapshot"],
                "literary_model_training_performed":False,
            }
            if not result["fresh_roundtrip"]:
                raise SourceArchiveError("no confirmed R2 fresh download")
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as f:
                f.write("## 凡人修仙传 网页原文单书归档\n")
                f.write(f"Stage: {result['stage']}\n")
                f.write(f"Input bytes: {info['bytes']}\n")
                f.write(f"Raw source SHA256: {info['sha256']}\n")
                f.write(f"Headings observed: {info['chapter_heading_occurrences']}\n")
                if not args.validate_only:
                    f.write(f"New book archive: {result['new_private_archive']}\n")
                    f.write(f"New blob uploaded: {result['new_blob_uploaded']}\n")
                    f.write(f"Fresh R2 download: {result['fresh_roundtrip']}\n")
                    f.write(f"Snapshot: {result['snapshot']}\n")
                f.write("This is source archiving, not model semantic literary training.\n")


if __name__=="__main__":
    main()
