"""Content-addressed, independently verifiable study archive and GitHub restore.

Storage contract:
  - GitHub Actions is an ephemeral worker, NOT the canonical corpus store.
  - Only an explicitly allowlisted, public-domain original is published.
  - Each corpus+study-schema edition gets one GitHub Release, never a growing
    string of short-lived workflow artifacts or a binary committed to Git.
  - Local training is already durable in SQLite; restore never overwrites it.
  - Future private/author-owned corpora must use local/private object storage,
    not the public GitHub Release route.

This module uses the Python standard library; local restore needs no gh CLI.
"""
from __future__ import annotations

from hashlib import sha256
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote
from typing import Mapping
import json
import os
import re
import shutil
import sqlite3
import urllib.request
import zipfile

from .source_study import SOURCE_PAGE, WORK_ID

STUDY_SCHEMA = 1
FORMAT = "writerforge.xuehai.bundle.v1"
REPO_DEFAULT = "66tyu55/WriterForge"
RELEASE_PREFIX = "xuehai-xiyouji-23962-s1-"
BUNDLE_NAME = "xuehai-xiyouji-23962-s1.bundle.zip"
MANIFEST_NAME = "xuehai-xiyouji-23962-s1.manifest.json"
REQUIRED_FILES = (
    "xiyouji_23962_original.txt",
    "xiyouji_studied.sqlite3",
    "PROJECT_GUTENBERG_LICENSE.txt",
    "training_report.json",
    "verified_draft_context.json",
    "TRAINING_STATUS.md",
)
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_BYTES = 60 * 1024 * 1024
MAX_TOTAL_RAW_BYTES = 140 * 1024 * 1024
MAX_MANIFEST_BYTES = 96 * 1024


