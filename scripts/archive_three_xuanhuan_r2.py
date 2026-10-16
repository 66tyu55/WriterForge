"""Bounded, individually verified fantasy-novel web download -> private R2.

Three independent inputs; a bad file fails CLOSED for that work, without
impacting another. Full original text never enters ChatGPT, public GitHub
commits, Actions artifacts or job logs. Structural scene learning is separate.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import argparse
import json
import os
import re

from writerforge.r2_storage import (
    R2Config, R2StorageError, _canonical, _digest, MAX_LATEST_BYTES,
)
from writerforge.single_work_runner import SingleWorkVault, FORMAT

HF_BASE = "https://huggingface.co/datasets/lainka0o0/chinese-novel-nonH-collect/resolve/"
MAX_BYTES = 32 * 1024 * 1024
HEADER = re.compile(
    r"^\s*(?:正文[\s　]*)?第[0-9零〇一二三四五六七八九十百千萬万兩两]{1,15}章"
)


@dataclass(frozen=True)
class NovelSource:
    work_id: str
    title: str
    author: str
    protagonist: str
    source_url: str
    min_bytes: int
    max_bytes: int
    expected_bytes: int | None
    pinned_sha256: str | None
    min_heading_occurrences: int


SOURCES = {
    "doupo": NovelSource(
        "doupo", "斗破苍穹", "天蚕土豆", "萧炎",
        HF_BASE + "1cb09ea23ed6e3fcd0f4347e15c8f086307e9efe/L/" +
        quote("0005005.斗破苍穹.txt"),
        11_000_000, 20_000_000, 16_085_734,
        "8d2e617d7ea4742452b765393bb66b0b0bb8546f63b9ff88dff9d3f6a779c0f6",
        800,
    ),
    "wudongqiankun": NovelSource(
        "wudongqiankun", "武动乾坤", "天蚕土豆", "林动",
        HF_BASE + "bc2e50d1c3a760cf9220159f3247de25163a39a0/F/" +
        quote("武动乾坤.txt"),
        6_000_000, 12_000_000, None,
        "86a2fd859b424efe0500b4b36713ea8b05d551140650904ffc2ae02eb244ed28",
        600,
    ),
    "wanmeishijie": NovelSource(
        "wanmeishijie", "完美世界", "辰东", "石昊",
        "https://download.zxcs.zip/" + quote("《完美世界》（校对版全本）作者：辰东.txt"),
        9_000_000, 19_000_000, None,
        None, 800,
    ),
}


class OriginalSourceError(R2StorageError):
    pass


def verify_source(source: NovelSource, path: Path) -> dict:
    if not path.is_file():
        raise OriginalSourceError("MISSING_REAL_SOURCE")
    total = path.stat().st_size
    if not source.min_bytes <= total <= source.max_bytes:
        raise OriginalSourceError(
            f"SOURCE_SIZE_OUT_OF_RANGE: {source.work_id} {total} bytes"
        )
    if source.expected_bytes is not None and total != source.expected_bytes:
        raise OriginalSourceError(
            f"PINNED_SOURCE_SIZE_CHANGED: {source.work_id} {total} bytes"
        )
    digest, verified_size = _digest(path)
    if verified_size != total:
        raise OriginalSourceError("SOURCE_MODIFIED_ON_DISK")
    if source.pinned_sha256 and digest != source.pinned_sha256:
        raise OriginalSourceError("PINNED_SOURCE_SHA256_CHANGED")
    valid_encoding = None
    heading_count = 0
    protagonist = False
    with path.open("rb") as stream:
        start = stream.read(256)
    if b"<html" in start.lower() or b"<!doctype" in start.lower():
        raise OriginalSourceError("SOURCE_IS_WEBSITE_HTML_NOT_TXT")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            count = 0
            identified = False
            with path.open("r", encoding=encoding) as stream:
                for line in stream:
                    count += int(bool(HEADER.match(line)))
                    if source.protagonist in line:
                        identified = True
            valid_encoding = encoding
            heading_count = count
            protagonist = identified
            break
        except UnicodeError:
            continue
    if valid_encoding is None:
        raise OriginalSourceError("SOURCE_ENCODING_UNSUPPORTED")
    if heading_count < source.min_heading_occurrences or not protagonist:
        raise OriginalSourceError(
            f"SOURCE_NOT_FULL_NOVEL: {source.work_id}; "
            f"headings={heading_count}; protagonist={protagonist}"
        )
    return {
        "work_id": source.work_id,
        "source_bytes": total,
        "source_sha256": digest,
        "sha256_pinned_before_run": source.pinned_sha256 is not None,
        "encoding": valid_encoding,
        "chapter_heading_occurrences": heading_count,
        "source_url": source.source_url,
        "structural_learning_performed": False,
        "independent_reader_review_performed": False,
    }


def fetch_original(source: NovelSource, destination: Path) -> dict:
    if destination.exists():
        raise OriginalSourceError("REFUSE_REPLACE_EXISTING_INPUT")
    url = urlparse(source.source_url)
    if url.scheme != "https" or url.hostname not in (
        "huggingface.co", "download.zxcs.zip"
    ):
        raise OriginalSourceError("SOURCE_HOST_NOT_APPROVED")
    partial = destination.with_suffix(".part")
    size = 0
    try:
        req = Request(source.source_url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; WriterForge-private-library/1)"
        })
        with urlopen(req, timeout=90) as response, partial.open("xb") as out:
            if response.status != 200:
                raise OriginalSourceError("SOURCE_SERVER_HTTP_NOT_200")
            # HF's file downloads redirect to Xet/CloudFront. We hash-check
            # bytes against the original LFS SHA256; ignore unauthenticated
            # claims from a redirect target or HTTP content length.
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > MAX_BYTES:
                    raise OriginalSourceError("SOURCE_OVER_MAX_32_MIB")
                out.write(block)
        receipt = verify_source(source, partial)
        partial.replace(destination)
        return receipt
    except OriginalSourceError:
        raise
    except Exception as exc:
        # Do not print redirect tokens, query parameters or remote file content.
        raise OriginalSourceError(
            f"SOURCE_DOWNLOAD_FAILED_{source.work_id}: {type(exc).__name__}"
        ) from None
    finally:
        partial.unlink(missing_ok=True)


def store_verified_source(vault: SingleWorkVault,
                          source: NovelSource, path: Path, receipt: dict) -> dict:
    if (vault.work_id != source.work_id
        or vault.config.bucket != "writerforge-private-library"):
        raise OriginalSourceError("WRONG_WORK_OR_PRIVATE_R2_BUCKET")
    if _digest(path) != (receipt["source_sha256"], receipt["source_bytes"]):
        raise OriginalSourceError("SOURCE_CHANGED_AFTER_VERIFICATION")
    previous = vault.verify_existing_single_work()
    if previous is not None:
        if (previous["utf8_bytes"], previous["utf8_sha256"]) != (
            receipt["source_bytes"], receipt["source_sha256"]
        ):
            raise OriginalSourceError("PREEXISTING_R2_EDITION_DIFFERENT")
        return {**previous, "new_private_archive": False, "fresh_roundtrip": True}

    digest, size = receipt["source_sha256"], receipt["source_bytes"]
    key = vault._blob_key(source.work_id, digest)
    new_blob = vault._upload_blob(source.work_id, path, digest, size)
    manifest = {
        "format": FORMAT,
        "book_id": source.work_id,
        "title": source.title,
        "author": source.author,
        "status": "archived_unreviewed",
        "source_origin": "public_web_private_archive",
        "source_url": source.source_url,
        "file": {"key": key, "sha256": digest, "bytes": size},
        "chapter_heading_occurrences_not_verified_as_chapter_order":
            receipt["chapter_heading_occurrences"],
        "source_sha256_pinned": bool(source.pinned_sha256),
        "semantic_training_performed": False,
    }
    encoded = _canonical(manifest)
    version = sha256(encoded).hexdigest()
    vault._put_small_immutable(
        vault._manifest_key(source.work_id, version), encoded, version,
    )
    latest = vault._latest_key(source.work_id)
    if vault._head(latest) is not None:
        raise OriginalSourceError("R2_POINTER_CHANGED_CONCURRENTLY")
    pointer = _canonical({
        "format": FORMAT, "book_id": source.work_id,
        "snapshot": version, "manifest_sha256": version,
    })
    vault.client.put_object(
        Bucket=vault.config.bucket, Key=latest,
        Body=pointer, ContentType="application/json",
    )
    if vault._get_small(latest, MAX_LATEST_BYTES) != pointer:
        raise OriginalSourceError("R2_POINTER_NOT_READABLE")
    fresh = vault.verify_existing_single_work()
    if fresh is None or fresh["utf8_sha256"] != digest or not fresh["fresh_download_sha256_verified"]:
        raise OriginalSourceError("FRESH_R2_SOURCE_HASH_MISMATCH")
    return {
        **fresh, "new_private_archive": bool(new_blob),
        "uploaded_new_blob": bool(new_blob), "fresh_roundtrip": True,
        "source_origin": "public_web_private_archive",
    }


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--work", choices=sorted(SOURCES), required=True)
    cli.add_argument("--validate-only", action="store_true")
    args = cli.parse_args()
    spec = SOURCES[args.work]
    with TemporaryDirectory(prefix=f"writerforge-{args.work}-runner-") as tmp:
        raw = Path(tmp) / "downloaded-original.txt"
        receipt = fetch_original(spec, raw)
        if args.validate_only:
            result = {"stage": "download_sha_and_content_verified_only", **receipt}
        else:
            vault = SingleWorkVault(
                R2Config.from_environment(), work_id=spec.work_id,
            )
            saved = store_verified_source(vault, spec, raw, receipt)
            result = {
                "stage": "private_r2_fresh_restored",
                "work_id": spec.work_id,
                "title": spec.title,
                "source_bytes": receipt["source_bytes"],
                "source_sha256": receipt["source_sha256"],
                "source_sha256_pinned": bool(spec.pinned_sha256),
                "chapter_heading_occurrences": receipt["chapter_heading_occurrences"],
                "new_private_archive": saved["new_private_archive"],
                "new_blob_uploaded": saved["uploaded_new_blob"],
                "fresh_roundtrip": saved["fresh_roundtrip"],
                "private_prefix": saved["target_prefix"],
                "snapshot": saved["snapshot"],
                "model_training_performed": False,
            }
        # Do not log novel text, original file, or full URL with future tokens.
        redacted = {k: v for k, v in result.items() if k != "source_url"}
        print(json.dumps(redacted, ensure_ascii=False, indent=2))
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
                out.write(f"## {spec.title} — one-book verified source\n")
                out.write(f"Work: {spec.work_id}\n")
                out.write(f"Source SHA256: {receipt['source_sha256']}\n")
                out.write(f"Raw TXT bytes: {receipt['source_bytes']}\n")
                out.write(f"Chapter heading occurrences (not chapter-order proof): {receipt['chapter_heading_occurrences']}\n")
                if not args.validate_only:
                    out.write(f"New R2 book: {result['new_private_archive']}\n")
                    out.write(f"New blob uploaded: {result['new_blob_uploaded']}\n")
                    out.write(f"Fresh R2 SHA256 verified: {result['fresh_roundtrip']}\n")
                    out.write(f"R2 path: {result['private_prefix']}\n")
                out.write("Model literary training/reader evaluation: not performed\n")


if __name__ == "__main__":
    main()