class StudyStorageError(ValueError):
    pass


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _validate_database(path: Path, expected_work: str, source_sha: str,
                       report: Mapping) -> None:
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise StudyStorageError("missing or oversized study SQLite database")
    try:
        # sqlite3.connect(mode=ro) ensures verify never mutates the stored DB.
        from urllib.parse import quote as url_quote
        uri = "file:" + url_quote(str(path.resolve()).replace("\\", "/"), safe="/:") + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=15)) as conn:
            integrity = conn.execute("PRAGMA quick_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise StudyStorageError("SQLite integrity check failed")
            work = conn.execute(
                "SELECT work_id,source_sha256,chapter_count FROM studied_works"
            ).fetchall()
            if len(work) != 1 or work[0][0] != expected_work or work[0][1] != source_sha:
                raise StudyStorageError("study work/source provenance mismatch")
            chapters = conn.execute(
                "SELECT COUNT(*) FROM studied_chapters WHERE work_id=?",
                (expected_work,),
            ).fetchone()[0]
            units = conn.execute(
                "SELECT COALESCE(SUM(source_spans),0) FROM studied_chapters WHERE work_id=?",
                (expected_work,),
            ).fetchone()[0]
            entries = conn.execute(
                "SELECT COUNT(*) FROM xuehai_entries WHERE work_id=?",
                (expected_work,),
            ).fetchone()[0]
            if chapters != 100 or work[0][2] != 100:
                raise StudyStorageError("stored work is not the complete 100 chapters")
            if units != report["studied_units"] or entries != report["retrieval_entries"]:
                raise StudyStorageError("study statistics mismatch stored data")
    except sqlite3.Error as exc:
        raise StudyStorageError("cannot validate study SQLite database") from exc


def _check_sources(files: Mapping[str, Path]) -> dict:
    if set(files) != set(REQUIRED_FILES):
        raise StudyStorageError("study package missing required source/data/report files")
    for name, path in files.items():
        if not path.is_file() or path.stat().st_size <= 0 or path.stat().st_size > MAX_FILE_BYTES:
            raise StudyStorageError(f"missing, empty or oversized file: {name}")
    report = json.loads(files["training_report.json"].read_text(encoding="utf-8"))
    if (report.get("work_id") != WORK_ID or report.get("studied_chapters") != 100
        or not report.get("structure_complete") or report.get("literary_reader_first_complete")
        or report.get("model_generation_performed")
        or report.get("independent_litcritic_performed")):
        raise StudyStorageError("study report cannot be published as verified structural learning")
    if report.get("source_raw_sha256") != _hash_file(files["xiyouji_23962_original.txt"]):
        raise StudyStorageError("downloaded original source hash differs from report")
    _validate_database(files["xiyouji_studied.sqlite3"], WORK_ID, report["source_sha256"], report)
    trace = json.loads(files["verified_draft_context.json"].read_text(encoding="utf-8"))
    if (trace.get("study_level") != "deterministic_structural_unverified"
        or not trace.get("retrieval_refs") or trace.get("accepted")):
        raise StudyStorageError("draft context does not prove unaccepted source-grounded work")
    return report


def prepare_release(input_dir: str | Path, output_dir: str | Path) -> dict:
    """Package verified ORIGINAL 西遊記 only; never publish other user corpora."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    files = {name: input_dir/name for name in REQUIRED_FILES}
    report = _check_sources(files)
    output_dir.mkdir(parents=True, exist_ok=True)
    source = report["source_raw_sha256"]
    tag = RELEASE_PREFIX + source[:16]
    assets = {
        name: {"sha256":_hash_file(path),"size":path.stat().st_size}
        for name, path in files.items()
    }
    zip_path = output_dir/BUNDLE_NAME
    part = zip_path.with_suffix(".partial")
    try:
        # Stream ZIP compression from files; no full 65 MiB SQLite in Python.
        with zipfile.ZipFile(part, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name, path in files.items():
                archive.write(path, arcname=name)
        if part.stat().st_size > MAX_ARCHIVE_BYTES:
            raise StudyStorageError("compressed study package exceeds 60 MiB")
        os.replace(part, zip_path)
    finally:
        part.unlink(missing_ok=True)
    manifest = {
        "format": FORMAT,
        "study_schema": STUDY_SCHEMA,
        "release_tag": tag,
        "work_id": WORK_ID,
        "title": "西遊記",
        "language": "zh-Hant",
        "study_level": "deterministic_structural_unverified",
        "source_page": SOURCE_PAGE,
        "source_sha256": report["source_sha256"],
        "source_raw_sha256": source,
        "studied_chapters": 100,
        "studied_units": report["studied_units"],
        "retrieval_entries": report["retrieval_entries"],
        "files": assets,
        "archive": {
            "name": BUNDLE_NAME,
            "sha256": _hash_file(zip_path),
            "size": zip_path.stat().st_size,
        },
        "notes": [
            "This is structural indexing, not model fine-tuning or proven literary analysis.",
            "Original source is Project Gutenberg #23962; redistribution includes full Gutenberg license.",
            "Never auto-publish third-party copyrighted/private manuscripts to a public repository.",
        ],
    }
    man_path = output_dir/MANIFEST_NAME
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"tag":tag, "archive_path":str(zip_path), "manifest_path":str(man_path),
            "compressed_bytes":zip_path.stat().st_size,"source_sha256":source}


def validate_bundle(bundle_path: str | Path, manifest_path: str | Path,
                    target_dir: str | Path) -> dict:
    """Verify archive SHA, each member SHA/size, source and SQLite; then restore.

    Content is staged in a temporary directory and atomically installed only
    after ALL integrity checks pass. Existing target data is never overwritten.
    """
    bundle_path, manifest_path, target_dir = (
        Path(bundle_path), Path(manifest_path), Path(target_dir)
    )
    if not manifest_path.is_file() or manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise StudyStorageError("manifest missing or too large")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise StudyStorageError("manifest is not valid JSON") from exc
    if (manifest.get("format") != FORMAT or manifest.get("study_schema") != STUDY_SCHEMA
        or manifest.get("work_id") != WORK_ID or manifest.get("studied_chapters") != 100):
        raise StudyStorageError("incompatible/unknown storage manifest")
    source_hash = manifest.get("source_raw_sha256", "")
    if (not re.fullmatch(r"[0-9a-f]{64}", source_hash)
        or manifest.get("release_tag") != RELEASE_PREFIX + source_hash[:16]):
        raise StudyStorageError("storage release identity doesn't match original checksum")
    metadata = manifest.get("archive", {})
    if (not bundle_path.is_file() or bundle_path.name != metadata.get("name")
        or bundle_path.stat().st_size != metadata.get("size")
        or bundle_path.stat().st_size > MAX_ARCHIVE_BYTES
        or _hash_file(bundle_path) != metadata.get("sha256")):
        raise StudyStorageError("downloaded archive hash or size mismatch")
    saved = manifest.get("files", {})
    if set(saved) != set(REQUIRED_FILES):
        raise StudyStorageError("archive manifest missing required files")
    if target_dir.exists():
        raise StudyStorageError("target already exists: refusing to overwrite training/project data")
    target_dir.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix=".writerforge-restore-", dir=target_dir.parent) as tmp:
        stage = Path(tmp)/"study"
        stage.mkdir()
        with zipfile.ZipFile(bundle_path) as archive:
            infos = archive.infolist()
            if len(infos) != len(REQUIRED_FILES) or {x.filename for x in infos} != set(REQUIRED_FILES):
                raise StudyStorageError("unsafe or unexpected archive members")
            total = sum(x.file_size for x in infos)
            if total > MAX_TOTAL_RAW_BYTES or any(x.file_size > MAX_FILE_BYTES for x in infos):
                raise StudyStorageError("unsafe decompression budget")
            for info in infos:
                expected = saved[info.filename]
                if info.file_size != expected.get("size"):
                    raise StudyStorageError("archive member size mismatch")
                digest = sha256()
                actual = 0
                with archive.open(info, "r") as source, (stage/info.filename).open("xb") as dest:
                    while block := source.read(1024*1024):
                        actual += len(block)
                        if actual > MAX_FILE_BYTES or actual > info.file_size:
                            raise StudyStorageError("archive member exceeds declared size")
                        dest.write(block)
                        digest.update(block)
                if actual != info.file_size or digest.hexdigest() != expected.get("sha256"):
                    raise StudyStorageError("archive member checksum mismatch")
        _check_sources({name:stage/name for name in REQUIRED_FILES})
        # Archive preserved: future audit can compare the signed manifest.
        shutil.copyfile(manifest_path, stage/MANIFEST_NAME)
        os.replace(stage,target_dir)
    return {"restored_to":str(target_dir), "db":str(target_dir/"xiyouji_studied.sqlite3"),
            "source":str(target_dir/"xiyouji_23962_original.txt"),
            "release_tag":manifest["release_tag"], "studied_chapters":100,
            "verified":True}


def _git_request(url: str, token: str | None = None) -> urllib.request.Request:
    headers = {
        "Accept":"application/vnd.github+json",
        "User-Agent":"WriterForge-study-restore/1.0",
        "X-GitHub-Api-Version":"2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def _read_limited_json(url: str, token: str | None = None) -> dict | list:
    with urllib.request.urlopen(_git_request(url, token), timeout=45) as response:
        raw = response.read(MAX_MANIFEST_BYTES * 2 + 1)
    if len(raw)>MAX_MANIFEST_BYTES*2:
        raise StudyStorageError("GitHub API response exceeds safety limit")
    return json.loads(raw.decode("utf-8"))


def _download_limited(url: str, target: Path, *, max_bytes: int,
                      token: str | None = None) -> None:
    if not url.startswith("https://github.com/"):
        raise StudyStorageError("refused non-GitHub download URL")
    total = 0
    with urllib.request.urlopen(_git_request(url, token), timeout=120) as response:
        with target.open("xb") as out:
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > max_bytes:
                    raise StudyStorageError("remote asset exceeds download cap")
                out.write(block)


def restore_from_github(*, repo: str = REPO_DEFAULT, storage_dir: str | Path,
                        tag: str | None = None, token: str | None = None) -> dict:
    """Restore newest verified V23 Chinese-original release into a safe local directory.

    No manual ZIP handling or gh CLI required. Never publishes or overwrites.
    """
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise StudyStorageError("invalid GitHub repo")
    api = f"https://api.github.com/repos/{repo}/releases"
    if tag is not None:
        if not re.fullmatch(r"xuehai-xiyouji-23962-s1-[a-f0-9]{16}", tag):
            raise StudyStorageError("invalid study release tag")
        release = _read_limited_json(api+"/tags/"+quote(tag,safe=""), token)
    else:
        listed = _read_limited_json(api+"?per_page=100",token)
        releases = [r for r in listed if (
            not r.get("draft") and r.get("tag_name","").startswith(RELEASE_PREFIX)
        )]
        if not releases:
            raise StudyStorageError("no published original-Chinese study snapshot on GitHub")
        release = max(releases,key=lambda r:r.get("published_at") or "")
    remote_tag=release["tag_name"]
    assets = {a["name"]:a for a in release.get("assets", [])}
    if MANIFEST_NAME not in assets or BUNDLE_NAME not in assets:
        raise StudyStorageError("GitHub study release is incomplete")
    target = Path(storage_dir).expanduser()/remote_tag
    if target.exists():
        # Idempotent restore of an already verified copy; re-validate source,
        # DB and hashes, never assume directory existence proves integrity.
        local_manifest = target / MANIFEST_NAME
        if not local_manifest.exists():
            raise StudyStorageError("existing restore lacks signed manifest")
        cached = json.loads(local_manifest.read_text(encoding="utf-8"))
        if cached.get("release_tag") != remote_tag:
            raise StudyStorageError("existing restore is a different training edition")
        _check_sources({name:target/name for name in REQUIRED_FILES})
        for name in REQUIRED_FILES:
            if _hash_file(target/name) != cached.get("files",{}).get(name,{}).get("sha256"):
                raise StudyStorageError("existing cached training content is corrupted")
        return {"restored_to":str(target),"db":str(target/"xiyouji_studied.sqlite3"),
                "source":str(target/"xiyouji_23962_original.txt"),
                "release_tag":remote_tag,"studied_chapters":100,"verified":True,
                "from_local_cache":True}
    target.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix=".writerforge-gh-download-",dir=target.parent) as tmp:
        staging=Path(tmp)
        for name,cap in ((MANIFEST_NAME,MAX_MANIFEST_BYTES),(BUNDLE_NAME,MAX_ARCHIVE_BYTES)):
            asset=assets[name]
            url=asset.get("browser_download_url","")
            if not url.startswith("https://github.com/"+repo+"/releases/download/"):
                raise StudyStorageError("asset URL doesn't match expected trusted repository")
            _download_limited(url,staging/name,max_bytes=cap,token=token)
        result=validate_bundle(staging/BUNDLE_NAME,staging/MANIFEST_NAME,target)
        result["from_local_cache"]=False
        return result
